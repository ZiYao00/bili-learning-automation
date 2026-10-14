from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_version_metadata_matches_pyproject_single_source() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"(?P<version>\d+\.\d+\.\d+)"\s*$', pyproject)
    assert match, "project.version must be a single semantic version in pyproject.toml"
    version = match.group("version")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"(?m)^## \[" + re.escape(version) + r"\] - \d{4}-\d{2}-\d{2}$", changelog)
    assert changelog.index("## [Unreleased]") < changelog.index(f"## [{version}]")
    for doc in ("README.md", "README.en.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert f"v{version}" in text, f"{doc} must match pyproject.toml"

    # The pinned yt-dlp distribution has its own upstream version convention.
    manifest = (ROOT / "tools" / "yt-dlp.release.json").read_text(encoding="utf-8")
    assert '"version": "2026.08.19"' in manifest
