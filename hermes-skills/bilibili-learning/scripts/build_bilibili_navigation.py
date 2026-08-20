#!/usr/bin/env python3
"""Generate Obsidian navigation pages from the Bilibili note taxonomy."""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TAXONOMY = Path(os.environ.get("BILI_LEARNING_TAXONOMY", str(PROJECT_ROOT / "config" / "bilibili-note-taxonomy.json")))


def load_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return {"title": path.stem, "tags": []}
    frontmatter = match.group(1)
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    tags_match = re.search(r"(?ms)^tags:\s*\n((?:\s+-\s+.*\r?\n?)*)", frontmatter)
    tags = [item.strip() for item in re.findall(r"(?m)^\s+-\s+(.+)$", tags_match.group(1) if tags_match else "")]
    return {"title": title_match.group(1).strip() if title_match else path.stem, "tags": tags}


def write_page(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    config = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    configured_root = Path(config["notes_root"])
    root = configured_root if configured_root.is_absolute() else PROJECT_ROOT / configured_root
    nav_dir = root / config["navigation_dir"]
    nav_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []
    for note in root.rglob("*.md"):
        if nav_dir in note.parents:
            continue
        relative = note.relative_to(root)
        data = load_frontmatter(note)
        entries.append({"path": relative.with_suffix(""), "title": data["title"], "tags": data["tags"], "category": relative.parent})
    entries.sort(key=lambda item: (str(item["category"]), str(item["title"])))
    by_top: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_model: dict[str, list[dict[str, object]]] = defaultdict(list)
    model_names = {model["canonical"] for model in config["models"]}
    for entry in entries:
        top = entry["category"].parts[0] if entry["category"].parts else "00-待整理"
        by_top[top].append(entry)
        for tag in entry["tags"]:
            if tag in model_names:
                by_model[tag].append(entry)
    index_lines = ["# B站学习笔记导航", "", "## 按领域", ""]
    for category in sorted(by_top):
        page = f"{category}.md"
        index_lines.append(f"- [[99-导航/{category}|{category}]]（{len(by_top[category])}）")
        lines = [f"# {category}", ""]
        for entry in by_top[category]:
            lines.append(f"- [[{entry['path']}|{entry['title']}]]")
        write_page(nav_dir / page, "\n".join(lines) + "\n")
    index_lines.extend(["", "## 按模型", ""])
    for model in sorted(by_model):
        index_lines.append(f"- [[99-导航/模型索引#{model}|{model}]]（{len(by_model[model])}）")
    write_page(nav_dir / "首页.md", "\n".join(index_lines) + "\n")
    model_lines = ["# 模型索引", ""]
    for model in sorted(by_model):
        model_lines.append(f"## {model}\n")
        for entry in by_model[model]:
            model_lines.append(f"- [[{entry['path']}|{entry['title']}]]")
        model_lines.append("")
    write_page(nav_dir / "模型索引.md", "\n".join(model_lines))


if __name__ == "__main__":
    main()
