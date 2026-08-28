from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_TAXONOMY_VERSION = 1
LOCAL_CONFIG_RELATIVE_PATH = Path("config/local.json")
DEFAULT_NOTES_SUBDIR = "bilibili"
DEFAULT_WORKFLOW_MODE = "light"
SUPPORTED_WORKFLOW_MODES = {"light", "strict"}
OBSIDIAN_SNIPPET_NAMES = ("learning-lab.css", "video-note.css")
OBSIDIAN_STYLE_REPOSITORY = "https://github.com/ZiYao00/obsidian-learning-snippets"
YTDLP_INSTALL_URL = "https://github.com/yt-dlp/yt-dlp/wiki/Installation"
YTDLP_WINDOWS_INSTALL_COMMAND = "winget install yt-dlp"


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
    vault_root: Path | None
    notes_subdir: Path | None
    notes_source: str
    notes_is_fallback: bool
    navigation_dir: str
    runtime_root: Path
    cookie_file: Path
    ytdlp: ExecutableResolution
    local_config_path: Path
    workflow_mode: str = DEFAULT_WORKFLOW_MODE


def _resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else project_root / path


def _normalize_notes_subdir(value: str) -> Path:
    path = Path(value.strip())
    if not value.strip() or path.is_absolute() or path == Path(".") or ".." in path.parts:
        raise ConfigurationError(
            "notes_subdir_invalid",
            "notes_subdir 必须是 Vault 内的相对子目录，且不能包含 ..。",
        )
    return path


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

    organization = config.get("organization")
    if organization is not None:
        if not isinstance(organization, dict):
            raise ValueError("taxonomy.organization 必须是对象")
        for key in ("enabled_by_default", "scope_confirmation_required"):
            if key in organization and not isinstance(organization[key], bool):
                raise ValueError(f"taxonomy.organization.{key} 必须是布尔值")
        max_depth = organization.get("max_depth", 2)
        if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 1 or max_depth > 2:
            raise ValueError("taxonomy.organization.max_depth 必须是 1 或 2")
        resource_root = organization.get("resource_root")
        if resource_root is not None and (not isinstance(resource_root, str) or not resource_root.strip()):
            raise ValueError("taxonomy.organization.resource_root 必须是非空字符串")

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


def _load_local_config(project_root: Path) -> tuple[Path, dict[str, Any]]:
    path = project_root / LOCAL_CONFIG_RELATIVE_PATH
    if not path.is_file():
        return path, {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError("local_config_invalid_json", f"本机配置不是有效 JSON：{path}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("local_config_invalid_type", "本机配置必须是 JSON 对象")
    allowed = {"taxonomy", "notes_root", "vault_root", "notes_subdir", "cookie_file", "ytdlp", "workflow_mode", "siliconflow"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ConfigurationError("local_config_unknown_key", "本机配置存在不支持字段：" + ", ".join(unknown))
    values: dict[str, Any] = {}
    for key, value in raw.items():
        if key == "siliconflow":
            if not isinstance(value, dict) or set(value) != {"api_key"}:
                raise ConfigurationError("local_config_invalid_value", "siliconflow 必须只包含非空 api_key 字段")
            api_key = value.get("api_key")
            if not isinstance(api_key, str) or not api_key.strip():
                raise ConfigurationError("local_config_invalid_value", "siliconflow.api_key 必须是非空字符串")
            values[key] = {"api_key": api_key.strip()}
            continue
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError("local_config_invalid_value", f"本机配置 {key} 必须是非空字符串")
        values[key] = value.strip()
    if "notes_root" in values and ({"vault_root", "notes_subdir"} & values.keys()):
        raise ConfigurationError(
            "local_config_notes_conflict",
            "notes_root 是旧版直接路径配置，不能与 vault_root / notes_subdir 同时使用。",
        )
    if "notes_subdir" in values and "vault_root" not in values:
        raise ConfigurationError("local_config_notes_subdir_without_vault", "配置 notes_subdir 时必须同时配置 vault_root。")
    workflow_mode = values.get("workflow_mode")
    if workflow_mode and workflow_mode not in SUPPORTED_WORKFLOW_MODES:
        raise ConfigurationError(
            "workflow_mode_invalid",
            "workflow_mode 只支持 light 或 strict。",
        )
    return path, values


def _resolve_notes_location(
    project_root: Path,
    taxonomy: dict[str, Any],
    local_config: dict[str, str],
) -> tuple[Path, Path | None, Path | None, str, bool]:
    env_notes_root = os.environ.get("BILI_LEARNING_NOTES_ROOT")
    env_vault_root = os.environ.get("BILI_LEARNING_VAULT_ROOT")
    env_notes_subdir = os.environ.get("BILI_LEARNING_NOTES_SUBDIR")
    if env_notes_root and (env_vault_root or env_notes_subdir):
        raise ConfigurationError(
            "environment_notes_conflict",
            "BILI_LEARNING_NOTES_ROOT 不能与 BILI_LEARNING_VAULT_ROOT / BILI_LEARNING_NOTES_SUBDIR 同时使用。",
        )
    if env_notes_subdir and not env_vault_root:
        raise ConfigurationError(
            "environment_notes_subdir_without_vault",
            "BILI_LEARNING_NOTES_SUBDIR 需要同时设置 BILI_LEARNING_VAULT_ROOT。",
        )

    if env_notes_root:
        return _resolve_path(project_root, env_notes_root), None, None, "environment_notes_root", False
    if env_vault_root:
        vault_root = _resolve_path(project_root, env_vault_root)
        notes_subdir = _normalize_notes_subdir(env_notes_subdir or DEFAULT_NOTES_SUBDIR)
        return vault_root / notes_subdir, vault_root, notes_subdir, "environment_vault", False

    local_notes_root = local_config.get("notes_root")
    if local_notes_root:
        return _resolve_path(project_root, local_notes_root), None, None, "local_notes_root", False
    local_vault_root = local_config.get("vault_root")
    if local_vault_root:
        vault_root = _resolve_path(project_root, local_vault_root)
        notes_subdir = _normalize_notes_subdir(local_config.get("notes_subdir") or DEFAULT_NOTES_SUBDIR)
        return vault_root / notes_subdir, vault_root, notes_subdir, "local_vault", False

    notes_root = _resolve_path(project_root, taxonomy["notes_root"])
    return notes_root, None, None, "taxonomy_fallback", True


def _save_local_config(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def configure_obsidian(project_root: Path, vault_root: Path, notes_subdir: str = DEFAULT_NOTES_SUBDIR) -> Path:
    project_root = project_root.resolve()
    vault_root = vault_root.expanduser().resolve()
    if not vault_root.is_dir():
        raise ConfigurationError("vault_root_missing", f"Vault 目录不存在：{vault_root}")
    if not (vault_root / ".obsidian").is_dir():
        raise ConfigurationError("vault_root_not_obsidian", f"未在该目录发现 .obsidian：{vault_root}")
    normalized_subdir = _normalize_notes_subdir(notes_subdir)

    path, local_config = _load_local_config(project_root)
    updated = dict(local_config)
    updated.pop("notes_root", None)
    updated["vault_root"] = str(vault_root)
    updated["notes_subdir"] = str(normalized_subdir)
    return _save_local_config(path, updated)


def configure_cookie_file(project_root: Path, cookie_file: Path) -> Path:
    project_root = project_root.resolve()
    cookie_file = cookie_file.expanduser().resolve()
    if not cookie_file.is_file():
        raise ConfigurationError("cookie_file_missing", f"Bilibili Cookie 文件不存在：{cookie_file}")

    path, local_config = _load_local_config(project_root)
    updated = dict(local_config)
    updated["cookie_file"] = str(cookie_file)
    return _save_local_config(path, updated)


def configure_ytdlp_path(project_root: Path, ytdlp_path: Path) -> Path:
    project_root = project_root.resolve()
    ytdlp_path = ytdlp_path.expanduser().resolve()
    if not ytdlp_path.is_file():
        raise ConfigurationError("ytdlp_path_invalid", f"yt-dlp 路径不存在或不是文件：{ytdlp_path}")

    path, local_config = _load_local_config(project_root)
    updated = dict(local_config)
    updated["ytdlp"] = str(ytdlp_path)
    return _save_local_config(path, updated)


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


def _resolve_workflow_mode(local_config: dict[str, str]) -> str:
    mode = (os.environ.get("BILI_LEARNING_WORKFLOW_MODE") or local_config.get("workflow_mode") or DEFAULT_WORKFLOW_MODE)
    normalized = mode.strip().lower()
    if normalized not in SUPPORTED_WORKFLOW_MODES:
        raise ConfigurationError(
            "workflow_mode_invalid",
            "BILI_LEARNING_WORKFLOW_MODE / workflow_mode 只支持 light 或 strict。",
        )
    return normalized


def load_settings(project_root: Path) -> Settings:
    project_root = project_root.resolve()
    local_config_path, local_config = _load_local_config(project_root)
    taxonomy_path = _resolve_path(
        project_root,
        os.environ.get("BILI_LEARNING_TAXONOMY") or local_config.get("taxonomy") or "config/bilibili-note-taxonomy.json",
    )
    if not taxonomy_path.is_file():
        raise FileNotFoundError(f"未找到 B站笔记分类配置：{taxonomy_path}")
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8-sig"))
    validate_taxonomy(taxonomy)

    notes_root, vault_root, notes_subdir, notes_source, notes_is_fallback = _resolve_notes_location(
        project_root,
        taxonomy,
        local_config,
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
        vault_root=vault_root,
        notes_subdir=notes_subdir,
        notes_source=notes_source,
        notes_is_fallback=notes_is_fallback,
        navigation_dir=taxonomy["navigation_dir"],
        runtime_root=project_root / ".runtime" / "bilibili-learning",
        cookie_file=cookie_file,
        ytdlp=find_ytdlp(project_root, local_config),
        local_config_path=local_config_path,
        workflow_mode=_resolve_workflow_mode(local_config),
    )
