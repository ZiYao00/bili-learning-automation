from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import (
    DEFAULT_NOTES_SUBDIR,
    OBSIDIAN_SNIPPET_NAMES,
    OBSIDIAN_STYLE_REPOSITORY,
    YTDLP_INSTALL_URL,
    YTDLP_WINDOWS_INSTALL_COMMAND,
    Settings,
)

MINIMUM_PYTHON = (3, 10)


def _write_probe(path: Path) -> tuple[bool, str]:
    target = path if path.exists() else path.parent
    while not target.exists() and target != target.parent:
        target = target.parent
    if not target.exists() or not os.access(target, os.W_OK):
        return False, str(target)
    try:
        with tempfile.NamedTemporaryFile(prefix=".bili-learning-doctor-", dir=target, delete=True):
            pass
    except OSError as error:
        return False, str(error)
    return True, str(target)


def doctor_report(settings: Settings) -> dict[str, object]:
    checks: list[dict[str, object]] = []

    def add(status: str, code: str, label: str, detail: str = "", **extra: object) -> None:
        checks.append({"status": status, "code": code, "label": label, "detail": detail, **extra})

    python_ok = sys.version_info >= MINIMUM_PYTHON
    add(
        "OK" if python_ok else "FAIL",
        "python_version",
        "Python",
        sys.version.split()[0],
        required=f">={MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}",
    )
    add("OK" if settings.project_root.is_dir() else "FAIL", "project_root_exists", "project root", str(settings.project_root))
    add("OK", "taxonomy_ready", "taxonomy", str(settings.taxonomy_path))
    add("OK", "workflow_mode", "workflow mode", settings.workflow_mode)

    if settings.notes_is_fallback:
        add(
            "WARN",
            "notes_repository_fallback",
            "Obsidian notes location",
            str(settings.notes_root),
            source=settings.notes_source,
            message="当前仍使用仓库内临时 fallback；建议配置真实 Obsidian Vault。",
        )
    else:
        add("OK", "notes_location_configured", "Obsidian notes location", str(settings.notes_root), source=settings.notes_source)

    if settings.vault_root is not None:
        obsidian_dir = settings.vault_root / ".obsidian"
        add(
            "OK" if obsidian_dir.is_dir() else "FAIL",
            "obsidian_vault_detected",
            "Obsidian Vault",
            str(settings.vault_root),
        )
        snippets_dir = obsidian_dir / "snippets"
        for snippet_name in OBSIDIAN_SNIPPET_NAMES:
            snippet_path = snippets_dir / snippet_name
            add(
                "OK" if snippet_path.is_file() else "WARN",
                f"obsidian_snippet_{snippet_name.removesuffix('.css').replace('-', '_')}",
                f"CSS snippet {snippet_name}",
                str(snippet_path),
            )
    else:
        add(
            "WARN",
            "obsidian_vault_unknown",
            "Obsidian Vault",
            "未配置 vault_root；无法可靠检查 .obsidian/snippets。",
            source=settings.notes_source,
        )

    notes_ok, notes_detail = _write_probe(settings.notes_root)
    add("OK" if notes_ok else "FAIL", "notes_root_writable", "notes root write probe", notes_detail)
    runtime_ok, runtime_detail = _write_probe(settings.runtime_root)
    add("OK" if runtime_ok else "FAIL", "runtime_root_writable", "runtime root write probe", runtime_detail)

    ytdlp = settings.ytdlp
    if ytdlp.path is None:
        add(
            "FAIL",
            "ytdlp_not_configured",
            "yt-dlp",
            f"未检测到；不会自动安装或内置可执行文件。Windows 推荐：{YTDLP_WINDOWS_INSTALL_COMMAND}",
            source=ytdlp.source,
            checked_sources=list(ytdlp.checked_sources),
            windows_install_command=YTDLP_WINDOWS_INSTALL_COMMAND,
            install_url=YTDLP_INSTALL_URL,
            next_step="安装完成后重新运行 doctor；若使用自定义位置，再配置 BILI_LEARNING_YTDLP 或 local.json 的 ytdlp。",
        )
    elif not ytdlp.path.is_file():
        add("FAIL", "ytdlp_path_invalid", "yt-dlp", str(ytdlp.path), source=ytdlp.source, checked_sources=list(ytdlp.checked_sources))
    else:
        try:
            completed = subprocess.run(
                [str(ytdlp.path), "--version"], text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=10
            )
        except subprocess.TimeoutExpired as exc:
            add(
                "WARN",
                "ytdlp_version_check_timeout",
                "yt-dlp",
                str(exc),
                source=ytdlp.source,
                path=str(ytdlp.path),
                message="yt-dlp --version 检查超时；保留为警告，正式采集仍会做真实可用性验证。",
                checked_sources=list(ytdlp.checked_sources),
            )
        except OSError as exc:
            add("FAIL", "ytdlp_not_executable", "yt-dlp", str(exc), source=ytdlp.source, checked_sources=list(ytdlp.checked_sources))
        else:
            version = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
            if completed.returncode or not version:
                add("FAIL", "ytdlp_not_executable", "yt-dlp", completed.stderr.strip() or "--version 未返回版本", source=ytdlp.source, checked_sources=list(ytdlp.checked_sources))
            else:
                add("OK", "ytdlp_ready", "yt-dlp", str(ytdlp.path), source=ytdlp.source, version=version, checked_sources=list(ytdlp.checked_sources))

    add("OK" if settings.cookie_file.is_file() else "FAIL", "cookie_file_exists", "cookie file exists", str(settings.cookie_file))
    protocol = settings.project_root / "docs" / "AGENT-INTEGRATION.md"
    add("OK" if protocol.is_file() else "FAIL", "agent_protocol_exists", "agent protocol", str(protocol))

    failures = sum(1 for check in checks if check["status"] == "FAIL")
    warnings = sum(1 for check in checks if check["status"] == "WARN")
    return {
        "schema_version": 1,
        "status": "ok" if not failures else "failed",
        "warnings": warnings,
        "checks": checks,
    }


def onboarding_report(settings: Settings) -> dict[str, object]:
    report = doctor_report(settings)
    checks = {str(check["code"]): check for check in report["checks"]}  # type: ignore[index]
    actions: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    def add_action(code: str, message: str, **extra: object) -> None:
        actions.append({"code": code, "message": message, **extra})

    python_check = checks.get("python_version")
    if python_check and python_check["status"] == "FAIL":
        add_action(
            "python_required",
            f"需要 Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}+；当前环境不满足要求。",
            required=f">={MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}",
        )

    if settings.notes_is_fallback:
        add_action(
            "obsidian_vault_required",
            "尚未绑定真实 Obsidian Vault。请提供直接包含 .obsidian 的 Vault 根目录。",
            required_input="vault_root",
            prompt="请提供 Obsidian Vault 根目录（即直接包含 .obsidian 的目录）。",
            default_notes_subdir=DEFAULT_NOTES_SUBDIR,
            config_path=str(settings.local_config_path),
        )

    vault_check = checks.get("obsidian_vault_detected")
    if vault_check and vault_check["status"] == "FAIL":
        add_action(
            "obsidian_vault_invalid",
            "已配置的 Vault 无效：目标目录必须直接包含 .obsidian。",
            required_input="vault_root",
            prompt="请重新提供直接包含 .obsidian 的 Obsidian Vault 根目录。",
            current_value=str(settings.vault_root) if settings.vault_root is not None else "",
        )

    if settings.ytdlp.path is None or not settings.ytdlp.path.is_file():
        add_action(
            "ytdlp_required",
            "未检测到 yt-dlp。项目不会自动安装或复制可执行文件。",
            recommended_command=YTDLP_WINDOWS_INSTALL_COMMAND,
            install_url=YTDLP_INSTALL_URL,
            custom_path_supported=True,
            prompt="如已在自定义目录安装 yt-dlp，请提供可执行文件路径；否则可先按推荐命令安装。",
        )

    ytdlp_unusable = checks.get("ytdlp_not_executable")
    if ytdlp_unusable and ytdlp_unusable["status"] == "FAIL":
        add_action(
            "ytdlp_unusable",
            "已找到 yt-dlp，但当前环境无法执行它；请检查文件权限、损坏或兼容性后重试。",
            current_value=str(settings.ytdlp.path) if settings.ytdlp.path is not None else "",
        )

    ytdlp_timeout = checks.get("ytdlp_version_check_timeout")
    if ytdlp_timeout and ytdlp_timeout["status"] == "WARN":
        warnings.append(
            {
                "code": "ytdlp_version_check_timeout",
                "message": "yt-dlp 版本探测超时，但文件已检测到；这不会阻塞首次配置，正式采集会再次验证。",
                "path": str(settings.ytdlp.path) if settings.ytdlp.path is not None else "",
            }
        )

    if not settings.cookie_file.is_file():
        add_action(
            "cookie_file_required",
            "未检测到 Bilibili Cookie 文件。请只提供 Netscape 格式 Cookie 文件路径，不要粘贴 Cookie 内容。",
            required_input="cookie_file_path",
            expected_path=str(settings.cookie_file),
            prompt="请提供 Netscape 格式 Bilibili Cookie 文件路径；不要在聊天中粘贴 Cookie 内容。",
        )

    missing_css: list[str] = []
    for snippet_name in OBSIDIAN_SNIPPET_NAMES:
        code = f"obsidian_snippet_{snippet_name.removesuffix('.css').replace('-', '_')}"
        check = checks.get(code)
        if check and check["status"] == "WARN":
            missing_css.append(snippet_name)
    if missing_css:
        destination = (
            str(settings.vault_root / ".obsidian" / "snippets") if settings.vault_root is not None else "<vault_root>/.obsidian/snippets"
        )
        warnings.append(
            {
                "code": "obsidian_css_missing",
                "message": "Obsidian 样式缺失不会阻止笔记生成，但排版效果会不完整；程序不会静默复制或覆盖 CSS。",
                "missing": missing_css,
                "repository": OBSIDIAN_STYLE_REPOSITORY,
                "destination": destination,
                "activation": "Obsidian → 设置 → 外观 → CSS 代码片段，并启用 learning-lab 与 video-note。",
            }
        )

    vault_unknown = checks.get("obsidian_vault_unknown")
    if vault_unknown and vault_unknown["status"] == "WARN":
        warnings.append(
            {
                "code": "obsidian_vault_unknown",
                "message": "当前使用兼容的旧版 notes_root，笔记仍可生成，但无法可靠检查 CSS；建议以后迁移到 vault_root + notes_subdir。",
            }
        )

    ytdlp_status = "missing"
    if settings.ytdlp.path is not None and settings.ytdlp.path.is_file():
        ytdlp_status = "unusable" if ytdlp_unusable else ("warning" if ytdlp_timeout else "ready")
    summary = {
        "python": {"status": "ready" if sys.version_info >= MINIMUM_PYTHON else "required", "version": sys.version.split()[0]},
        "yt_dlp": {
            "status": ytdlp_status,
            "path": str(settings.ytdlp.path) if settings.ytdlp.path is not None else None,
            "source": settings.ytdlp.source,
        },
        "bilibili_cookie": {"status": "ready" if settings.cookie_file.is_file() else "required"},
        "obsidian": {
            "status": "required" if settings.notes_is_fallback else "ready",
            "vault_root": str(settings.vault_root) if settings.vault_root is not None else None,
            "notes_root": str(settings.notes_root),
        },
        "css": {"status": "missing_optional" if missing_css else "ready", "missing": missing_css},
        "workflow_mode": settings.workflow_mode,
    }

    return {
        "schema_version": 1,
        "status": "action_required" if actions else "ready",
        "actions": actions,
        "warnings": warnings,
        "summary": summary,
        "checks": report["checks"],
    }


def run_doctor(settings: Settings) -> tuple[int, list[str]]:
    report = doctor_report(settings)
    lines = [f"[{check['status']}] {check['label']} - {check['detail']}" for check in report["checks"]]  # type: ignore[index]
    return (0 if report["status"] == "ok" else 1), lines
