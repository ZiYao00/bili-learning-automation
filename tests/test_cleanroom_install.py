from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows agent installation acceptance only")


def _ps(script: Path, *args: str, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), *args],
        cwd=script.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=55,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def _simulate_new_clone(destination: Path) -> Path:
    destination.mkdir(parents=True)
    for directory in ("config", "docs", "scripts", "skill", "src", "tools"):
        shutil.copytree(
            ROOT / directory,
            destination / directory,
            ignore=shutil.ignore_patterns(
                "local.json", "pinned-comment-whitelist.local.json",
                "__pycache__", "*.pyc", "*.pyo", ".runtime",
            ),
        )
    for name in ("AGENTS.md", "README.md", "pyproject.toml"):
        shutil.copy2(ROOT / name, destination / name)
    assert not (destination / ".venv").exists()
    assert not (destination / "config" / "local.json").exists()
    assert not (destination / "key").exists()
    assert not (destination / "notes").exists()
    return destination


def test_cleanroom_agent_install_without_bundled_python_or_real_credentials(tmp_path: Path) -> None:
    project = _simulate_new_clone(tmp_path / "新手 模拟 Project")
    vault = tmp_path / "私有 Obsidian Vault"
    (vault / ".obsidian").mkdir(parents=True)
    cookie = tmp_path / "private files" / "cookies.txt"
    cookie.parent.mkdir()
    cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    # The fresh project has no .venv; a separately available Python is used.
    env = os.environ.copy()
    env["BILI_LEARNING_PYTHON"] = sys.executable
    runner = project / "scripts" / "run_bili_learning.ps1"
    junction = project / "scripts" / "ensure_junction.ps1"

    code, stdout, stderr = _ps(runner, "-ProbeOnly", env=env)
    assert code == 0, stderr + stdout
    probe = json.loads(stdout)
    assert probe["status"] == "ready"
    assert probe["source"] == "explicit_env", probe

    code, stdout, stderr = _ps(runner, "onboarding", env=env)
    assert code == 2, stderr  # Fresh install should not claim ready.
    initial = json.loads(stdout)
    assert initial["status"] == "action_required"
    assert initial["summary"]["yt_dlp"]["source"] == "project"

    code, stdout, stderr = _ps(runner, "configure-obsidian", "--vault", str(vault), env=env)
    assert code == 0, stderr
    assert json.loads(stdout)["status"] == "configured"
    code, stdout, stderr = _ps(runner, "configure-cookie", "--file", str(cookie), env=env)
    assert code == 0, stderr
    assert json.loads(stdout)["status"] == "configured"

    source = project / "notes" / "bilibili"
    target = vault / "bilibili"
    assert source.is_dir()
    assert json.loads((project / "config" / "local.json").read_text(encoding="utf-8"))["notes_root"] == "notes/bilibili"

    code, stdout, stderr = _ps(junction, "-Source", str(source), "-Target", str(target))
    assert code == 0 and json.loads(stdout)["status"] == "planned", stderr
    assert not target.exists()
    code, stdout, stderr = _ps(junction, "-Source", str(source), "-Target", str(target), "-Apply")
    assert code == 0 and json.loads(stdout)["status"] == "installed", stderr

    code, stdout, stderr = _ps(runner, "onboarding", env=env)
    assert code == 0, stderr
    assert json.loads(stdout)["status"] == "ready"

    code, stdout, stderr = _ps(junction, "-Source", str(source), "-Target", str(target), "-Apply")
    assert code == 0 and json.loads(stdout)["status"] == "already_installed", stderr

    occupied = vault / "pre-existing notebook"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("keep", encoding="utf-8")
    code, stdout, stderr = _ps(junction, "-Source", str(source), "-Target", str(occupied), "-Apply")
    assert code == 2 and json.loads(stdout)["status"] == "conflict", stderr
    assert (occupied / "keep.txt").read_text(encoding="utf-8") == "keep"
