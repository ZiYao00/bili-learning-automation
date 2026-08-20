from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import Settings


def _writable(path: Path) -> bool:
    target = path if path.exists() else path.parent
    while not target.exists() and target != target.parent:
        target = target.parent
    return target.exists() and os.access(target, os.W_OK)


def run_doctor(settings: Settings) -> tuple[int, list[str]]:
    lines: list[str] = []
    failures = 0

    def add(status: str, label: str, detail: str = "") -> None:
        nonlocal failures
        if status == "FAIL":
            failures += 1
        suffix = f" - {detail}" if detail else ""
        lines.append(f"[{status}] {label}{suffix}")

    add("OK", "Python", sys.version.split()[0])
    add("OK", "taxonomy", str(settings.taxonomy_path))
    add("OK" if _writable(settings.notes_root) else "FAIL", "notes root", str(settings.notes_root))
    add("OK" if _writable(settings.runtime_root) else "FAIL", "runtime root", str(settings.runtime_root))
    add(
        "OK" if settings.ytdlp and settings.ytdlp.is_file() else "FAIL",
        "yt-dlp",
        str(settings.ytdlp) if settings.ytdlp else "未找到",
    )
    add(
        "OK" if settings.cookie_file.is_file() else "FAIL",
        "cookie file exists",
        str(settings.cookie_file),
    )
    skill = settings.project_root / "hermes-skills" / "bilibili-learning" / "SKILL.md"
    add("OK" if skill.is_file() else "FAIL", "Hermes skill", str(skill))
    return (1 if failures else 0), lines
