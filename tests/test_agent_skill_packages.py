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
CANONICAL_SKILL = REPO_ROOT / "skill" / "bili-learning-automation"
GENERATED_MARKER = "GENERATED from skill/bili-learning-automation/SKILL.md; DO NOT EDIT DIRECTLY."
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
NATIVE_MIRRORS = (
    REPO_ROOT / "hermes-skills" / "bili-learning-automation",
    REPO_ROOT / "workbuddy-skills" / "bili-learning-automation",
)


def test_canonical_skill_is_single_maintained_source() -> None:
    skill_text = (CANONICAL_SKILL / "SKILL.md").read_text(encoding="utf-8")
    yaml_text = (CANONICAL_SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert "name: bili-learning-automation" in skill_text
    assert "唯一需要人工维护的 Skill 流程真源" in skill_text
    assert GENERATED_MARKER not in skill_text
    assert "$bili-learning-automation" in yaml_text
    assert list(CANONICAL_SKILL.rglob("SKILL.md")) == [CANONICAL_SKILL / "SKILL.md"]


@pytest.mark.parametrize(("skill_name", "skill_dir", "requires_openai_metadata"), SKILLS)
def test_generated_install_exit_metadata_is_unique_and_complete(
    skill_name: str, skill_dir: Path, requires_openai_metadata: bool
) -> None:
    skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

    assert f"name: {skill_name}" in skill_text
    assert "description:" in skill_text
    assert GENERATED_MARKER in skill_text
    assert list(skill_dir.rglob("SKILL.md")) == [skill_dir / "SKILL.md"]
    if requires_openai_metadata:
        yaml_text = (skill_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
        assert "$" + skill_name in yaml_text


@pytest.mark.parametrize("skill_dir", NATIVE_MIRRORS)
def test_native_junction_install_exit_is_generated(skill_dir: Path) -> None:
    skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "name: bili-learning-automation" in skill_text
    assert GENERATED_MARKER in skill_text


def test_all_install_exits_are_in_sync_with_canonical_source() -> None:
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--check"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "skill_sources_in_sync"
    assert Path(payload["canonical"]).resolve() == CANONICAL_SKILL.resolve()


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
    assert Path(payload["canonical"]).resolve() == CANONICAL_SKILL.resolve()
    assert {item["skill"] for item in payload["packages"]} == {name for name, _, _ in SKILLS}

    for skill_name, _, _ in SKILLS:
        archive_path = tmp_path / f"{skill_name}.zip"
        assert archive_path.is_file()
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            skill_files = [name for name in names if name.endswith("/SKILL.md")]
            assert skill_files == [f"{skill_name}/SKILL.md"]
            assert all(name.startswith(f"{skill_name}/") for name in names)
            packaged_skill = archive.read(f"{skill_name}/SKILL.md").decode("utf-8")
            assert GENERATED_MARKER in packaged_skill
            assert not any(
                forbidden in name.lower()
                for name in names
                for forbidden in ("/key/", "cookies.txt", "config/local.json", "/.runtime/", "/notes/")
            )
