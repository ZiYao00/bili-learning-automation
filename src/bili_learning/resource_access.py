from __future__ import annotations

import html
import re
from pathlib import Path

_RESOURCE_TERMS = (
    "提示词模板",
    "工程文件",
    "项目文件",
    "配置文件",
    "整合包",
    "工作流",
    "模型文件",
    "提示词",
    "模板",
    "脚本",
    "插件",
    "资料",
    "文件",
    "资源",
)

_STRONG_ACTION_TERMS = (
    "领取",
    "获取",
    "获得",
    "拿到",
    "下载",
    "发送",
    "发给",
    "会发",
    "提供",
    "放在",
    "放到",
    "上传",
    "公布",
)

_METHOD_ACTION_TERMS = (*_STRONG_ACTION_TERMS, "回复", "留言", "私信", "进群", "加群")

_CONDITION_PATTERNS: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    ("三连", re.compile(r"(?:一键)?三连"), True),
    ("充电", re.compile(r"充电(?:用户|会员|专属)?"), True),
    ("点赞", re.compile(r"点赞"), True),
    ("投币", re.compile(r"投币"), True),
    ("收藏", re.compile(r"收藏"), True),
    ("关注", re.compile(r"关注"), True),
    ("评论/关键词", re.compile(r"评论(?:区)?|关键词|暗号"), False),
    ("私信", re.compile(r"私信"), False),
    ("进群", re.compile(r"进群|加群|群里"), False),
)

_SRT_TIMECODE_RE = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}")


def _compact_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _resource_term(text: str) -> str | None:
    return next((term for term in _RESOURCE_TERMS if term in text), None)


def _action_term(text: str, *, engagement_condition: bool) -> str | None:
    terms = _STRONG_ACTION_TERMS if engagement_condition else _METHOD_ACTION_TERMS
    return next((term for term in terms if term in text), None)


def _linked_engagement(text: str, match: re.Match[str], action: str) -> bool:
    tail = text[match.end() : match.end() + 32]
    clause = re.split(r"[。！？!?]", tail, maxsplit=1)[0]
    escaped_action = re.escape(action)
    relation = rf"^.{{0,4}}(?:后|之后|完成后|完后|以后|即可|就能|可以|才(?:能)?).{{0,16}}{escaped_action}"
    if re.search(relation, clause):
        return True
    direct = rf"^[，,、\s]{{0,3}}.{{0,6}}{escaped_action}"
    return bool(re.search(direct, clause))


def _notice_from_text(text: str, source: str) -> dict[str, str] | None:
    compact = _compact_text(text)
    if not compact:
        return None
    resource = _resource_term(compact)
    if not resource:
        return None

    conditions: list[str] = []
    for condition, pattern, engagement_condition in _CONDITION_PATTERNS:
        match = pattern.search(compact)
        if not match:
            continue
        action = _action_term(compact, engagement_condition=engagement_condition)
        if not action:
            continue
        if engagement_condition and not _linked_engagement(compact, match, action):
            continue
        if condition not in conditions:
            conditions.append(condition)
    if not conditions:
        return None
    return {
        "source": source,
        "condition": " / ".join(conditions),
        "resource": resource,
        "text": compact,
    }


def _description_lines(description: str) -> list[str]:
    lines = [_compact_text(line) for line in description.splitlines()]
    return [line for line in lines if line]


def _subtitle_cues(subtitle_path: Path) -> list[str]:
    text = subtitle_path.read_text(encoding="utf-8", errors="replace")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n+", normalized.strip()) if normalized.strip() else []
    cues: list[str] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and lines[0].isdigit():
            lines = lines[1:]
        if lines and _SRT_TIMECODE_RE.match(lines[0]):
            lines = lines[1:]
        compact = _compact_text(" ".join(lines))
        if compact:
            cues.append(compact)
    return cues


def detect_resource_access_notices(description: str, subtitle_path: Path) -> list[dict[str, str]]:
    """Detect explicit source-backed conditions for receiving extra materials.

    Detection is intentionally conservative: a candidate must mention a resource,
    an access condition/method and a concrete acquisition action in a small source
    window. The returned source text is preserved for deterministic rendering; the
    agent must never infer the missing material itself.
    """

    notices: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(candidate: str, source: str) -> bool:
        notice = _notice_from_text(candidate, source)
        if not notice:
            return False
        key = (notice["condition"], notice["resource"])
        if key in seen:
            return True
        seen.add(key)
        notices.append(notice)
        return True

    def add_sequence(lines: list[str], source: str) -> None:
        matched: set[int] = set()
        for index, line in enumerate(lines):
            if add(line, source):
                matched.add(index)
        for index in range(len(lines) - 1):
            if index in matched or index + 1 in matched:
                continue
            add(f"{lines[index]} {lines[index + 1]}", source)

    add_sequence(_description_lines(description), "description")
    add_sequence(_subtitle_cues(subtitle_path), "subtitle")
    return notices[:6]
