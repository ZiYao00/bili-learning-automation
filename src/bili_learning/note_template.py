from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .frontmatter import render_frontmatter

PLACEHOLDER_TEXT = "待智能体根据字幕填写"

AI_MARKERS = {
    "summary": ("<!-- BILI_AI_SUMMARY_START -->", "<!-- BILI_AI_SUMMARY_END -->"),
    "body": ("<!-- BILI_AI_BODY_START -->", "<!-- BILI_AI_BODY_END -->"),
}

_URL_PATTERN = re.compile(r"https?://[^\s<>()]+")
_SEPARATOR_RE = re.compile(r"^[\s\-_=~*#·•—–]{5,}$")
_DECORATED_HEADING_RE = re.compile(r"^[\s\-_=~*#·•—–]{2,}(.+?)[\s\-_=~*#·•—–]{2,}$")
_SECTION_HEADINGS = {
    "国内站",
    "国际站",
    "涉及插件",
    "资料",
    "资源",
    "下载",
    "工作流",
    "模型",
    "整合包",
    "交流群",
    "网盘",
    "在线工作流区域",
    "本地工作流区域",
}
_SECTION_RESOURCE_TERMS = ("工作流", "模型", "提示词", "整合包", "下载", "插件", "资源", "资料", "网盘")


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


def metadata_line(job: dict[str, Any]) -> str:
    parts = [str(job.get("author") or "").strip(), str(job.get("published") or "").strip(), str(job.get("duration") or "").strip()]
    parts = [part for part in parts if part]
    parts.append(str(job["bvid"]))
    return '<small class="video-note-meta">' + " · ".join(html.escape(part) for part in parts) + "</small>"


def _resource_label(value: str) -> str:
    return value.strip().strip("⏺️•*-—:： \t")


def _normalize_heading(value: str) -> str:
    cleaned = html.unescape(value).strip()
    decorated = _DECORATED_HEADING_RE.match(cleaned)
    if decorated:
        cleaned = decorated.group(1).strip()
    return _resource_label(cleaned)


def _resource_platform(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host == "github.com" or host.endswith(".github.com"):
        return "GitHub"
    if host == "pan.quark.cn" or host.endswith(".pan.quark.cn"):
        return "夸克网盘"
    if host == "feishu.cn" or host.endswith(".feishu.cn"):
        return "飞书"
    return ""


def _append_platform(label: str, platform: str) -> str:
    aliases = {
        "GitHub": ("github",),
        "夸克网盘": ("夸克网盘", "夸克", "quark"),
        "飞书": ("飞书", "feishu"),
    }
    normalized_label = label.lower()
    if not platform or any(alias in normalized_label for alias in aliases.get(platform, (platform.lower(),))):
        return label
    return f"{label}（{platform}）"


def _display_resource_label(label: str, section: str, url: str) -> str:
    platform = _resource_platform(url)
    if section == "涉及插件":
        if platform == "GitHub" and not label.lower().startswith("github"):
            return f"GitHub 插件 · {label}"
        if not label.startswith("插件"):
            label = f"插件 · {label}"
        return _append_platform(label, platform)
    if section and section not in label and label in {"体验地址", "下载地址", "在线地址", "地址", "链接"}:
        label = f"{section} · {label}"
    return _append_platform(label, platform)


def _description_resources(description: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    previous_label = ""
    section = ""
    for raw_line in html.unescape(description).splitlines():
        urls = _URL_PATTERN.findall(raw_line)
        label = _resource_label(_URL_PATTERN.sub("", raw_line))
        heading = _normalize_heading(raw_line)
        if not urls:
            if heading:
                previous_label = heading
                if raw_line.strip().endswith(("：", ":")) or _DECORATED_HEADING_RE.match(raw_line.strip()):
                    section = heading
            continue
        for index, url in enumerate(urls, start=1):
            resource_name = label if label else previous_label
            resource_name = resource_name or f"UP 主资源 {len(candidates) + index}"
            candidates.append((_display_resource_label(resource_name, section, url), url))
        previous_label = ""

    resources: list[tuple[str, str]] = []
    index_by_url: dict[str, int] = {}
    for label, url in candidates:
        normalized_url = url.rstrip("/ ")
        existing = index_by_url.get(normalized_url)
        if existing is None:
            index_by_url[normalized_url] = len(resources)
            resources.append((label, url))
            continue
        old_label, old_url = resources[existing]
        if len(label) > len(old_label):
            resources[existing] = (label, old_url)
    return resources


def _markdown_resource_link(label: str, url: str) -> str:
    escaped_label = label.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    return f"- [{escaped_label}](<{url}>)"


def _is_section_like(line: str) -> bool:
    stripped = html.unescape(line).strip()
    if not stripped:
        return True
    if _SEPARATOR_RE.match(stripped):
        return True
    decorated = _DECORATED_HEADING_RE.match(stripped)
    if decorated:
        stripped = decorated.group(1).strip()
    if stripped.endswith(("：", ":")):
        return True
    normalized = _resource_label(stripped)
    if normalized in _SECTION_HEADINGS:
        return True
    if len(normalized) <= 28 and normalized.endswith(("区域", "专区", "合集", "地址", "链接")):
        return True
    if len(normalized) <= 28 and not re.search(r"[。！？!?]", normalized):
        hits = sum(term in normalized for term in _SECTION_RESOURCE_TERMS)
        if hits >= 2:
            return True
    return False


def _description_overview(description: str) -> str | None:
    for raw_line in html.unescape(description).splitlines():
        line = raw_line.strip()
        if not line or _SEPARATOR_RE.match(line):
            continue
        decorated = _DECORATED_HEADING_RE.match(line)
        if decorated:
            heading = _resource_label(decorated.group(1))
            if heading in _SECTION_HEADINGS or any(term in heading for term in _SECTION_RESOURCE_TERMS):
                break
            continue
        if _URL_PATTERN.search(line):
            break
        if line.endswith(("：", ":")):
            heading = _resource_label(line)
            if heading in _SECTION_HEADINGS or any(term in heading for term in _SECTION_RESOURCE_TERMS):
                break
            continue
        left, separator, _right = line.partition("：")
        if not separator:
            left, separator, _right = line.partition(":")
        if separator and any(term in _resource_label(left) for term in _SECTION_RESOURCE_TERMS):
            break
        if _is_section_like(line):
            break
        return line
    return None


def render_resource_access_notices(notices: list[dict[str, str]]) -> str:
    if not notices:
        return ""
    lines = ["**资料获取**", ""]
    for notice in notices:
        condition = html.escape(str(notice.get("condition") or "需按 UP 主说明操作"))
        resource = html.escape(str(notice.get("resource") or "附加资料"))
        source_kind = notice.get("source")
        source = "视频简介" if source_kind == "description" else ("ASR 转写" if source_kind == "asr" else "字幕")
        source_text = html.escape(str(notice.get("text") or "").strip())
        lines.extend(
            [
                f"> [!resource] {resource} · {condition}",
                f"> 来源：{source}；当前采集内容未包含该资料本体，本笔记不自行补写。",
            ]
        )
        if source_text:
            lines.append(f"> <small>原始说明：{source_text}</small>")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_video_materials(job: dict[str, Any]) -> str:
    description = str(job.get("description") or "")
    status = str(job["description_status"])
    if status not in {"present", "confirmed_empty"}:
        raise ValueError("简介状态不是可生成笔记的状态")

    bvid = str(job["bvid"])
    resources = _description_resources(description) if status == "present" else []
    overview = _description_overview(description) if status == "present" else None
    notices = list(job.get("resource_access_notices") or [])
    user_source = job.get("user_supplied_source")
    user_source = user_source if isinstance(user_source, dict) else {}
    user_source_label = str(user_source.get("label") or "用户补充材料").strip()
    user_source_text = str(user_source.get("text") or "").strip()
    user_resources = _description_resources(user_source_text) if user_source_text else []

    result = [f'<iframe class="video-note-player" src="https://player.bilibili.com/player.html?bvid={bvid}&autoplay=0&danmaku=0" allowfullscreen></iframe>']

    notice_block = render_resource_access_notices(notices)
    if notice_block:
        result.extend(["", notice_block])

    if resources:
        result.extend(["", "### UP 主资源", "", *[_markdown_resource_link(label, url) for label, url in resources]])

    if user_source_text:
        if user_resources:
            result.extend(
                [
                    "",
                    "### 用户补充资源",
                    "",
                    *[_markdown_resource_link(label, url) for label, url in user_resources],
                ]
            )
        result.extend(
            [
                "",
                '<details class="video-note-source-details">',
                f"<summary>用户补充来源（{html.escape(user_source_label)}，未与 B站简介合并）</summary>",
                "",
                html.escape(user_source_text),
                "",
                "</details>",
            ]
        )

    if overview:
        result.extend(["", f'<p class="video-note-overview"><strong>视频简介</strong>：{html.escape(overview)}</p>'])

    if status == "present":
        normalized_description = html.unescape(description)
        result.extend(
            [
                "",
                '<details class="video-note-source-details">',
                "<summary>UP 主原文（完整说明与链接）</summary>",
                "",
                html.escape(normalized_description),
                "",
                "</details>",
            ]
        )
    elif not resources and not notices:
        result.extend(["", '<small class="video-note-empty-description">UP 主未提供视频简介。</small>'])

    return "\n".join(result)


def quote_description(description: str, status: str) -> str:
    """Backward-compatible wrapper used by tests and validator helpers."""
    return render_video_materials(
        {
            "description": description,
            "description_status": status,
            "bvid": "BV_PLACEHOLDER",
            "resource_access_notices": [],
        }
    )


def render_note_skeleton(job: dict[str, Any]) -> str:
    materials = render_video_materials(job)
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
        f"{metadata_line(job)}\n\n"
        f"{AI_MARKERS['summary'][0]}\n"
        "> [!summary] 先看结论\n"
        f"> {PLACEHOLDER_TEXT}。\n"
        f"{AI_MARKERS['summary'][1]}\n\n"
        f"{materials}\n\n"
        f"{AI_MARKERS['body'][0]}\n"
        f"{PLACEHOLDER_TEXT}。根据视频实际内容组织知识正文；不要套固定章节。\n"
        f"{AI_MARKERS['body'][1]}\n"
    )


def write_skeleton(path: Path, job: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"目标笔记已存在，拒绝覆盖：{path}")
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(render_note_skeleton(job), encoding="utf-8", newline="\n")
    temp.replace(path)
