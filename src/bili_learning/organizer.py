from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
from pathlib import Path, PurePosixPath

from .config import Settings
from .frontmatter import parse_frontmatter
from .navigation import atomic_write, build_navigation
from .note_library import RESOURCE_COLLECTION_MARKER, extract_bvid, find_notes_by_bvid
from .note_template import note_filename, safe_title

ORGANIZE_SCOPES = {"single", "latest", "all"}
RESOURCE_CARD_MAX_CHARS = 8000
RESOURCE_CARD_RUNTIME_DIR = "resource-cards"
ORGANIZE_BACKUP_RUNTIME_DIR = "organize-backups"


def find_duplicate_bvid_notes(settings: Settings, source: Path) -> tuple[str | None, list[Path]]:
    source_resolved = source.resolve()
    if not source_resolved.is_file():
        return None, []
    text = source_resolved.read_text(encoding="utf-8-sig")
    bvid = extract_bvid(text)
    if not bvid:
        return None, []

    duplicates = [item.path.resolve() for item in find_notes_by_bvid(settings, bvid) if item.path.resolve() != source_resolved]
    return bvid, duplicates


def _validate_confirmed_scope(settings: Settings, source: Path, confirmed_scope: str) -> None:
    if confirmed_scope not in ORGANIZE_SCOPES:
        raise ValueError("整理功能默认不执行；执行前必须由用户明确选择单篇（single）、最近一篇（latest）或全部（all）")
    if confirmed_scope == "single":
        return

    notes_root = settings.notes_root.resolve()
    inbox = notes_root.joinpath(*settings.taxonomy["fallback"]["path"]).resolve()
    if source.parent != inbox:
        raise ValueError(f"{confirmed_scope} 仅适用于待整理目录中的笔记：{inbox}")
    if confirmed_scope == "all":
        return

    candidates = [path.resolve() for path in inbox.glob("*.md") if path.is_file()]
    if not candidates:
        raise ValueError("待整理目录中没有可整理的 Markdown 笔记")
    latest = max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name.lower()))
    if source != latest:
        raise ValueError(f"confirmed_scope=latest 但指定文件不是最近一篇：{latest}")


def _validate_source_note(settings: Settings, source: Path, confirmed_scope: str) -> Path:
    source = source.resolve()
    _validate_confirmed_scope(settings, source, confirmed_scope)
    notes_root = settings.notes_root.resolve()
    if source == notes_root or notes_root not in source.parents or not source.is_file():
        raise ValueError("待整理笔记必须是 notes_root 内的现有 Markdown 文件")
    if source.suffix.lower() != ".md":
        raise ValueError("待整理对象必须是 Markdown 笔记")
    navigation_root = (notes_root / settings.navigation_dir).resolve()
    if source.parent == navigation_root or navigation_root in source.parents:
        raise ValueError("导航文件不能作为整理对象")
    return source


def _safe_destination(value: str) -> tuple[str, ...]:
    path = PurePosixPath(value.replace("\\", "/"))
    parts = path.parts
    if path.is_absolute() or not parts or any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise ValueError("目标目录必须是笔记根目录下的相对路径")
    return tuple(parts)


def _validated_destination(settings: Settings, value: str) -> tuple[str, ...]:
    destination = _safe_destination(value)
    organization = settings.taxonomy.get("organization") or {}
    max_depth = organization.get("max_depth", 2)
    if len(destination) > max_depth:
        raise ValueError(f"整理目录最多允许 {max_depth} 层；推荐使用“领域/对象”，不要继续细分")

    reserved = {
        settings.navigation_dir,
        settings.taxonomy["fallback"]["path"][0],
    }
    if destination[0] in reserved:
        raise ValueError("目标目录不能是待整理目录或导航目录")
    return destination


def _resource_root(settings: Settings) -> str:
    organization = settings.taxonomy.get("organization") or {}
    raw = str(organization.get("resource_root") or "05-资源").strip()
    parts = _safe_destination(raw)
    if len(parts) != 1:
        raise ValueError("taxonomy.organization.resource_root 必须是 notes_root 下的一级目录名")
    if parts[0] in {settings.navigation_dir, settings.taxonomy["fallback"]["path"][0]}:
        raise ValueError("resource_root 不能与待整理目录或导航目录冲突")
    return parts[0]


def _clean_note_name(value: str, *, empty_message: str) -> str:
    raw = " ".join(value.split())
    if raw.lower().endswith(".md"):
        raw = raw[:-3].rstrip()
    clean = safe_title(raw)
    if not clean:
        raise ValueError(empty_message)
    return clean


def _available_path(directory: Path, filename: str, source: Path) -> Path:
    sequence = 1
    while True:
        candidate = directory / note_filename(filename, sequence)
        if candidate == source or not candidate.exists():
            return candidate
        sequence += 1


def _move_without_rewriting(source: Path, target: Path) -> None:
    if target == source:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    os.link(source, target)
    source.unlink()


def _resource_card_input(settings: Settings, card_path: Path) -> tuple[Path, str]:
    card = card_path.expanduser().resolve()
    runtime_root = settings.runtime_root.resolve()
    allowed_root = (runtime_root / RESOURCE_CARD_RUNTIME_DIR).resolve()
    if allowed_root not in card.parents:
        raise ValueError(f"资源卡草稿必须位于 runtime 目录：{allowed_root}")
    if not card.is_file():
        raise ValueError("资源卡草稿不存在")
    text = card.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("资源卡草稿不能为空")
    if len(text) > RESOURCE_CARD_MAX_CHARS:
        raise ValueError(f"资源卡草稿过长；上限为 {RESOURCE_CARD_MAX_CHARS} 字符，纯资源整理应保留功能、用途、获取方式和状态")
    return card, text


def _backup_original(settings: Settings, source: Path, bvid: str) -> Path:
    backup_dir = settings.runtime_root / ORGANIZE_BACKUP_RUNTIME_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_title(f"{source.stem}--{bvid}") or bvid
    sequence = 1
    while True:
        candidate = backup_dir / note_filename(stem, sequence)
        if not candidate.exists():
            shutil.copy2(source, candidate)
            return candidate
        sequence += 1


def _resource_card_block(source_text: str, bvid: str, card_text: str) -> tuple[str, str, str]:
    metadata, _ = parse_frontmatter(source_text)
    title_match = re.search(r"^#\s+(.+)$", source_text, re.MULTILINE)
    source_title = title_match.group(1).strip() if title_match else "原 B站资源分享"
    author = metadata.get("author", "")
    published = metadata.get("published", "")
    source_url = metadata.get("source", "")
    details = " · ".join(item for item in (author, published, bvid, source_url) if item)
    source_line = f"来源视频：{source_title}" + (f" · {details}" if details else "")

    key = hashlib.sha256(bvid.encode("utf-8")).hexdigest()[:16]
    start = f"<!-- BILI_RESOURCE_CARD_START:{key} -->"
    end = f"<!-- BILI_RESOURCE_CARD_END:{key} -->"
    provenance = f'<small class="resource-card-source">{html.escape(source_line)}</small>'
    block = f"{start}\n{card_text.rstrip()}\n\n{provenance}\n{end}"
    return start, end, block


def _merge_resource_collection(collection_path: Path, collection_title: str, start: str, end: str, block: str) -> tuple[str, bool]:
    if collection_path.is_file():
        current = collection_path.read_text(encoding="utf-8-sig")
        if RESOURCE_COLLECTION_MARKER not in current:
            raise ValueError(f"目标文件已存在但不是 bili-learning 资源集合页：{collection_path}")
        pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
        if pattern.search(current):
            return pattern.sub(block, current, count=1), True
        return current.rstrip() + "\n\n" + block + "\n", False

    return f"# {collection_title}\n\n{RESOURCE_COLLECTION_MARKER}\n\n{block}\n", False


def organize_note(
    settings: Settings,
    source: Path,
    filename: str,
    *,
    destination: str,
    confirmed_scope: str,
) -> Path:
    source = _validate_source_note(settings, source, confirmed_scope)
    notes_root = settings.notes_root.resolve()
    filename_clean = _clean_note_name(filename, empty_message="整理后的文件名不能为空")

    target_destination = _validated_destination(settings, destination)
    target = _available_path(notes_root.joinpath(*target_destination), filename_clean, source)
    _move_without_rewriting(source, target)
    build_navigation(settings)
    return target


def organize_resource_note(
    settings: Settings,
    source: Path,
    collection: str,
    *,
    card_path: Path,
    confirmed_scope: str,
) -> dict[str, object]:
    source = _validate_source_note(settings, source, confirmed_scope)
    source_text = source.read_text(encoding="utf-8-sig")
    if RESOURCE_COLLECTION_MARKER in source_text:
        raise ValueError("资源集合页不能再次作为纯资源笔记压缩")
    bvid = extract_bvid(source_text)
    if not bvid:
        raise ValueError("纯资源压缩要求原笔记包含可识别的 BVID，以便稳定更新同一资源卡")

    collection_clean = _clean_note_name(collection, empty_message="资源集合页名称不能为空")
    card, card_text = _resource_card_input(settings, card_path)
    start, end, block = _resource_card_block(source_text, bvid, card_text)

    notes_root = settings.notes_root.resolve()
    collection_path = notes_root / _resource_root(settings) / note_filename(collection_clean)
    if collection_path.resolve() == source:
        raise ValueError("资源集合页不能与待压缩的原笔记是同一个文件")
    before_collection = collection_path.read_text(encoding="utf-8-sig") if collection_path.is_file() else None
    merged, updated_existing_card = _merge_resource_collection(collection_path, collection_clean, start, end, block)

    backup_path = _backup_original(settings, source, bvid)
    collection_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(collection_path, merged)
    try:
        source.unlink()
    except Exception:
        if before_collection is None:
            if collection_path.is_file():
                collection_path.unlink()
        else:
            atomic_write(collection_path, before_collection)
        raise

    card_cleanup_warning: str | None = None
    try:
        card.unlink()
    except OSError as error:
        card_cleanup_warning = str(error)

    build_navigation(settings)
    return {
        "bvid": bvid,
        "collection_path": collection_path,
        "backup_path": backup_path,
        "updated_existing_card": updated_existing_card,
        "card_cleanup_warning": card_cleanup_warning,
    }
