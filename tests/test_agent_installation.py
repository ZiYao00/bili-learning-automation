from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENSURE_JUNCTION = ROOT / "scripts" / "ensure_junction.ps1"
INSTALL_AGENT = ROOT / "scripts" / "install_agent_skill.ps1"

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows Junction installer only")


def _powershell(script: Path, *args: str, env: dict[str, str] | None = None) -> tuple[int, dict]:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), *args],
        cwd=ROOT, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, timeout=30,
    )
    assert result.stdout.strip(), result.stderr
    return result.returncode, json.loads(result.stdout.strip().splitlines()[-1])


def test_agent_junction_plan_apply_and_repeat_are_safe(tmp_path: Path) -> None:
    source = tmp_path / "source folder"
    source.mkdir()
    target = tmp_path / "profile folder" / "skill link"

    code, planned = _powershell(ENSURE_JUNCTION, "-Source", str(source), "-Target", str(target))
    assert code == 0 and planned["status"] == "planned"
    assert not target.exists()

    code, installed = _powershell(ENSURE_JUNCTION, "-Source", str(source), "-Target", str(target), "-Apply")
    assert code == 0 and installed["status"] == "installed"
    assert target.resolve() == source.resolve()

    code, repeated = _powershell(ENSURE_JUNCTION, "-Source", str(source), "-Target", str(target), "-Apply")
    assert code == 0 and repeated["status"] == "already_installed"


def test_agent_junction_conflict_never_overwrites_data(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "profile" / "skill"
    target.mkdir(parents=True)
    original = target / "keep.txt"
    original.write_text("do not overwrite", encoding="utf-8")

    code, outcome = _powershell(ENSURE_JUNCTION, "-Source", str(source), "-Target", str(target), "-Apply")
    assert code == 2 and outcome["status"] == "conflict"
    assert original.read_text(encoding="utf-8") == "do not overwrite"


def test_agent_junction_rejects_recursive_target(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    target = source / "nested" / "loop"
    code, outcome = _powershell(ENSURE_JUNCTION, "-Source", str(source), "-Target", str(target), "-Apply")
    assert code == 2 and outcome["status"] == "failed"
    assert "nested inside Source" in outcome["message"]
    assert not target.exists()


def test_agent_install_wrapper_uses_selected_host_and_is_idempotent(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["USERPROFILE"] = str(tmp_path / "User Profile")
    env["LOCALAPPDATA"] = str(tmp_path / "Local AppData")
    target = tmp_path / "User Profile" / ".agents" / "skills" / "bili-learning-automation"

    code, planned = _powershell(INSTALL_AGENT, "-Agent", "Codex", env=env)
    assert code == 0 and planned["status"] == "planned"
    assert not target.exists()

    code, installed = _powershell(INSTALL_AGENT, "-Agent", "Codex", "-Apply", env=env)
    assert code == 0 and installed["status"] == "installed"
    assert (target / "SKILL.md").is_file()

    code, repeated = _powershell(INSTALL_AGENT, "-Agent", "Codex", "-Apply", env=env)
    assert code == 0 and repeated["status"] == "already_installed"
