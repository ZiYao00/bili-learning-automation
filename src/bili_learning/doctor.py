from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import OBSIDIAN_SNIPPET_NAMES, YTDLP_INSTALL_URL, YTDLP_WINDOWS_INSTALL_COMMAND, Settings

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
        except (OSError, subprocess.TimeoutExpired) as exc:
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


def run_doctor(settings: Settings) -> tuple[int, list[str]]:
    report = doctor_report(settings)
    lines = [f"[{check['status']}] {check['label']} - {check['detail']}" for check in report["checks"]]  # type: ignore[index]
    return (0 if report["status"] == "ok" else 1), lines
