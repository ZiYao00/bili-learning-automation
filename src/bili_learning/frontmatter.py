from __future__ import annotations

import json
import re
from collections.abc import Mapping

FRONTMATTER_FIELDS = ("author", "published", "duration", "source")


def yaml_scalar(value: object) -> str:
    """Encode a string using JSON syntax, a valid unambiguous YAML scalar subset."""
    return json.dumps(str(value), ensure_ascii=False)


def render_frontmatter(values: Mapping[str, object], tags: list[str]) -> str:
    lines = ["---"]
    lines.extend(f"{field}: {yaml_scalar(values[field])}" for field in FRONTMATTER_FIELDS)
    lines.append("tags:")
    lines.extend(f"  - {yaml_scalar(tag)}" for tag in tags)
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


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return {}, []
    values: dict[str, str] = {}
    tags: list[str] = []
    active_key: str | None = None
    for raw in match.group(1).splitlines():
        if raw.startswith("  - ") and active_key == "tags":
            tags.append(_parse_scalar(raw[4:]))
            continue
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", raw)
        if field:
            active_key = field.group(1)
            values[active_key] = _parse_scalar(field.group(2))
        elif raw.strip():
            active_key = None
    return values, tags
