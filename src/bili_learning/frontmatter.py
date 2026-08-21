from __future__ import annotations

import json
import re
from collections.abc import Mapping

FRONTMATTER_FIELDS = ("author", "published", "duration", "source")
DEFAULT_CSSCLASSES = ("learning-page", "video-note")


def yaml_scalar(value: object) -> str:
    """Encode a string using JSON syntax, a valid unambiguous YAML scalar subset."""
    return json.dumps(str(value), ensure_ascii=False)


def render_frontmatter(
    values: Mapping[str, object],
    tags: list[str],
    cssclasses: tuple[str, ...] = DEFAULT_CSSCLASSES,
) -> str:
    lines = ["---"]
    lines.extend(f"{field}: {yaml_scalar(values[field])}" for field in FRONTMATTER_FIELDS)
    lines.append("tags:")
    lines.extend(f"  - {yaml_scalar(tag)}" for tag in tags)
    lines.append("cssclasses:")
    lines.extend(f"  - {yaml_scalar(cssclass)}" for cssclass in cssclasses)
    lines.append("---")
    return "\n".join(lines)


def _parse_scalar(raw: str) -> str:
    value = raw.strip()
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return parsed if isinstance(parsed, str) else value
    return value


def parse_frontmatter_list(text: str, key: str) -> list[str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return []
    values: list[str] = []
    active_key: str | None = None
    for raw in match.group(1).splitlines():
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", raw)
        if field:
            active_key = field.group(1)
            continue
        if raw.startswith("  - ") and active_key == key:
            values.append(_parse_scalar(raw[4:]))
        elif raw.strip() and not raw.startswith("  - "):
            active_key = None
    return values


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return {}, []
    values: dict[str, str] = {}
    for raw in match.group(1).splitlines():
        if raw.startswith("  - "):
            continue
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", raw)
        if field:
            values[field.group(1)] = _parse_scalar(field.group(2))
    return values, parse_frontmatter_list(text, "tags")
