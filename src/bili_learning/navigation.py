from __future__ import annotations

import html
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import Settings
from .frontmatter import parse_frontmatter
from .runtime import waiting_file_lock

NAVIGATION_LOCK_TIMEOUT_SECONDS = 30.0


def load_note_metadata(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8-sig")
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    meta_match = re.search(r'^<small class="video-note-meta">(.*?)</small>$', text, re.MULTILINE)
    marker = ""
    if meta_match:
        marker_match = re.match(r"\s*(\([^()]{1,40}\))\s+", html.unescape(meta_match.group(1)))
        if marker_match:
            marker = marker_match.group(1).strip()
    _, tags = parse_frontmatter(text)
    title = title_match.group(1).strip() if title_match else path.stem
    display_title = f"{title} {marker}" if marker else title
    return {"title": title, "display_title": display_title, "tags": tags}


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temp, path)


def build_navigation(settings: Settings) -> None:
    lock_path = settings.runtime_root / "locks" / "navigation.lock"
    with waiting_file_lock(lock_path, timeout_seconds=NAVIGATION_LOCK_TIMEOUT_SECONDS):
        _build_navigation(settings)


def _build_navigation(settings: Settings) -> None:
    root = settings.notes_root
    nav_dir = root / settings.navigation_dir
    nav_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    if root.is_dir():
        for note in root.rglob("*.md"):
            if nav_dir in note.parents:
                continue
            relative = note.relative_to(root)
            data = load_note_metadata(note)
            entries.append(
                {
                    "path": relative.with_suffix(""),
                    "title": data["title"],
                    "display_title": data["display_title"],
                    "tags": data["tags"],
                    "category": relative.parent,
                }
            )
    entries.sort(key=lambda item: (str(item["category"]), str(item["title"]), str(item["path"])))

    by_top: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    model_names = {model["canonical"] for model in settings.taxonomy["models"]}
    for entry in entries:
        category: Path = entry["category"]
        top = category.parts[0] if category.parts else "00-待整理"
        by_top[top].append(entry)

        object_name = category.parts[1] if len(category.parts) >= 2 else ""
        if object_name in model_names:
            by_model[object_name].append(entry)
            continue

        for tag in entry["tags"]:
            if tag in model_names:
                by_model[tag].append(entry)

    inbox_category = settings.taxonomy["fallback"]["path"][0]
    index_lines = ["# B站视频转笔记导航", "", "## 按领域", ""]
    for category in sorted(set(by_top) | {inbox_category}):
        index_lines.append(f"- [[{settings.navigation_dir}/{category}|{category}]]（{len(by_top[category])}）")
        lines = [f"# {category}", ""]
        if by_top[category]:
            for entry in by_top[category]:
                lines.append(f"- [[{entry['path']}|{entry['display_title']}]]")
        else:
            lines.append("暂无待整理笔记。")
        atomic_write(nav_dir / f"{category}.md", "\n".join(lines) + "\n")

    index_lines.extend(["", "## 按模型", ""])
    for model in sorted(by_model):
        index_lines.append(
            f"- [[{settings.navigation_dir}/模型索引#{model}|{model}]]（{len(by_model[model])}）"
        )
    atomic_write(nav_dir / "首页.md", "\n".join(index_lines) + "\n")

    model_lines = ["# 模型索引", ""]
    for model in sorted(by_model):
        model_lines.append(f"## {model}\n")
        for entry in by_model[model]:
            model_lines.append(f"- [[{entry['path']}|{entry['display_title']}]]")
        model_lines.append("")
    atomic_write(nav_dir / "模型索引.md", "\n".join(model_lines))
