from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import Settings

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
    notes_ok, notes_detail = _write_probe(settings.notes_root)
    add("OK" if notes_ok else "FAIL", "notes_root_writable", "notes root write probe", notes_detail)
    runtime_ok, runtime_detail = _write_probe(settings.runtime_root)
    add("OK" if runtime_ok else "FAIL", "runtime_root_writable", "runtime root write probe", runtime_detail)
    ytdlp = settings.ytdlp
    if ytdlp.path is None:
        add("FAIL", "ytdlp_not_configured", "yt-dlp", "未找到", source=ytdlp.source, checked_sources=list(ytdlp.checked_sources))
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
    return {"schema_version": 1, "status": "ok" if not failures else "failed", "checks": checks}


def run_doctor(settings: Settings) -> tuple[int, list[str]]:
    report = doctor_report(settings)
    lines = [f"[{check['status']}] {check['label']} - {check['detail']}" for check in report["checks"]]  # type: ignore[index]
    return (0 if report["status"] == "ok" else 1), lines
