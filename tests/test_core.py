from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from bili_learning.collector import cleanup_stale_jobs, create_job, description_state, run_ytdlp
from bili_learning.config import Settings, load_settings, validate_taxonomy
from bili_learning.input_resolver import resolve_input
from bili_learning.note_template import note_filename, render_note_skeleton
from bili_learning.runtime import file_lock, safe_job_path
from bili_learning.taxonomy import classify
from bili_learning.validator import validate_note


@pytest.fixture
def taxonomy() -> dict:
    return {
        "version": 1,
        "notes_root": "notes/bilibili",
        "navigation_dir": "99-导航",
        "fallback": {"path": ["00-待整理"], "task": "待整理", "tags": ["待整理"]},
        "models": [{"canonical": "MiniMax-H3", "aliases": ["H3", "MiniMax-H3"]}],
        "routes": [
            {
                "id": "h3_segment",
                "path": ["01-视频生成", "01-MiniMax-H3"],
                "all_patterns": ["H3", "分段"],
                "task": "分段生成",
                "tags": ["视频生成", "工作流"],
            }
        ],
    }


def test_resolve_bvid() -> None:
    result = resolve_input("BV1TXua68EYi")
    assert result.bvid == "BV1TXua68EYi"
    assert result.canonical_url == "https://www.bilibili.com/video/BV1TXua68EYi/"


def test_resolve_bvid_inside_text() -> None:
    result = resolve_input("复制链接 https://www.bilibili.com/video/BV1TXua68EYi/?spm_id_from=333")
    assert result.bvid == "BV1TXua68EYi"


def test_reject_non_bilibili_url_without_bvid() -> None:
    with pytest.raises(ValueError):
        resolve_input("https://example.com/video/123")


def test_taxonomy_classification(taxonomy: dict) -> None:
    filing = classify({"title": "H3 分段工作流", "description": "", "tags": []}, taxonomy)
    assert filing["canonical_title"] == "MiniMax-H3 分段生成"
    assert filing["category_path"] == ["01-视频生成", "01-MiniMax-H3"]


def test_note_filename_is_unique_per_bvid() -> None:
    first = note_filename("MiniMax-H3 分段生成", "BV1TXua68EYi")
    second = note_filename("MiniMax-H3 分段生成", "BV1os8G6zEnU")
    assert first != second
    assert first.endswith("__BV1TXua68EYi.md")


def test_description_states() -> None:
    assert description_state({"description": "hello"}) == ("present", "hello")
    assert description_state({"description": ""}) == ("confirmed_empty", "")
    assert description_state({"description": None}) == ("confirmed_empty", "")
    assert description_state({}) == ("failed", "")
    assert description_state({"description": 123}) == ("failed", "")


def test_taxonomy_rejects_duplicate_route_ids(taxonomy: dict) -> None:
    taxonomy["routes"].append(dict(taxonomy["routes"][0]))
    with pytest.raises(ValueError, match="重复"):
        validate_taxonomy(taxonomy)


def test_notes_root_comes_from_taxonomy(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    taxonomy["notes_root"] = "custom/notes"
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    monkeypatch.delenv("BILI_LEARNING_TAXONOMY", raising=False)
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)
    settings = load_settings(tmp_path)
    assert settings.notes_root == tmp_path / "custom" / "notes"


def _complete_ai_regions(text: str) -> str:
    return (
        text.replace("> 待 Hermes 根据字幕填写。", "> 这是结论。")
        .replace("待 Hermes 根据字幕填写。", "1. 这是步骤。", 1)
        .replace("待 Hermes 根据字幕填写。", "- 这是坑点。", 1)
        .replace("- [ ] 待 Hermes 根据字幕填写。", "- [ ] 完成一次最小测试。")
    )


def test_validator_checks_real_metadata_and_markers(tmp_path: Path) -> None:
    note = tmp_path / "MiniMax-H3 分段生成__BV1TXua68EYi.md"
    job = {
        "bvid": "BV1TXua68EYi",
        "canonical_url": "https://www.bilibili.com/video/BV1TXua68EYi/",
        "author": "UP",
        "published": "2026-08-11",
        "duration": "07:05",
        "description": "原始简介",
        "description_status": "present",
        "canonical_title": "MiniMax-H3 分段生成",
        "required_tags": ["视频生成", "MiniMax-H3"],
        "note_path": str(note),
    }
    note.write_text(_complete_ai_regions(render_note_skeleton(job)), encoding="utf-8")
    assert validate_note(note, job) == []
    note.write_text(note.read_text(encoding="utf-8").replace("author: UP", "author: OTHER"), encoding="utf-8")
    assert any("author" in error for error in validate_note(note, job))


def test_safe_job_path_blocks_escape(tmp_path: Path) -> None:
    runtime = tmp_path / ".runtime" / "bilibili-learning"
    runtime.mkdir(parents=True)
    inside = runtime / "job"
    inside.mkdir()
    assert safe_job_path(runtime, inside) == inside.resolve()
    with pytest.raises(ValueError):
        safe_job_path(runtime, tmp_path / "outside")


def _settings(tmp_path: Path, taxonomy: dict) -> Settings:
    taxonomy_path = tmp_path / "taxonomy.json"
    taxonomy_path.write_text(json.dumps(taxonomy), encoding="utf-8")
    notes_root = tmp_path / "notes"
    runtime_root = tmp_path / ".runtime" / "bilibili-learning"
    cookie_file = tmp_path / "cookie.txt"
    cookie_file.write_text("placeholder", encoding="utf-8")
    ytdlp = tmp_path / "yt-dlp"
    ytdlp.write_text("placeholder", encoding="utf-8")
    return Settings(
        project_root=tmp_path,
        taxonomy_path=taxonomy_path,
        taxonomy=taxonomy,
        notes_root=notes_root,
        navigation_dir="99-导航",
        runtime_root=runtime_root,
        cookie_file=cookie_file,
        ytdlp=ytdlp,
    )


def test_create_job_writes_bvid_skeleton(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    job_dir = settings.runtime_root / "job"
    job_dir.mkdir(parents=True)
    subtitle = job_dir / "video.ai-zh.srt"
    subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\n字幕\n", encoding="utf-8")
    payload = create_job(
        settings,
        "BV1TXua68EYi",
        "https://www.bilibili.com/video/BV1TXua68EYi/",
        {
            "title": "H3 分段工作流",
            "description": "原始简介",
            "tags": [],
            "uploader": "UP",
            "upload_date": "20260811",
            "duration": 425,
        },
        subtitle,
        job_dir,
    )
    note = Path(payload["note_path"])
    assert note.name == "MiniMax-H3 分段生成__BV1TXua68EYi.md"
    assert note.is_file()
    assert "source: https://www.bilibili.com/video/BV1TXua68EYi/" in note.read_text(encoding="utf-8")


def test_cleanup_stale_jobs_keeps_locks(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    settings.runtime_root.mkdir(parents=True)
    stale_job = settings.runtime_root / "BV1-old"
    stale_job.mkdir()
    locks = settings.runtime_root / "locks"
    locks.mkdir()
    old = time.time() - 7200
    os.utime(stale_job, (old, old))
    os.utime(locks, (old, old))
    assert cleanup_stale_jobs(settings) == 1
    assert not stale_job.exists()
    assert locks.is_dir()


def test_ytdlp_command_never_downloads_media(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, taxonomy)
    job_dir = settings.runtime_root / "job"
    job_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        captured["command"] = command
        captured["timeout"] = kwargs.get("timeout")
        return Completed()

    monkeypatch.setattr("bili_learning.collector.subprocess.run", fake_run)
    run_ytdlp(settings, job_dir, "https://www.bilibili.com/video/BV1TXua68EYi/")
    command = captured["command"]
    assert isinstance(command, list)
    assert "--skip-download" in command
    assert "--write-subs" in command
    assert "--write-auto-subs" in command
    assert captured["timeout"] == 180


def test_file_lock_blocks_concurrent_owner(tmp_path: Path) -> None:
    lock = tmp_path / "locks" / "BV1TXua68EYi.lock"
    with file_lock(lock):
        with pytest.raises(RuntimeError, match="已有任务正在处理"):
            with file_lock(lock):
                pass
    assert not lock.exists()


def test_file_lock_recovers_stale_file(tmp_path: Path) -> None:
    lock = tmp_path / "locks" / "BV1TXua68EYi.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("old", encoding="utf-8")
    old = time.time() - 7200
    os.utime(lock, (old, old))
    with file_lock(lock, stale_seconds=3600):
        assert lock.is_file()
    assert not lock.exists()
