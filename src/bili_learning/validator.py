from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .frontmatter import DEFAULT_CSSCLASSES, parse_frontmatter, parse_frontmatter_list
from .note_template import AI_MARKERS, PLACEHOLDER_TEXT, bvid_line, quote_description
from .quality import load_analysis_report, validate_analysis_report

ALLOWED_FRONTMATTER_FIELDS = {"author", "published", "duration", "source", "tags", "cssclasses"}


def validate_note(note: Path, job: dict[str, Any]) -> list[str]:
    if not note.is_file():
        return ["笔记文件不存在"]
    text = note.read_text(encoding="utf-8")
    errors: list[str] = []

    if job.get("schema_version") != 1:
        errors.append("不支持的 job schema_version")

    expected_path = Path(job.get("draft_path", job["note_path"]))
    if note.resolve() != expected_path.resolve():
        errors.append("笔记路径不符合分类规范")
    expected_name = job["note_filename"]
    if note.name != expected_name:
        errors.append("文件名不符合唯一命名规范")

    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if not title_match or title_match.group(1).strip() != job["canonical_title"]:
        errors.append("H1 不符合原视频标题")
    if bvid_line(job["bvid"]) not in text:
        errors.append("缺少 BVID 小字标识")

    values, tags = parse_frontmatter(text)
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
    cssclasses = parse_frontmatter_list(text, "cssclasses")
    missing_cssclasses = [cssclass for cssclass in DEFAULT_CSSCLASSES if cssclass not in cssclasses]
    if missing_cssclasses:
        errors.append("缺少必需 cssclasses：" + ", ".join(missing_cssclasses))

    description_block = quote_description(job.get("description", ""), job["description_status"])
    description_at = text.find(description_block)
    iframe_url = "https://player.bilibili.com/player.html?bvid=" + job["bvid"]
    iframe_at = text.find(iframe_url)
    summary_at = text.find(AI_MARKERS["summary"][0])
    body_at = text.find(AI_MARKERS["body"][0])
    if description_at < 0:
        errors.append("视频简介未按采集结果完整保留")
    if iframe_at < 0:
        errors.append("缺少正确的官方播放器 iframe")
    if min(summary_at, iframe_at, body_at, description_at) >= 0 and not (
        summary_at < iframe_at < body_at < description_at
    ):
        errors.append("阅读顺序必须为先看结论 → 播放器 → 知识正文 → 视频资料")

    for key, (start, end) in AI_MARKERS.items():
        start_at = text.find(start)
        end_at = text.find(end)
        if start_at < 0 or end_at < 0 or end_at <= start_at:
            errors.append(f"AI 内容区域损坏：{key}")
            continue
        region = text[start_at + len(start) : end_at]
        if PLACEHOLDER_TEXT in region or not region.strip():
            errors.append(f"AI 内容区域尚未完成：{key}")

    if "[!summary] 先看结论" not in text:
        errors.append("缺少先看结论")

    try:
        report = load_analysis_report(Path(job["analysis_path"]))
        errors.extend(validate_analysis_report(report))
        if report.get("source_assessment", {}).get("status") == "insufficient":
            errors.append("来源不足，拒绝发布正式学习笔记")
    except (KeyError, ValueError) as error:
        errors.append(str(error))

    forbidden = (".runtime", "agent_handoff.md", "job.json", "analysis.json", "字幕证据索引")
    for token in forbidden:
        if token in text:
            errors.append(f"主笔记包含机器内部信息：{token}")
    return errors
