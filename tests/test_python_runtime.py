from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts" / "python_runtime.ps1"
RUNNER = ROOT / "scripts" / "run_bili_learning.ps1"
BRIDGE = ROOT / "skill" / "bili-learning-automation" / "scripts" / "local_bridge.ps1"

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell runtime resolution only")


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _powershell(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=40,
        check=False,
    )


def _source_resolver(code: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    expression = "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); . " + _ps_quote(str(RESOLVER)) + "; " + code
    return _powershell("-Command", expression, env=env)


def test_python_probe_uses_real_validated_interpreter() -> None:
    outcome = _powershell("-File", str(RUNNER), "-ProbeOnly")
    assert outcome.returncode == 0, outcome.stderr
    report = json.loads(outcome.stdout.strip())
    assert report["status"] == "ready"
    assert report["python_version"].startswith("3.")
    assert report["source"] in {"project_venv", "system:python", "system:python3", "py_launcher", "explicit_env"}
    assert report["changes_made"] is False


def test_invalid_explicit_python_override_fails_closed(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["BILI_LEARNING_PYTHON"] = str(tmp_path / "nonexistent-python.exe")
    outcome = _powershell("-File", str(RUNNER), "-ProbeOnly", env=env)
    assert outcome.returncode == 2, outcome.stderr
    report = json.loads(outcome.stdout.strip())
    assert report["status"] == "python_required"
    assert report["changes_made"] is False



def test_python_probe_can_report_missing_without_any_installer(tmp_path: Path) -> None:
    project = tmp_path / "empty no Python environment"
    project.mkdir()
    code = (
        "function Get-Command { param($Name, $CommandType, $ErrorAction) return $null }; "
        "$r=Resolve-BiliPython -ProjectRoot " + _ps_quote(str(project)) + "; "
        "if ($null -eq $r) { Write-Output 'python_required' } else { Write-Output 'unexpected_python' }"
    )
    outcome = _source_resolver(code)
    assert outcome.returncode == 0, outcome.stderr
    assert outcome.stdout.strip() == "python_required"


def test_broken_venv_falls_back_to_a_valid_system_python(tmp_path: Path) -> None:
    project = tmp_path / "中文 测试"
    invalid = project / ".venv" / "Scripts" / "python.exe"
    invalid.parent.mkdir(parents=True)
    invalid.write_bytes(b"not a Windows executable")
    code = (
        "$r=Resolve-BiliPython -ProjectRoot " + _ps_quote(str(project)) + "; "
        "if ($null -ne $r) { $r | ConvertTo-Json -Compress }"
    )
    outcome = _source_resolver(code)
    assert outcome.returncode == 0, outcome.stderr
    if not outcome.stdout.strip():
        pytest.skip("Host exposes no system Python executable to PowerShell")
    report = json.loads(outcome.stdout.strip())
    assert report["source"] != "project_venv"
    assert report["version"].startswith("3.")


def test_python_probe_preserves_unicode_quotes_and_backslashes() -> None:
    argument = '中文 path with space "quoted" ending\\'
    program = "import sys, json; print(json.dumps(sys.argv[1:], ensure_ascii=False))"
    code = (
        "$r=Invoke-BiliPythonProbe -Executable " + _ps_quote(sys.executable)
        + " -Arguments @('-c', " + _ps_quote(program) + ", " + _ps_quote(argument) + "); "
        "Write-Output $r.stdout"
    )
    outcome = _source_resolver(code)
    assert outcome.returncode == 0, outcome.stderr
    assert json.loads(outcome.stdout.strip()) == [argument]


def test_powershell_cli_and_skill_bridge_return_help() -> None:
    for script in (RUNNER, BRIDGE):
        outcome = _powershell("-File", str(script), "--help")
        assert outcome.returncode == 0, outcome.stderr
        assert "usage:" in outcome.stdout.lower()
