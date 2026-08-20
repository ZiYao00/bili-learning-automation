from __future__ import annotations

import re
from pathlib import Path
from typing import Any

PLACEHOLDER_TEXT = "待 Hermes 根据字幕填写"

AI_MARKERS = {
    "summary": ("<!-- BILI_AI_SUMMARY_START -->", "<!-- BILI_AI_SUMMARY_END -->"),
    "steps": ("<!-- BILI_AI_STEPS_START -->", "<!-- BILI_AI_STEPS_END -->"),
    "pitfalls": ("<!-- BILI_AI_PITFALLS_START -->", "<!-- BILI_AI_PITFALLS_END -->"),
    "practice": ("<!-- BILI_AI_PRACTICE_START -->", "<!-- BILI_AI_PRACTICE_END -->"),
}


def safe_title(value: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", value).strip().rstrip(".")
    return name or "Bilibili 学习笔记"


def note_filename(canonical_title: str, bvid: str) -> str:
    return f"{safe_title(canonical_title)}__{bvid}.md"


def quote_description(description: str, status: str) -> str:
    if status == "confirmed_empty":
        return "> **视频简介**\n>\n> 本视频未提供简介。"
    if status != "present":
        raise ValueError("简介状态不是可生成笔记的状态")
    lines = description.splitlines() or [description]
    quoted = ["> **视频简介**", ">"]
    quoted.extend("> " + line if line else ">" for line in lines)
    return "\n".join(quoted)


def render_note_skeleton(job: dict[str, Any]) -> str:
    tags = "\n".join(f"  - {tag}" for tag in job["required_tags"])
    description = quote_description(job["description"], job["description_status"])
    bvid = job["bvid"]
    return (
        "---\n"
        f"author: {job['author']}\n"
        f"published: {job['published']}\n"
        f"duration: {job['duration']}\n"
        f"source: {job['canonical_url']}\n"
        "tags:\n"
        f"{tags}\n"
        "---\n\n"
        f"# {job['canonical_title']}\n\n"
        f"{description}\n\n"
        "<iframe\n"
        f"  src=\"https://player.bilibili.com/player.html?bvid={bvid}&autoplay=0&danmaku=0\"\n"
        "  style=\"width:100%;aspect-ratio:16/9;border:0;\"\n"
        "  allowfullscreen>\n"
        "</iframe>\n\n"
        f"{AI_MARKERS['summary'][0]}\n"
        "> [!summary] 先看结论\n"
        f"> {PLACEHOLDER_TEXT}。\n"
        f"{AI_MARKERS['summary'][1]}\n\n"
        f"{AI_MARKERS['steps'][0]}\n"
        "## 怎么做\n\n"
        "待 Hermes 根据字幕填写。\n"
        f"{AI_MARKERS['steps'][1]}\n\n"
        f"{AI_MARKERS['pitfalls'][0]}\n"
        "## 容易踩坑\n\n"
        "待 Hermes 根据字幕填写。\n"
        f"{AI_MARKERS['pitfalls'][1]}\n\n"
        f"{AI_MARKERS['practice'][0]}\n"
        "**我来实践**\n\n"
        "- [ ] 待 Hermes 根据字幕填写。\n"
        f"{AI_MARKERS['practice'][1]}\n"
    )


def write_skeleton(path: Path, job: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"目标笔记已存在，拒绝覆盖：{path}")
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(render_note_skeleton(job), encoding="utf-8", newline="\n")
    temp.replace(path)
