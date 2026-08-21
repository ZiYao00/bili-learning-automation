from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from .frontmatter import render_frontmatter

PLACEHOLDER_TEXT = "待智能体根据字幕填写"

AI_MARKERS = {
    "summary": ("<!-- BILI_AI_SUMMARY_START -->", "<!-- BILI_AI_SUMMARY_END -->"),
    "body": ("<!-- BILI_AI_BODY_START -->", "<!-- BILI_AI_BODY_END -->"),
}


def strip_ai_markers(text: str) -> str:
    """Remove runtime-only validation comments before publishing a note."""
    for start, end in AI_MARKERS.values():
        text = text.replace(start, "").replace(end, "")
    return re.sub(r"\n{3,}", "\n\n", text)


def safe_title(value: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", value).strip().rstrip(".")
    return name or "Bilibili 学习笔记"


def note_filename(title: str, sequence: int = 1) -> str:
    stem = safe_title(title)
    return f"{stem}.md" if sequence == 1 else f"{stem}（{sequence}）.md"


def bvid_line(bvid: str) -> str:
    return f"<small>BV号：{bvid}</small>"


_URL_PATTERN = re.compile(r"https?://[^\s<>()]+")


def _resource_label(value: str) -> str:
    return value.strip().strip("⏺️•*-—:： \t")


def _description_resources(description: str) -> list[tuple[str, str]]:
    resources: list[tuple[str, str]] = []
    previous_label = ""
    for raw_line in description.splitlines():
        urls = _URL_PATTERN.findall(raw_line)
        label = _resource_label(_URL_PATTERN.sub("", raw_line))
        if not urls:
            if label:
                previous_label = label
            continue
        for index, url in enumerate(urls, start=1):
            resource_name = label if label else previous_label
            resources.append((resource_name or f"UP 主资源 {len(resources) + index}", url))
        previous_label = ""
    return resources


def quote_description(description: str, status: str) -> str:
    if status == "confirmed_empty":
        return "## 视频资料\n\n### 视频简介\n\n本视频未提供简介。"
    if status != "present":
        raise ValueError("简介状态不是可生成笔记的状态")
    lines = [line.strip() for line in description.splitlines() if line.strip()]
    overview = next((line for line in lines if not _URL_PATTERN.search(line) and not line.endswith(("：", ":"))), "UP 主原始简介见下方。")
    resources = _description_resources(description)
    result = ["## 视频资料", "", "### 视频简介", "", overview]
    if resources:
        result.extend(["", "### UP 主资源", ""])
        result.extend(f"- [{label}]({url})" for label, url in resources)
    result.extend(
        [
            "",
            '<details class="video-note-source-details">',
            "<summary>UP 主原始简介</summary>",
            "",
            html.escape(description),
            "",
            "</details>",
        ]
    )
    return "\n".join(result)


def render_note_skeleton(job: dict[str, Any]) -> str:
    description = quote_description(job["description"], job["description_status"])
    bvid = job["bvid"]
    frontmatter = render_frontmatter(
        {
            "author": job["author"],
            "published": job["published"],
            "duration": job["duration"],
            "source": job["canonical_url"],
        },
        job["required_tags"],
    )
    return (
        f"{frontmatter}\n\n"
        f"# {job['canonical_title']}\n\n"
        f"{bvid_line(bvid)}\n\n"
        f"{AI_MARKERS['summary'][0]}\n"
        "> [!summary] 先看结论\n"
        f"> {PLACEHOLDER_TEXT}。\n"
        f"{AI_MARKERS['summary'][1]}\n\n"
        "<iframe\n"
        f"  src=\"https://player.bilibili.com/player.html?bvid={bvid}&autoplay=0&danmaku=0\"\n"
        "  style=\"width:100%;aspect-ratio:16/9;border:0;\"\n"
        "  allowfullscreen>\n"
        "</iframe>\n\n"
        f"{AI_MARKERS['body'][0]}\n"
        f"{PLACEHOLDER_TEXT}。根据视频实际内容组织知识正文；不要套固定章节。\n"
        f"{AI_MARKERS['body'][1]}\n\n"
        f"{description}\n"
    )


def write_skeleton(path: Path, job: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"目标笔记已存在，拒绝覆盖：{path}")
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(render_note_skeleton(job), encoding="utf-8", newline="\n")
    temp.replace(path)
