from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath

from .config import Settings
from .navigation import build_navigation
from .note_template import note_filename, safe_title

ORGANIZE_SCOPES = {"single", "latest", "all"}


def _extract_bvid(text: str) -> str | None:
    patterns = (
        r"player\.html\?bvid=(BV[0-9A-Za-z]+)",
        r"bilibili\.com/video/(BV[0-9A-Za-z]+)",
        r"\b(BV[0-9A-Za-z]{8,})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def find_duplicate_bvid_notes(settings: Settings, source: Path) -> tuple[str | None, list[Path]]:
    source_resolved = source.resolve()
    if not source_resolved.is_file():
        return None, []
    text = source_resolved.read_text(encoding="utf-8-sig")
    bvid = _extract_bvid(text)
    if not bvid:
        return None, []

    notes_root = settings.notes_root.resolve()
    navigation_root = (notes_root / settings.navigation_dir).resolve()
    duplicates: list[Path] = []
    for candidate in notes_root.rglob("*.md"):
        resolved = candidate.resolve()
        if resolved == source_resolved or resolved == navigation_root or navigation_root in resolved.parents:
            continue
        try:
            candidate_text = resolved.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        if _extract_bvid(candidate_text) == bvid:
            duplicates.append(resolved)
    duplicates.sort(key=lambda path: str(path).lower())
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


def organize_note(
    settings: Settings,
    source: Path,
    filename: str,
    *,
    destination: str,
    confirmed_scope: str,
) -> Path:
    source = source.resolve()
    _validate_confirmed_scope(settings, source, confirmed_scope)
    notes_root = settings.notes_root.resolve()
    if source == notes_root or notes_root not in source.parents or not source.is_file():
        raise ValueError("待整理笔记必须是 notes_root 内的现有 Markdown 文件")
    navigation_root = (notes_root / settings.navigation_dir).resolve()
    if source.parent == navigation_root or navigation_root in source.parents:
        raise ValueError("导航文件不能作为整理对象")

    raw_filename = " ".join(filename.split())
    if raw_filename.lower().endswith(".md"):
        raw_filename = raw_filename[:-3].rstrip()
    filename_clean = safe_title(raw_filename)
    if not filename_clean:
        raise ValueError("整理后的文件名不能为空")

    target_destination = _validated_destination(settings, destination)
    target = _available_path(notes_root.joinpath(*target_destination), filename_clean, source)
    _move_without_rewriting(source, target)
    build_navigation(settings)
    return target
