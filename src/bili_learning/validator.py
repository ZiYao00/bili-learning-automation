from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .note_template import AI_MARKERS, PLACEHOLDER_TEXT, note_filename, quote_description

ALLOWED_FRONTMATTER_FIELDS = {"author", "published", "duration", "source", "tags"}


def _parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return {}, []
    block = match.group(1)
    values: dict[str, str] = {}
    tags: list[str] = []
    active_key: str | None = None
    for raw in block.splitlines():
        if raw.startswith("  - ") and active_key == "tags":
            tags.append(raw[4:].strip())
            continue
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", raw)
        if field:
            active_key = field.group(1)
            values[active_key] = field.group(2).strip()
        elif raw.strip():
            active_key = None
    return values, tags


def validate_note(note: Path, job: dict[str, Any]) -> list[str]:
    if not note.is_file():
        return ["笔记文件不存在"]
    text = note.read_text(encoding="utf-8")
    errors: list[str] = []

    expected_path = Path(job["note_path"])
    if note.resolve() != expected_path.resolve():
        errors.append("笔记路径不符合分类规范")
    expected_name = note_filename(job["canonical_title"], job["bvid"])
    if note.name != expected_name:
        errors.append("文件名不符合唯一命名规范")

    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if not title_match or title_match.group(1).strip() != job["canonical_title"]:
        errors.append("H1 不符合标准短标题")

    values, tags = _parse_frontmatter(text)
    actual_fields = set(values)
    if actual_fields != ALLOWED_FRONTMATTER_FIELDS:
        missing = sorted(ALLOWED_FRONTMATTER_FIELDS - actual_fields)
        extra = sorted(actual_fields - ALLOWED_FRONTMATTER_FIELDS)
        if missing:
            errors.append("缺少 Frontmatter 字段：" + ", ".join(missing))
        if extra:
            errors.append("存在不允许的 Frontmatter 字段：" + ", ".join(extra))
    expected_values = {
        "author": str(job["author"]),
        "published": str(job["published"]),
        "duration": str(job["duration"]),
        "source": str(job["canonical_url"]),
    }
    for field, expected in expected_values.items():
        if values.get(field) != expected:
            errors.append(f"Frontmatter {field} 与采集元数据不一致")
    for tag in job.get("required_tags", []):
        if tag not in tags:
            errors.append(f"缺少规范标签：{tag}")

    description_block = quote_description(job.get("description", ""), job["description_status"])
    description_at = text.find(description_block)
    iframe_url = "https://player.bilibili.com/player.html?bvid=" + job["bvid"]
    iframe_at = text.find(iframe_url)
    if description_at < 0:
        errors.append("视频简介未按采集结果完整保留")
    if iframe_at < 0:
        errors.append("缺少正确的官方播放器 iframe")
    elif description_at >= 0 and description_at > iframe_at:
        errors.append("视频简介没有放在播放器之前")

    for key, (start, end) in AI_MARKERS.items():
        start_at = text.find(start)
        end_at = text.find(end)
        if start_at < 0 or end_at < 0 or end_at <= start_at:
            errors.append(f"AI 内容区域损坏：{key}")
            continue
        region = text[start_at + len(start) : end_at]
        if PLACEHOLDER_TEXT in region or not region.strip():
            errors.append(f"AI 内容区域尚未完成：{key}")

    for heading in ("## 怎么做", "## 容易踩坑"):
        if heading not in text:
            errors.append(f"缺少章节：{heading}")
    if "[!summary] 先看结论" not in text:
        errors.append("缺少先看结论")
    if "**我来实践**" not in text:
        errors.append("缺少实践清单")

    forbidden = (".runtime", "agent_handoff.md", "job.json", "字幕证据索引")
    for token in forbidden:
        if token in text:
            errors.append(f"主笔记包含机器内部信息：{token}")
    return errors
