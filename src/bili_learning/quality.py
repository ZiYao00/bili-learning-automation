from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ANALYSIS_SCHEMA_VERSION = 1
SOURCE_STATUSES = {"pending", "sufficient", "insufficient"}
REVIEW_STATUSES = {"pending", "passed", "not_applicable"}


def analysis_report_template() -> dict[str, Any]:
    """Return the runtime-only quality report template filled by the agent."""
    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "source_assessment": {
            "status": "pending",
            "reason": "",
        },
        "knowledge_outline": [],
        "coverage_review": {
            "status": "pending",
            "notes": "",
        },
    }


def write_analysis_template(path: Path) -> None:
    path.write_text(
        json.dumps(analysis_report_template(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_analysis_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError("缺少运行时内容质量报告")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError("无法读取内容质量报告") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("内容质量报告不是有效 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("内容质量报告必须是 JSON 对象")
    return payload


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_analysis_report(report: dict[str, Any]) -> list[str]:
    """Validate workflow state only; semantic quality remains the agent's responsibility."""
    errors: list[str] = []
    if report.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
        errors.append("内容质量报告 schema_version 不受支持")

    source = report.get("source_assessment")
    if not isinstance(source, dict):
        errors.append("缺少 source_assessment")
        return errors

    source_status = source.get("status")
    if source_status not in SOURCE_STATUSES:
        errors.append("source_assessment.status 无效")
    if source_status == "pending":
        errors.append("来源充分性尚未判断")
    if source_status in {"sufficient", "insufficient"} and not _nonempty_text(source.get("reason")):
        errors.append("来源充分性判断缺少 reason")

    outline = report.get("knowledge_outline")
    if not isinstance(outline, list) or any(not _nonempty_text(item) for item in outline):
        errors.append("knowledge_outline 必须是字符串列表")
        outline = []

    review = report.get("coverage_review")
    if not isinstance(review, dict):
        errors.append("缺少 coverage_review")
        return errors

    review_status = review.get("status")
    if review_status not in REVIEW_STATUSES:
        errors.append("coverage_review.status 无效")

    if source_status == "sufficient":
        if not outline:
            errors.append("来源充分时必须先形成 knowledge_outline")
        if review_status != "passed":
            errors.append("来源充分时必须完成 coverage_review")
        if review_status == "passed" and not _nonempty_text(review.get("notes")):
            errors.append("coverage_review 通过时必须填写 notes")
    elif source_status == "insufficient" and review_status != "not_applicable":
        errors.append("来源不足时 coverage_review.status 应为 not_applicable")

    return errors
