from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_TAXONOMY_VERSION = 1


@dataclass(frozen=True)
class Settings:
    project_root: Path
    taxonomy_path: Path
    taxonomy: dict[str, Any]
    notes_root: Path
    navigation_dir: str
    runtime_root: Path
    cookie_file: Path
    ytdlp: Path | None


def _resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else project_root / path


def validate_taxonomy(config: dict[str, Any]) -> None:
    if config.get("version") != SUPPORTED_TAXONOMY_VERSION:
        raise ValueError(f"Unsupported taxonomy version: {config.get('version')!r}")
    for key in ("notes_root", "navigation_dir", "fallback", "models", "routes"):
        if key not in config:
            raise ValueError(f"taxonomy 缺少字段：{key}")
    if not isinstance(config["notes_root"], str) or not config["notes_root"].strip():
        raise ValueError("taxonomy.notes_root 必须是非空字符串")
    if not isinstance(config["navigation_dir"], str) or not config["navigation_dir"].strip():
        raise ValueError("taxonomy.navigation_dir 必须是非空字符串")
    if not isinstance(config["models"], list) or not isinstance(config["routes"], list):
        raise ValueError("taxonomy.models/routes 必须是数组")

    route_ids: set[str] = set()
    for route in [config["fallback"], *config["routes"]]:
        if not isinstance(route, dict):
            raise ValueError("taxonomy route 必须是对象")
        for key in ("path", "task", "tags"):
            if key not in route:
                raise ValueError(f"taxonomy route 缺少字段：{key}")
        if not isinstance(route["path"], list) or not route["path"] or not all(isinstance(x, str) and x for x in route["path"]):
            raise ValueError("taxonomy route.path 必须是非空字符串数组")
        if not isinstance(route["task"], str) or not route["task"].strip():
            raise ValueError("taxonomy route.task 必须是非空字符串")
        if not isinstance(route["tags"], list) or not all(isinstance(x, str) and x for x in route["tags"]):
            raise ValueError("taxonomy route.tags 必须是字符串数组")
        for pattern_key in ("all_patterns", "any_patterns"):
            if pattern_key in route and (
                not isinstance(route[pattern_key], list)
                or not all(isinstance(x, str) and x for x in route[pattern_key])
            ):
                raise ValueError(f"taxonomy route.{pattern_key} 必须是字符串数组")
        route_id = route.get("id")
        if route_id is not None:
            if not isinstance(route_id, str) or not route_id:
                raise ValueError("taxonomy route.id 必须是非空字符串")
            if route_id in route_ids:
                raise ValueError(f"taxonomy route.id 重复：{route_id}")
            route_ids.add(route_id)

    for model in config["models"]:
        if not isinstance(model, dict) or not isinstance(model.get("canonical"), str):
            raise ValueError("taxonomy model 缺少 canonical")
        aliases = model.get("aliases")
        if not isinstance(aliases, list) or not all(isinstance(x, str) and x for x in aliases):
            raise ValueError(f"taxonomy model aliases 无效：{model.get('canonical')}")


def find_ytdlp(project_root: Path) -> Path | None:
    configured = os.environ.get("BILI_LEARNING_YTDLP")
    if configured:
        return Path(configured).expanduser()
    on_path = shutil.which("yt-dlp")
    if on_path:
        return Path(on_path)
    return None


def load_settings(project_root: Path) -> Settings:
    project_root = project_root.resolve()
    taxonomy_path = _resolve_path(
        project_root,
        os.environ.get("BILI_LEARNING_TAXONOMY", "config/bilibili-note-taxonomy.json"),
    )
    if not taxonomy_path.is_file():
        raise FileNotFoundError(f"未找到 B站笔记分类配置：{taxonomy_path}")
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    validate_taxonomy(taxonomy)

    notes_override = os.environ.get("BILI_LEARNING_NOTES_ROOT")
    notes_root = _resolve_path(project_root, notes_override or taxonomy["notes_root"])
    cookie_file = _resolve_path(
        project_root,
        os.environ.get("BILI_LEARNING_COOKIE_FILE", "key/bilibili_cookies.txt"),
    )
    return Settings(
        project_root=project_root,
        taxonomy_path=taxonomy_path,
        taxonomy=taxonomy,
        notes_root=notes_root,
        navigation_dir=taxonomy["navigation_dir"],
        runtime_root=project_root / ".runtime" / "bilibili-learning",
        cookie_file=cookie_file,
        ytdlp=find_ytdlp(project_root),
    )
