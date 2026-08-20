from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import Settings


def load_note_metadata(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    frontmatter = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    tags: list[str] = []
    if frontmatter:
        tags_match = re.search(r"(?ms)^tags:\s*\n((?:\s+-\s+.*\r?\n?)*)", frontmatter.group(1))
        if tags_match:
            tags = [item.strip() for item in re.findall(r"(?m)^\s+-\s+(.+)$", tags_match.group(1))]
    return {"title": title_match.group(1).strip() if title_match else path.stem, "tags": tags}


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temp, path)


def build_navigation(settings: Settings) -> None:
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
        for tag in entry["tags"]:
            if tag in model_names:
                by_model[tag].append(entry)

    index_lines = ["# B站视频转笔记导航", "", "## 按领域", ""]
    for category in sorted(by_top):
        index_lines.append(f"- [[{settings.navigation_dir}/{category}|{category}]]（{len(by_top[category])}）")
        lines = [f"# {category}", ""]
        for entry in by_top[category]:
            lines.append(f"- [[{entry['path']}|{entry['title']}]]")
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
            model_lines.append(f"- [[{entry['path']}|{entry['title']}]]")
        model_lines.append("")
    atomic_write(nav_dir / "模型索引.md", "\n".join(model_lines))
