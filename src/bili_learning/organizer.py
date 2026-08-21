from __future__ import annotations

import os
import re
import uuid
from pathlib import Path, PurePosixPath

from .config import Settings
from .frontmatter import parse_frontmatter
from .navigation import build_navigation
from .note_template import bvid_line, note_filename, quote_description, safe_title


def _safe_category(value: str) -> tuple[str, ...]:
    path = PurePosixPath(value.replace("\\", "/"))
    parts = path.parts
    if path.is_absolute() or not parts or any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise ValueError("整理目录必须是笔记根目录下的相对路径")
    return tuple(parts)


def _suggest_category(settings: Settings, tags: list[str]) -> tuple[str, ...]:
    tag_set = set(tags)
    candidates = [
        route
        for route in settings.taxonomy["routes"]
        if set(route["tags"]).issubset(tag_set)
    ]
    if not candidates:
        return tuple(settings.taxonomy["fallback"]["path"])
    best = max(candidates, key=lambda route: len(route["tags"]))
    return tuple(best["path"])


def _available_path(directory: Path, title: str, source: Path) -> Path:
    sequence = 1
    while True:
        candidate = directory / note_filename(title, sequence)
        if candidate == source or not candidate.exists():
            return candidate
        sequence += 1


def _upgrade_legacy_description(text: str) -> str:
    pattern = r"^> \*\*视频简介\*\*\r?\n>\r?\n(?P<body>.*?)(?=\r?\n\r?\n<iframe)"
    match = re.search(pattern, text, flags=re.DOTALL | re.MULTILINE)
    if not match:
        return text
    raw = "\n".join(re.sub(r"^> ?", "", line) for line in match.group("body").splitlines()).strip()
    if not raw:
        raise ValueError("旧笔记的视频简介为空，无法整理")
    return text[: match.start()] + quote_description(raw, "present") + text[match.end() :]


def _rewrite_title_and_intro(text: str, title: str, intro: str) -> str:
    text = _upgrade_legacy_description(text)
    bvid_match = re.search(r"player\.html\?bvid=(BV[0-9A-Za-z]+)", text)
    if not bvid_match:
        raise ValueError("笔记缺少播放器 BVID，无法整理")
    result, count = re.subn(
        r"^#\s+.+$(?:\r?\n\r?\n<small>BV号：[^<]+</small>)?",
        f"# {title}\n\n{bvid_line(bvid_match.group(1))}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError("笔记缺少 H1，无法整理")
    pattern = r"(^## 视频简介\r?\n\r?\n)(.*?)(?=\r?\n\r?\n## |\Z)"
    result, count = re.subn(pattern, lambda match: match.group(1) + intro, result, count=1, flags=re.DOTALL | re.MULTILINE)
    if count != 1:
        raise ValueError("笔记缺少标准视频简介，无法整理")
    return result


def _publish_reorganized(source: Path, target: Path, content: str) -> None:
    if target == source:
        temporary = source.with_name(f".{source.name}.{uuid.uuid4().hex}.organizing")
        temporary.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temporary, source)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.organizing")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        os.link(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    source.unlink()


def organize_note(settings: Settings, source: Path, title: str, intro: str, category: str | None = None) -> Path:
    source = source.resolve()
    notes_root = settings.notes_root.resolve()
    if source == notes_root or notes_root not in source.parents or not source.is_file():
        raise ValueError("待整理笔记必须是 notes_root 内的现有 Markdown 文件")
    if source.parent == (notes_root / settings.navigation_dir).resolve() or (notes_root / settings.navigation_dir).resolve() in source.parents:
        raise ValueError("导航文件不能作为整理对象")
    title = safe_title(" ".join(title.split()))
    intro = " ".join(intro.split())
    if not intro:
        raise ValueError("简介摘要不能为空")
    text = source.read_text(encoding="utf-8")
    _, tags = parse_frontmatter(text)
    target_category = _safe_category(category) if category else _suggest_category(settings, tags)
    target = _available_path(notes_root.joinpath(*target_category), title, source)
    updated = _rewrite_title_and_intro(text, title, intro)
    _publish_reorganized(source, target, updated)
    build_navigation(settings)
    return target
