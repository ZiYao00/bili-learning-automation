from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_TAXONOMY_VERSION = 1
LOCAL_CONFIG_RELATIVE_PATH = Path("config/local.json")


class ConfigurationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DependencyError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ExecutableResolution:
    path: Path | None
    source: str
    checked_sources: tuple[str, ...]


@dataclass(frozen=True)
class Settings:
    project_root: Path
    taxonomy_path: Path
    taxonomy: dict[str, Any]
    notes_root: Path
    navigation_dir: str
    runtime_root: Path
    cookie_file: Path
    ytdlp: ExecutableResolution
    local_config_path: Path


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
        if "title" in route and (not isinstance(route["title"], str) or not route["title"].strip()):
            raise ValueError("taxonomy route.title 必须是非空字符串")
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


def _load_local_config(project_root: Path) -> tuple[Path, dict[str, str]]:
    path = project_root / LOCAL_CONFIG_RELATIVE_PATH
    if not path.is_file():
        return path, {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError("local_config_invalid_json", f"本机配置不是有效 JSON：{path}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("local_config_invalid_type", "本机配置必须是 JSON 对象")
    allowed = {"taxonomy", "notes_root", "cookie_file", "ytdlp"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ConfigurationError("local_config_unknown_key", "本机配置存在不支持字段：" + ", ".join(unknown))
    values: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError("local_config_invalid_value", f"本机配置 {key} 必须是非空字符串")
        values[key] = value.strip()
    return path, values


def find_ytdlp(project_root: Path, local_config: dict[str, str]) -> ExecutableResolution:
    checked = ["environment:BILI_LEARNING_YTDLP", f"local_config:{LOCAL_CONFIG_RELATIVE_PATH}", "PATH:yt-dlp"]
    configured = os.environ.get("BILI_LEARNING_YTDLP")
    if configured:
        return ExecutableResolution(Path(configured).expanduser(), "environment", tuple(checked))
    local_value = local_config.get("ytdlp")
    if local_value:
        return ExecutableResolution(_resolve_path(project_root, local_value), "local_config", tuple(checked))
    on_path = shutil.which("yt-dlp")
    if on_path:
        return ExecutableResolution(Path(on_path), "path", tuple(checked))
    return ExecutableResolution(None, "missing", tuple(checked))


def load_settings(project_root: Path) -> Settings:
    project_root = project_root.resolve()
    local_config_path, local_config = _load_local_config(project_root)
    taxonomy_path = _resolve_path(
        project_root,
        os.environ.get("BILI_LEARNING_TAXONOMY") or local_config.get("taxonomy") or "config/bilibili-note-taxonomy.json",
    )
    if not taxonomy_path.is_file():
        raise FileNotFoundError(f"未找到 B站笔记分类配置：{taxonomy_path}")
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    validate_taxonomy(taxonomy)

    notes_root = _resolve_path(
        project_root,
        os.environ.get("BILI_LEARNING_NOTES_ROOT") or local_config.get("notes_root") or taxonomy["notes_root"],
    )
    cookie_file = _resolve_path(
        project_root,
        os.environ.get("BILI_LEARNING_COOKIE_FILE") or local_config.get("cookie_file") or "key/bilibili_cookies.txt",
    )
    return Settings(
        project_root=project_root,
        taxonomy_path=taxonomy_path,
        taxonomy=taxonomy,
        notes_root=notes_root,
        navigation_dir=taxonomy["navigation_dir"],
        runtime_root=project_root / ".runtime" / "bilibili-learning",
        cookie_file=cookie_file,
        ytdlp=find_ytdlp(project_root, local_config),
        local_config_path=local_config_path,
    )
