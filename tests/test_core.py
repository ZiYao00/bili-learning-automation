from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import bili_learning.navigation as navigation
from bili_learning.collector import (
    cleanup_stale_jobs,
    create_job,
    description_state,
    find_existing_note,
    run_ytdlp,
    select_subtitle,
)
from bili_learning.config import ExecutableResolution, Settings, find_ytdlp, load_settings, validate_taxonomy
from bili_learning.doctor import doctor_report
from bili_learning.frontmatter import parse_frontmatter
from bili_learning.input_resolver import resolve_input
from bili_learning.lifecycle import finalize_note, prepare_note
from bili_learning.note_template import bvid_line, note_filename, quote_description, render_note_skeleton
from bili_learning.organizer import organize_note
from bili_learning.publisher import publish_validated_draft
from bili_learning.runtime import (
    ReservationBusyError,
    bind_reservation,
    claim_reservation,
    cleanup_job,
    file_lock,
    safe_job_path,
)
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
    assert filing["suggested_title"] == "分段生成"
    assert filing["category_path"] == ["00-待整理"]
    assert filing["suggested_category_path"] == ["01-视频生成", "01-MiniMax-H3"]
    assert filing["suggested_route_id"] == "h3_segment"


def test_note_filename_uses_a_clean_title_and_collision_sequence() -> None:
    assert note_filename("MiniMax-H3 分段生成") == "MiniMax-H3 分段生成.md"
    assert note_filename("MiniMax-H3 分段生成", 2) == "MiniMax-H3 分段生成（2）.md"


def test_taxonomy_uses_a_specific_topic_title_in_the_inbox(taxonomy: dict) -> None:
    taxonomy["routes"].insert(
        0,
        {
            "id": "h3_grid",
            "path": ["01-视频生成", "01-MiniMax-H3"],
            "all_patterns": ["H3"],
            "any_patterns": ["9宫格"],
            "task": "9宫格",
            "title": "9宫格提示词模板",
            "tags": ["视频生成", "工作流", "9宫格"],
        },
    )
    filing = classify({"title": "MiniMax H3 9宫格实测", "description": "", "tags": []}, taxonomy)
    assert filing["suggested_title"] == "9宫格提示词模板"
    assert filing["category_path"] == ["00-待整理"]


def test_taxonomy_uses_node_prompt_topic_title_in_the_inbox(taxonomy: dict) -> None:
    taxonomy["routes"].insert(
        0,
        {
            "id": "h3_node_prompt",
            "path": ["01-视频生成", "01-MiniMax-H3"],
            "all_patterns": ["H3", "节点", "提示词优化"],
            "task": "节点升级",
            "title": "节点升级与提示词优化",
            "tags": ["视频生成", "工作流", "节点", "提示词优化"],
        },
    )
    filing = classify(
        {"title": "H3智能一体化节点重磅升级，支持本地提示词优化", "description": "", "tags": []}, taxonomy
    )
    assert filing["suggested_title"] == "节点升级与提示词优化"
    assert filing["required_tags"] == ["视频生成", "工作流", "节点", "提示词优化", "MiniMax-H3"]


def test_description_states() -> None:
    assert description_state({"description": "hello"}) == ("present", "hello")
    assert description_state({"description": ""}) == ("confirmed_empty", "")
    assert description_state({"description": None}) == ("failed", "")
    assert description_state({}) == ("failed", "")
    assert description_state({"description": 123}) == ("failed", "")
    assert description_state({"description": "info"}, "sidecar") == ("failed", "")
    assert description_state({"description": "info\n"}, "info") == ("present", "info")


def test_description_renders_compact_resources_and_preserves_raw_source() -> None:
    description = "节点升级说明\n工作流地址：\nhttps://example.com/workflow\n仓库：https://example.com/repo"
    rendered = quote_description(description, "present")
    assert "## 视频简介" in rendered
    assert "- [工作流地址](https://example.com/workflow)" in rendered
    assert "- [仓库](https://example.com/repo)" in rendered
    assert "<summary>UP 主原始简介</summary>" in rendered
    assert description in rendered


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
        text.replace("> 待智能体根据字幕填写。", "> 这是结论。")
        .replace("待智能体根据字幕填写。", "1. 这是步骤。", 1)
        .replace("待智能体根据字幕填写。", "- 这是坑点。", 1)
        .replace("- [ ] 待智能体根据字幕填写。", "- [ ] 完成一次最小测试。")
    )


def test_validator_checks_real_metadata_and_markers(tmp_path: Path) -> None:
    note = tmp_path / "H3 分段工作流.md"
    job = {
        "schema_version": 1,
        "bvid": "BV1TXua68EYi",
        "canonical_url": "https://www.bilibili.com/video/BV1TXua68EYi/",
        "author": "UP",
        "published": "2026-08-11",
        "duration": "07:05",
        "description": "原始简介",
        "description_status": "present",
        "canonical_title": "H3 分段工作流",
        "note_filename": note.name,
        "required_tags": ["视频生成", "MiniMax-H3"],
        "note_path": str(note),
    }
    note.write_text(_complete_ai_regions(render_note_skeleton(job)), encoding="utf-8")
    assert validate_note(note, job) == []
    note.write_text(
        note.read_text(encoding="utf-8").replace('author: "UP"', 'author: "OTHER"'), encoding="utf-8"
    )
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
        ytdlp=ExecutableResolution(ytdlp, "test", ("test",)),
        local_config_path=tmp_path / "config" / "local.json",
    )


def test_create_job_writes_runtime_draft_without_publishing_note(tmp_path: Path, taxonomy: dict) -> None:
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
    note_path = Path(payload["note_path"])
    draft_path = Path(payload["draft_path"])
    assert note_path.name == "H3 分段工作流.md"
    assert not note_path.exists()
    assert draft_path.parent == job_dir
    assert draft_path.name == note_path.name
    draft_text = draft_path.read_text(encoding="utf-8")
    assert 'source: "https://www.bilibili.com/video/BV1TXua68EYi/"' in draft_text
    assert bvid_line("BV1TXua68EYi") in draft_text


def test_frontmatter_quotes_yaml_special_characters_round_trip() -> None:
    job = {
        "author": "A: # [creator]",
        "published": "2026-08-20",
        "duration": "07:05",
        "canonical_url": "https://www.bilibili.com/video/BV1TXua68EYi/?a=b#c",
        "required_tags": ["true", "[模型]", "a: b"],
    }
    text = render_note_skeleton(
        {
            **job,
            "bvid": "BV1TXua68EYi",
            "description": "简介",
            "description_status": "present",
            "canonical_title": "测试",
        }
    )
    values, tags = parse_frontmatter(text)
    assert values["author"] == job["author"]
    assert values["source"] == job["canonical_url"]
    assert tags == job["required_tags"]


def test_publish_validated_draft_is_no_overwrite(tmp_path: Path) -> None:
    draft = tmp_path / "runtime" / "MiniMax-H3 分段生成__BV1TXua68EYi.md"
    target = tmp_path / "notes" / draft.name
    draft.parent.mkdir(parents=True)
    draft.write_text("validated note", encoding="utf-8")
    publish_validated_draft(draft, target)
    assert target.read_text(encoding="utf-8") == "validated note"
    assert draft.is_file()
    with pytest.raises(FileExistsError):
        publish_validated_draft(draft, target)


def test_publish_removes_runtime_only_ai_markers(tmp_path: Path) -> None:
    draft = tmp_path / "runtime" / "draft.md"
    target = tmp_path / "notes" / "published.md"
    draft.parent.mkdir(parents=True)
    draft.write_text("<!-- BILI_AI_SUMMARY_START -->\n内容\n<!-- BILI_AI_SUMMARY_END -->\n", encoding="utf-8")
    publish_validated_draft(draft, target)
    assert target.read_text(encoding="utf-8") == "\n内容\n\n"


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


def test_duplicate_detection_uses_frontmatter_source_not_body_text(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    canonical = "https://www.bilibili.com/video/BV1TXua68EYi/"
    body_reference = notes / "related-video.md"
    body_reference.write_text(f"# 相关视频\n\n{canonical}\n", encoding="utf-8")
    assert find_existing_note(notes, canonical, "BV1TXua68EYi") is None

    published = notes / "published.md"
    published.write_text(f"---\nsource: {canonical}\n---\n\n# 已发布\n", encoding="utf-8")
    assert find_existing_note(notes, canonical, "BV1TXua68EYi") == published


def test_duplicate_detection_keeps_legacy_bvid_filename_compatibility(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    legacy = notes / "旧笔记__BV1TXua68EYi.md"
    legacy.write_text("# 旧笔记\n", encoding="utf-8")
    assert find_existing_note(notes, "https://www.bilibili.com/video/BV1TXua68EYi/", "BV1TXua68EYi") == legacy


def test_duplicate_detection_supports_the_visible_bvid_line(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    note = notes / "无 source.md"
    note.write_text(f"# 标题\n\n{bvid_line('BV1TXua68EYi')}\n", encoding="utf-8")
    assert find_existing_note(notes, "https://www.bilibili.com/video/BV1TXua68EYi/", "BV1TXua68EYi") == note


def test_reservation_spans_job_lifecycle_and_cleanup_releases_it(tmp_path: Path) -> None:
    runtime = tmp_path / ".runtime" / "bilibili-learning"
    reservation = claim_reservation(runtime, "BV1TXua68EYi")
    with pytest.raises(ReservationBusyError):
        claim_reservation(runtime, "BV1TXua68EYi")

    job = runtime / "BV1TXua68EYi-job"
    job.mkdir()
    (job / "job.json").write_text(json.dumps({"bvid": "BV1TXua68EYi"}), encoding="utf-8")
    bind_reservation(reservation, job)
    cleanup_job(runtime, job)
    assert not job.exists()
    assert claim_reservation(runtime, "BV1TXua68EYi").path.is_file()


def test_core_prepare_dry_run_returns_versioned_status_and_releases_reservation(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)
    payload, code = prepare_note(tmp_path, "BV1TXua68EYi", dry_run=True)
    assert code == 0
    assert payload["schema_version"] == 1
    assert payload["status"] == "ready_to_process"
    locks = tmp_path / ".runtime" / "bilibili-learning" / "locks"
    assert not list(locks.glob("*.reservation.json"))


def _write_e2e_config(project_root: Path, taxonomy: dict) -> None:
    config_dir = project_root / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")


def _fake_ytdlp(_settings: Settings, job_dir: Path, canonical_url: str) -> None:
    bvid = canonical_url.rstrip("/").rsplit("/", 1)[-1]
    info = {
        "title": "H3 分段工作流",
        "description": "原始简介",
        "tags": [],
        "uploader": "UP",
        "upload_date": "20260811",
        "duration": 425,
    }
    (job_dir / f"{bvid}.info.json").write_text(json.dumps(info), encoding="utf-8")
    (job_dir / f"{bvid}.description").write_text("原始简介", encoding="utf-8")
    (job_dir / f"{bvid}.ai-zh.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n字幕\n", encoding="utf-8")


def test_e2e_draft_publish_navigation_and_duplicate(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    first, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and first["status"] == "materials_ready"
    draft = Path(first["draft_path"])
    target = Path(first["note_path"])
    assert draft.is_file() and not target.exists()

    draft.write_text(_complete_ai_regions(draft.read_text(encoding="utf-8")), encoding="utf-8")
    completed, code = finalize_note(tmp_path, Path(first["job_dir"]), draft)
    assert code == 0 and completed["status"] == "note_ready"
    assert target.is_file()
    assert "BILI_AI_" not in target.read_text(encoding="utf-8")
    assert not Path(first["job_dir"]).exists()
    nav = tmp_path / "notes" / "bilibili" / "99-导航" / "首页.md"
    assert nav.is_file()

    duplicate, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and duplicate["status"] == "already_exists"


def test_e2e_unfinished_draft_never_enters_navigation_and_invalid_draft_is_not_published(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    unfinished, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and unfinished["status"] == "materials_ready"
    finished, code = prepare_note(tmp_path, "BV1os8G6zEnU")
    assert code == 0 and finished["status"] == "materials_ready"
    finished_draft = Path(finished["draft_path"])
    finished_draft.write_text(_complete_ai_regions(finished_draft.read_text(encoding="utf-8")), encoding="utf-8")
    completed, code = finalize_note(tmp_path, Path(finished["job_dir"]), finished_draft)
    assert code == 0 and completed["status"] == "note_ready"
    nav_text = (tmp_path / "notes" / "bilibili" / "99-导航" / "00-待整理.md").read_text(encoding="utf-8")
    assert "H3 分段工作流" in nav_text

    invalid, code = finalize_note(tmp_path, Path(unfinished["job_dir"]), Path(unfinished["draft_path"]))
    assert code == 2 and invalid["status"] == "note_invalid"
    assert Path(unfinished["note_path"]).name == "H3 分段工作流.md"
    assert Path(finished["note_path"]).name == "H3 分段工作流（2）.md"
    assert Path(finished["note_path"]).exists()
    assert not Path(unfinished["job_dir"]).exists()


def test_organize_note_updates_title_intro_moves_and_rebuilds_navigation(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    source = settings.notes_root / "00-待整理" / "H3 分段工作流.md"
    source.parent.mkdir(parents=True)
    job = {
        "bvid": "BV1TXua68EYi",
        "author": "UP",
        "published": "2026-08-11",
        "duration": "07:05",
        "canonical_url": "https://www.bilibili.com/video/BV1TXua68EYi/",
        "required_tags": ["视频生成", "工作流", "MiniMax-H3"],
        "description": "原始说明\n工作流：\nhttps://example.com/workflow",
        "description_status": "present",
        "canonical_title": "H3 分段工作流",
    }
    source.write_text(
        _complete_ai_regions(render_note_skeleton(job)).replace("<!-- BILI_AI_SUMMARY_START -->", "").replace("<!-- BILI_AI_SUMMARY_END -->", "").replace("<!-- BILI_AI_STEPS_START -->", "").replace("<!-- BILI_AI_STEPS_END -->", "").replace("<!-- BILI_AI_PITFALLS_START -->", "").replace("<!-- BILI_AI_PITFALLS_END -->", "").replace("<!-- BILI_AI_PRACTICE_START -->", "").replace("<!-- BILI_AI_PRACTICE_END -->", ""),
        encoding="utf-8",
    )
    target = organize_note(settings, source, "H3 分段生成", "将长视频拆成连续片段生成。")
    assert target == settings.notes_root / "01-视频生成" / "01-MiniMax-H3" / "H3 分段生成.md"
    assert not source.exists()
    organized = target.read_text(encoding="utf-8")
    assert organized.startswith("---")
    assert "# H3 分段生成" in organized
    assert "将长视频拆成连续片段生成。" in organized
    assert bvid_line("BV1TXua68EYi") in organized
    assert (settings.notes_root / "99-导航" / "01-视频生成.md").is_file()
    assert "00-待整理]]（0）" in (settings.notes_root / "99-导航" / "首页.md").read_text(encoding="utf-8")


def test_organize_note_migrates_a_legacy_description_and_bvid_filename(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    source = settings.notes_root / "00-待整理" / "旧标题__BV1TXua68EYi.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "---\nsource: \"https://www.bilibili.com/video/BV1TXua68EYi/\"\ntags:\n  - \"视频生成\"\n  - \"工作流\"\n---\n\n"
        "# 旧标题\n\n> **视频简介**\n>\n> 原始说明\n> 工作流：\n> https://example.com/workflow\n\n"
        "<iframe src=\"https://player.bilibili.com/player.html?bvid=BV1TXua68EYi\"></iframe>\n",
        encoding="utf-8",
    )
    target = organize_note(settings, source, "整理后标题", "整理后的简介摘要。")
    text = target.read_text(encoding="utf-8")
    assert target.name == "整理后标题.md"
    assert bvid_line("BV1TXua68EYi") in text
    assert "## UP 主资源" in text
    assert "[工作流](https://example.com/workflow)" in text
    assert "<summary>UP 主原始简介</summary>" in text


def test_navigation_rebuilds_are_serialized(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, taxonomy)
    active = 0
    maximum_active = 0
    entered = threading.Event()
    state_lock = threading.Lock()

    def slow_build(_settings: Settings) -> None:
        nonlocal active, maximum_active
        with state_lock:
            active += 1
            maximum_active = max(maximum_active, active)
            entered.set()
        time.sleep(0.15)
        with state_lock:
            active -= 1

    monkeypatch.setattr(navigation, "_build_navigation", slow_build)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(navigation.build_navigation, settings)
        assert entered.wait(timeout=1)
        second = executor.submit(navigation.build_navigation, settings)
        first.result(timeout=2)
        second.result(timeout=2)
    assert maximum_active == 1


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
    assert command[command.index("--sub-format") + 1] == "srt"
    assert captured["timeout"] == 180


def test_select_subtitle_only_accepts_supported_srt_languages(tmp_path: Path) -> None:
    (tmp_path / "video.zh-Hans.srt").write_text("字幕", encoding="utf-8")
    (tmp_path / "video.ai-zh.srt").write_text("AI 字幕", encoding="utf-8")
    (tmp_path / "video.zh-Hans.json").write_text("{}", encoding="utf-8")
    assert select_subtitle(tmp_path) == tmp_path / "video.ai-zh.srt"


def test_ytdlp_resolution_prefers_environment_then_local_then_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BILI_LEARNING_YTDLP", "C:/configured/yt-dlp.exe")
    assert find_ytdlp(tmp_path, {"ytdlp": "local/yt-dlp"}).source == "environment"
    monkeypatch.delenv("BILI_LEARNING_YTDLP")
    local = find_ytdlp(tmp_path, {"ytdlp": "local/yt-dlp"})
    assert local.source == "local_config"
    assert local.path == tmp_path / "local" / "yt-dlp"
    monkeypatch.setattr("bili_learning.config.shutil.which", lambda _: "C:/PATH/yt-dlp.exe")
    assert find_ytdlp(tmp_path, {}).source == "path"


def test_load_settings_reads_ignored_local_config(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    (config_dir / "local.json").write_text(json.dumps({"ytdlp": "tools/yt-dlp.exe"}), encoding="utf-8")
    monkeypatch.delenv("BILI_LEARNING_YTDLP", raising=False)
    monkeypatch.setattr("bili_learning.config.shutil.which", lambda _: None)
    settings = load_settings(tmp_path)
    assert settings.ytdlp.source == "local_config"
    assert settings.ytdlp.path == tmp_path / "tools" / "yt-dlp.exe"


def test_doctor_reports_ytdlp_source_and_version(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path, taxonomy)

    class Completed:
        returncode = 0
        stdout = "2026.08.20\n"
        stderr = ""

    monkeypatch.setattr("bili_learning.doctor.subprocess.run", lambda *args, **kwargs: Completed())
    report = doctor_report(settings)
    ytdlp = next(check for check in report["checks"] if check["code"] == "ytdlp_ready")
    assert ytdlp["source"] == "test"
    assert ytdlp["version"] == "2026.08.20"
    assert {"python_version", "project_root_exists", "notes_root_writable", "runtime_root_writable"} <= {
        check["code"] for check in report["checks"]
    }


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
