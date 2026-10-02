from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_chatgpt_skill.py"
LAUNCHER = REPO_ROOT / "scripts" / "run_bili_learning.py"
CANONICAL_SKILL = REPO_ROOT / "skill" / "bili-learning-automation"
LOCAL_BRIDGE = CANONICAL_SKILL / "scripts" / "local_bridge.py"
CHATGPT_SKILL_NAME = "bili-learning-automation-chatgpt"
CHATGPT_REFERENCES = {
    "AGENT-INTEGRATION.md",
    "BILIBILI-COOKIE.md",
    "CONFIGURATION.md",
    "MAINTENANCE-HANDOFF.md",
    "NOTE-ORGANIZATION.md",
    "OBSIDIAN-STYLING.md",
    "TROUBLESHOOTING.md",
    "LIGHT-WORKFLOW.md",
    "CODEX-VIDEO-NOTE-GUIDE.md",
    "KNOWLEDGE-DENSE-WORKFLOW.md",
    "STANDARD-VIDEO-NOTE-EXAMPLE.md",
}


def run_build(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def test_canonical_skill_is_the_only_local_skill_source() -> None:
    skill_text = (CANONICAL_SKILL / "SKILL.md").read_text(encoding="utf-8")
    yaml_text = (CANONICAL_SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert "name: bili-learning-automation" in skill_text
    assert "唯一需要人工维护" in skill_text
    assert "目录链接安装" in skill_text
    assert "$bili-learning-automation" in yaml_text
    assert list(CANONICAL_SKILL.rglob("SKILL.md")) == [CANONICAL_SKILL / "SKILL.md"]
    assert LOCAL_BRIDGE.is_file()
    assert (CANONICAL_SKILL / "scripts" / "local_bridge.ps1").is_file()


def test_chatgpt_package_render_is_valid() -> None:
    result = run_build("--check")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "chatgpt_skill_ready"
    assert Path(payload["canonical"]).resolve() == CANONICAL_SKILL.resolve()
    assert payload["skill"] == CHATGPT_SKILL_NAME
    assert payload["files"] == 13


def test_shared_launcher_works_outside_project_directory(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert "bili-learning" in result.stdout
    assert "onboarding" in result.stdout
    assert "prepare-description" in result.stdout


def test_local_bridge_resolves_project_outside_project_directory(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(LOCAL_BRIDGE), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert "bili-learning" in result.stdout
    assert "onboarding" in result.stdout


def test_build_creates_only_chatgpt_archive_with_safe_references(tmp_path: Path) -> None:
    result = run_build("--output-dir", str(tmp_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "chatgpt_skill_built"
    assert payload["files"] == 13

    archive_path = tmp_path / f"{CHATGPT_SKILL_NAME}.zip"
    assert archive_path.is_file()
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        prefix = f"{CHATGPT_SKILL_NAME}/"
        assert all(name.startswith(prefix) for name in names)
        assert f"{prefix}SKILL.md" in names
        assert f"{prefix}agents/openai.yaml" in names
        assert not any(f"{prefix}scripts/" in name for name in names)

        ref_prefix = f"{prefix}references/"
        packaged_references = {name.removeprefix(ref_prefix) for name in names if name.startswith(ref_prefix)}
        assert packaged_references == CHATGPT_REFERENCES

        skill_text = archive.read(f"{prefix}SKILL.md").decode("utf-8")
        yaml_text = archive.read(f"{prefix}agents/openai.yaml").decode("utf-8")
        assert f"name: {CHATGPT_SKILL_NAME}" in skill_text
        assert "ChatGPT Web 宿主边界" in skill_text
        assert "$bili-learning-automation-chatgpt" in yaml_text
        assert not any(
            forbidden in name.lower()
            for name in names
            for forbidden in (
                "/key/",
                "cookies.txt",
                "bilibili_cookies.txt",
                "config/local.json",
                "pinned-comment-whitelist.local.json",
                "/.runtime/",
                "/notes/",
            )
        )


def test_chatgpt_archive_is_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert run_build("--output-dir", str(first)).returncode == 0
    assert run_build("--output-dir", str(second)).returncode == 0

    first_bytes = (first / f"{CHATGPT_SKILL_NAME}.zip").read_bytes()
    second_bytes = (second / f"{CHATGPT_SKILL_NAME}.zip").read_bytes()
    assert first_bytes == second_bytes
