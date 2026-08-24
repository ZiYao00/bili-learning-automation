from __future__ import annotations

from typing import Any


def _matched_models(source: str, models: list[dict[str, Any]]) -> list[str]:
    matched: list[str] = []
    for item in models:
        if any(alias.lower() in source for alias in item["aliases"]):
            matched.append(item["canonical"])
    return matched


def _matched_route(source: str, routes: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in routes
            if all(pattern.lower() in source for pattern in item.get("all_patterns", []))
            and (
                not item.get("any_patterns")
                or any(pattern.lower() in source for pattern in item["any_patterns"])
            )
        ),
        None,
    )


def classify(info: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    title_source = str(info.get("title") or "").lower()
    source = " ".join(
        [
            str(info.get("title") or ""),
            str(info.get("description") or ""),
            *map(str, info.get("tags") or []),
        ]
    ).lower()

    # 标题中的模型名优先级最高。标题没有任何模型命中时，才回退到简介 / 原标签，
    # 避免一个教程仅在简介里顺带提到其它模型时被错误打上模型标签。
    models = _matched_models(title_source, config["models"])
    if not models:
        models = _matched_models(source, config["models"])

    # 主分类同样优先看标题。旧笔记可能带有历史误分类 tags，不能让这些旧 tags
    # 覆盖标题已经明确表达的模型生态或知识主题；标题无法判断时才回退完整来源。
    route = _matched_route(title_source, config["routes"])
    if route is None:
        route = _matched_route(source, config["routes"])
    if route is None:
        route = config["fallback"]

    required_tags = list(dict.fromkeys([*route["tags"], *models]))
    return {
        "category_path": config["fallback"]["path"],
        "suggested_category_path": route["path"],
        "suggested_route_id": route.get("id", "fallback"),
        "suggested_title": route.get("title", route["task"]),
        "required_tags": required_tags,
    }
