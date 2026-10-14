from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import bili_learning.config as config
from bili_learning.config import configure_cookie_file, configure_obsidian

ROOT = Path(__file__).resolve().parents[1]


def test_pinned_windows_tool_matches_official_manifest() -> None:
    executable = ROOT / "tools" / "yt-dlp.exe"
    manifest = json.loads((ROOT / "tools" / "yt-dlp.release.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "2026.08.19"
    assert manifest["name"] == executable.name
    assert manifest["platform"] == "windows-x64"
    assert executable.stat().st_size > 10_000_000
    digest = hashlib.sha256()
    with executable.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    assert digest.hexdigest() == manifest["sha256"]
    assert (ROOT / "tools" / "YT-DLP-LICENSE.txt").is_file()
    assert (ROOT / "tools" / "THIRD_PARTY_LICENSES.txt").stat().st_size > 10000


def test_fresh_agent_configure_obsidian_sets_project_local_notes_root(tmp_path: Path) -> None:
    vault = tmp_path / "My Vault"
    (vault / ".obsidian").mkdir(parents=True)
    saved_path = configure_obsidian(tmp_path, vault)
    payload = json.loads(saved_path.read_text(encoding="utf-8"))

    assert payload["notes_root"] == "notes/bilibili"
    assert payload["vault_root"] == str(vault.resolve())
    assert payload["notes_subdir"] == "bilibili"
    assert (tmp_path / "notes" / "bilibili").is_dir()


def test_existing_direct_vault_is_not_silently_migrated(tmp_path: Path) -> None:
    vault = tmp_path / "My Vault"
    (vault / ".obsidian").mkdir(parents=True)
    local = tmp_path / "config" / "local.json"
    local.parent.mkdir()
    local.write_text(json.dumps({"vault_root": str(vault), "notes_subdir": "legacy"}), encoding="utf-8")
    configure_obsidian(tmp_path, vault)
    saved = json.loads(local.read_text(encoding="utf-8"))

    assert "notes_root" not in saved
    assert saved["vault_root"] == str(vault.resolve())


def test_config_replace_failure_preserves_original_and_cleans_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local = tmp_path / "config" / "local.json"
    local.parent.mkdir()
    old = json.dumps({"notes_root": "notes/bilibili"}, ensure_ascii=False)
    local.write_text(old, encoding="utf-8")
    cookie = tmp_path / "private_cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    def fail_replace(_source: os.PathLike[str], _destination: os.PathLike[str]) -> None:
        raise OSError("simulated config write interruption")

    monkeypatch.setattr(config.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        configure_cookie_file(tmp_path, cookie)

    assert local.read_text(encoding="utf-8") == old
    assert list(local.parent.glob(".local-config-*.tmp")) == []
    assert list((tmp_path / ".runtime" / "config-tmp").glob("*.tmp")) == []


def test_config_write_does_not_depend_on_deletion_after_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cookie = tmp_path / "cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    def forbidden_delete(*_args: object, **_kwargs: object) -> None:
        raise OSError("safe-delete forbidden")

    monkeypatch.setattr(Path, "unlink", forbidden_delete)
    path = configure_cookie_file(tmp_path, cookie)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["cookie_file"] == str(cookie.resolve())
