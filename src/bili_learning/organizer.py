from __future__ import annotations

import html
import os
import re
import uuid
from pathlib import Path, PurePosixPath

from .config import Settings
from .frontmatter import yaml_scalar
from .navigation import build_navigation
from .note_template import bvid_line, note_filename, render_video_materials, safe_title

ORGANIZE_SCOPES = {"latest", "all"}


def _safe_category(value: str) -> tuple[str, ...]:
    path = PurePosixPath(value.replace("\\", "/"))
    parts = path.parts
    if path.is_absolute() or not parts or any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise ValueError("整理目录必须是笔记根目录下的相对路径")
    return tuple(parts)


def _allowed_categories(settings: Settings) -> set[tuple[str, ...]]:
    organization = settings.taxonomy.get("organization") or {}
    configured = organization.get("categories")
    if configured:
        return {tuple(category) for category in configured}
    return {tuple(route["path"]) for route in settings.taxonomy["routes"]}


def _validated_category(settings: Settings, value: str) -> tuple[str, ...]:
    category = _safe_category(value)
    if category not in _allowed_categories(settings):
        raise ValueError("整理目录不在 taxonomy.organization.categories 允许范围内")
    return category


def _normalize_tags(values: list[str]) -> list[str]:
    tags: list[str] = []
    for raw in values:
        tag = " ".join(str(raw).split())
        if not tag or tag == "待整理" or tag in tags:
            continue
        tags.append(tag)
    if not tags:
        raise ValueError("整理后的 tags 不能为空")
    return tags


def _rewrite_frontmatter_tags(text: str, tags: list[str]) -> str:
    match = re.match(r"^---\r?\n(?P<body>.*?)\r?\n---\r?\n", text, flags=re.DOTALL)
    if not match:
        raise ValueError("笔记缺少 Frontmatter，无法整理 tags")

    lines = match.group("body").splitlines()
    start = next((index for index, line in enumerate(lines) if line.strip() == "tags:"), None)
    replacement = ["tags:", *[f"  - {yaml_scalar(tag)}" for tag in tags]]

    if start is None:
        insert_at = next((index for index, line in enumerate(lines) if line.strip() == "cssclasses:"), len(lines))
        lines[insert_at:insert_at] = replacement
    else:
        end = start + 1
        while end < len(lines):
            line = lines[end]
            if not line.startswith((" ", "\t")) and re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*", line):
                break
            end += 1
        lines[start:end] = replacement

    return text[: match.start("body")] + "\n".join(lines) + text[match.end("body") :]


def _preserve_original_video_title(text: str) -> str:
    if 'class="video-note-original-title"' in text:
        return text

    h1_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    if not h1_match:
        raise ValueError("笔记缺少 H1，无法保留原视频标题")
    original_title = h1_match.group(1).strip()
    original_line = (
        '<small class="video-note-original-title"><strong>原视频标题</strong>：'
        + html.escape(original_title)
        + "</small>"
    )

    meta_match = re.search(r'^<small class="video-note-meta">.*?</small>$', text, flags=re.MULTILINE)
    if meta_match:
        return text[: meta_match.end()] + f"\n\n{original_line}" + text[meta_match.end() :]

    bvid_match = re.search(r"^<small>BV号：[^<]+</small>$", text, flags=re.MULTILINE)
    if bvid_match:
        return text[: bvid_match.end()] + f"\n\n{original_line}" + text[bvid_match.end() :]

    return text[: h1_match.end()] + f"\n\n{original_line}" + text[h1_match.end() :]


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
    iframe_match = re.search(r"<iframe\b.*?</iframe>", text[match.end() :], flags=re.DOTALL | re.IGNORECASE)
    if not iframe_match:
        raise ValueError("旧笔记缺少播放器，无法整理")
    iframe_text = iframe_match.group(0)
    bvid_match = re.search(r"player\.html\?bvid=(BV[0-9A-Za-z]+)", iframe_text)
    if not bvid_match:
        raise ValueError("旧笔记播放器缺少 BVID，无法整理")
    materials = render_video_materials(
        {
            "bvid": bvid_match.group(1),
            "description": raw,
            "description_status": "present",
            "resource_access_notices": [],
        }
    )
    iframe_end = match.end() + iframe_match.end()
    return text[: match.start()] + materials + text[iframe_end:]


def _rewrite_title_and_intro(text: str, title: str, intro: str) -> str:
    text = _upgrade_legacy_description(text)
    text = _preserve_original_video_title(text)
    bvid_match = re.search(r"player\.html\?bvid=(BV[0-9A-Za-z]+)", text)
    if not bvid_match:
        raise ValueError("笔记缺少播放器 BVID，无法整理")

    result, count = re.subn(r"^#\s+.+$", f"# {title}", text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("笔记缺少 H1，无法整理")
    if "video-note-meta" not in result and not re.search(r"<small>BV号：[^<]+</small>", result):
        result = re.sub(
            r"^(#\s+.+)$",
            lambda match: match.group(1) + f"\n\n{bvid_line(bvid_match.group(1))}",
            result,
            count=1,
            flags=re.MULTILINE,
        )

    overview_pattern = r'(<p class="video-note-overview"><strong>视频简介</strong>：)(.*?)(</p>)'
    result, count = re.subn(
        overview_pattern,
        lambda match: match.group(1) + html.escape(intro) + match.group(3),
        result,
        count=1,
        flags=re.DOTALL,
    )
    if count == 1:
        return result

    patterns = (
        r"(^### 视频简介\r?\n\r?\n)(.*?)(?=\r?\n\r?\n### |\r?\n\r?\n<details|\r?\n\r?\n## |\Z)",
        r"(^## 视频简介\r?\n\r?\n)(.*?)(?=\r?\n\r?\n## |\r?\n\r?\n<details|\Z)",
    )
    for pattern in patterns:
        result, count = re.subn(
            pattern,
            lambda match: match.group(1) + intro,
            result,
            count=1,
            flags=re.DOTALL | re.MULTILINE,
        )
        if count == 1:
            return result

    details_marker = '<details class="video-note-source-details">'
    details_at = result.find(details_marker)
    compact_intro = f'<p class="video-note-overview"><strong>视频简介</strong>：{html.escape(intro)}</p>'
    if details_at >= 0:
        return result[:details_at].rstrip() + f"\n\n{compact_intro}\n\n" + result[details_at:]

    if 'player.bilibili.com/player.html?bvid=' in result:
        return result.rstrip() + f"\n\n{compact_intro}\n"

    raise ValueError("笔记缺少标准播放器与来源区，无法整理")


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


def organize_note(
    settings: Settings,
    source: Path,
    title: str,
    intro: str,
    *,
    category: str,
    tags: list[str],
    confirmed_scope: str,
) -> Path:
    if confirmed_scope not in ORGANIZE_SCOPES:
        raise ValueError("整理功能默认不执行；执行前必须由用户明确选择最近一篇（latest）或全部（all）")

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
    target_category = _validated_category(settings, category)
    normalized_tags = _normalize_tags(tags)

    text = source.read_text(encoding="utf-8")
    target = _available_path(notes_root.joinpath(*target_category), title, source)
    updated = _rewrite_title_and_intro(text, title, intro)
    updated = _rewrite_frontmatter_tags(updated, normalized_tags)
    _publish_reorganized(source, target, updated)
    build_navigation(settings)
    return target
