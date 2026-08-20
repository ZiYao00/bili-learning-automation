from __future__ import annotations

from typing import Any


def classify(info: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    source = " ".join(
        [
            str(info.get("title") or ""),
            str(info.get("description") or ""),
            *map(str, info.get("tags") or []),
        ]
    ).lower()
    model = next(
        (
            item["canonical"]
            for item in config["models"]
            if any(alias.lower() in source for alias in item["aliases"])
        ),
        None,
    )
    route = next(
        (
            item
            for item in config["routes"]
            if all(pattern.lower() in source for pattern in item.get("all_patterns", []))
            and (
                not item.get("any_patterns")
                or any(pattern.lower() in source for pattern in item["any_patterns"])
            )
        ),
        config["fallback"],
    )
    task = route["task"]
    title = f"{model} {task}" if model else task
    required_tags = list(dict.fromkeys([*route["tags"], *([model] if model else [])]))
    return {
        "category_path": route["path"],
        "canonical_title": title,
        "required_tags": required_tags,
    }
