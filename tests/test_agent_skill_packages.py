from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_agent_skill_packages.py"
LAUNCHER = REPO_ROOT / "scripts" / "run_bili_learning.py"
SKILLS = (
    (
        "bili-learning-automation-chatgpt",
        REPO_ROOT / "chatgpt-skills" / "bili-learning-automation-chatgpt",
        True,
    ),
    (
        "bili-learning-automation-codex",
        REPO_ROOT / ".agents" / "skills" / "bili-learning-automation-codex",
        True,
    ),
    (
        "bili-learning-automation-hermes",
        REPO_ROOT / "hermes-skills" / "bili-learning-automation-hermes",
        False,
    ),
    (
        "bili-learning-automation-workbuddy",
        REPO_ROOT / "workbuddy-skills" / "bili-learning-automation-workbuddy",
        False,
    ),
)


@pytest.mark.parametrize(("skill_name", "skill_dir", "requires_openai_metadata"), SKILLS)
def test_skill_metadata_is_unique_and_complete(
    skill_name: str, skill_dir: Path, requires_openai_metadata: bool
) -> None:
    skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

    assert f"name: {skill_name}" in skill_text
    assert "description:" in skill_text
    assert list(skill_dir.rglob("SKILL.md")) == [skill_dir / "SKILL.md"]
    if requires_openai_metadata:
        yaml_text = (skill_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
        assert "$" + skill_name in yaml_text


def test_launcher_works_outside_project_directory(tmp_path: Path) -> None:
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


def test_build_creates_four_isolated_skill_archives(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--output-dir", str(tmp_path)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "packages_ready"
    assert {item["skill"] for item in payload["packages"]} == {name for name, _, _ in SKILLS}

    for skill_name, _, _ in SKILLS:
        archive_path = tmp_path / f"{skill_name}.zip"
        assert archive_path.is_file()
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            skill_files = [name for name in names if name.endswith("/SKILL.md")]
            assert skill_files == [f"{skill_name}/SKILL.md"]
            assert all(name.startswith(f"{skill_name}/") for name in names)
            assert not any(
                forbidden in name.lower()
                for name in names
                for forbidden in ("/key/", "cookies.txt", "config/local.json", "/.runtime/", "/notes/")
            )
