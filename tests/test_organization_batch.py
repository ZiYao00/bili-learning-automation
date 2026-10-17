"""Organizer v2 safety, crash recovery and opt-in deletion contracts (isolated tmp_path only)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from bili_learning.config import ExecutableResolution, Settings
from bili_learning.note_library import note_sha256
from bili_learning.organization_batch import list_inbox, organize_batch
from bili_learning.organization_duplicates import duplicates_inventory, recycle_duplicates
from bili_learning.organizer import OrganizerNavigationPending, organize_note, organize_resource_note


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    taxonomy = {
        "version": 1,
        "notes_root": "notes/bilibili",
        "navigation_dir": "99-导航",
        "fallback": {"path": ["00-待整理"], "task": "待整理", "tags": []},
        "organization": {"max_depth": 2, "resource_root": "05-资源"},
        "models": [{"canonical": "MiniMax-H3", "aliases": ["MiniMax-H3", "H3"]}],
        "routes": [],
    }
    return Settings(
        project_root=tmp_path,
        taxonomy_path=tmp_path / "taxonomy.json",
        taxonomy=taxonomy,
        notes_root=tmp_path / "notes" / "bilibili",
        vault_root=None,
        notes_subdir=None,
        notes_source="test",
        notes_is_fallback=False,
        navigation_dir="99-导航",
        runtime_root=tmp_path / ".runtime" / "bilibili-learning",
        cookie_file=tmp_path / "not-a-real-cookie",
        ytdlp=ExecutableResolution(None, "test", ("test",)),
        local_config_path=tmp_path / "config" / "local.json",
    )


def make_note(settings: Settings, filename: str, bvid: str = "BV1TEST012345") -> Path:
    path = settings.notes_root / "00-待整理" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'---\nsource: "https://www.bilibili.com/video/{bvid}/"\n'
        f'tags:\n  - "MiniMax-H3"\n---\n\n# 完整原标题\n\n'
        "> [!summary] 结论\n> 保留。\n\n## 重要参数\n\n**测试** | A/B\n",
        encoding="utf-8",
    )
    return path


def make_plan(settings: Settings, items: list[tuple[Path, str]]) -> Path:
    root = settings.notes_root.resolve()
    plan = settings.runtime_root / "organize-plans" / "plan.json"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(
        json.dumps({
            "schema_version": 1,
            "notes": [
                {"source": path.relative_to(root).as_posix(), "destination": dest, "sha256": note_sha256(path)}
                for path, dest in items
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    return plan


def duplicate_plan(settings: Settings, keep: Path, discard: Path, bvid: str) -> Path:
    root = settings.notes_root.resolve()
    path = settings.runtime_root / "organize-plans" / "duplicate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    def entry(note: Path) -> dict[str, str]:
        return {"path": note.relative_to(root).as_posix(), "sha256": note_sha256(note)}
    path.write_text(json.dumps({
        "schema_version": 1, "bvid": bvid, "keep": entry(keep), "recycle": [entry(discard)],
    }, ensure_ascii=False), encoding="utf-8")
    return path


def test_list_inbox_only_lists_and_never_modifies_notes(settings: Settings) -> None:
    a = make_note(settings, "标题.md")
    original = a.read_bytes()
    result = list_inbox(settings, "all")
    assert result["note_count"] == 1
    assert result["notes"][0]["source"] == "00-待整理/标题.md"
    assert result["notes"][0]["sha256"] == note_sha256(a)
    assert a.read_bytes() == original
    assert not (settings.notes_root / "99-导航").exists()


def test_single_default_preserves_filename_and_exact_bytes(settings: Settings) -> None:
    a = make_note(settings, "原标题（3）.md")
    before = note_sha256(a)
    target = organize_note(settings, a, destination="01-视频/MiniMax-H3", confirmed_scope="single")
    assert target.name == a.name
    assert note_sha256(target) == before
    assert not a.exists()
    assert (settings.notes_root / "99-导航" / "首页.md").is_file()


def test_single_default_collision_must_not_add_suffix(settings: Settings) -> None:
    a = make_note(settings, "相同标题.md")
    target = settings.notes_root / "01-视频" / "MiniMax-H3" / a.name
    target.parent.mkdir(parents=True)
    target.write_text("其他人的笔记", encoding="utf-8")
    with pytest.raises(FileExistsError, match="不能覆盖"):
        organize_note(settings, a, destination="01-视频/MiniMax-H3", confirmed_scope="single")
    assert a.exists() and target.read_text(encoding="utf-8") == "其他人的笔记"


def test_batch_preview_never_moves_or_writes_checkpoint(settings: Settings) -> None:
    a = make_note(settings, "视频A.md")
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3")])
    out = organize_batch(settings, plan, confirmed_scope="single")
    assert out["status"] == "preview"
    assert out["results"][0]["status"] == "ready"
    assert a.exists()
    assert not (settings.runtime_root / "organize-batches").exists()



def test_all_requires_complete_initial_inbox_snapshot(settings: Settings) -> None:
    a = make_note(settings, "已列计划.md", "BV1TEST012345")
    b = make_note(settings, "未列计划.md", "BV2TEST012345")
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3")])
    with pytest.raises(ValueError, match="计划不完整"):
        organize_batch(settings, plan, confirmed_scope="all", apply=True)
    assert a.exists() and b.exists()


def test_batch_two_distinct_notes_and_idempotent_resume(settings: Settings) -> None:
    a = make_note(settings, "视频A.md", "BV1TEST012345")
    b = make_note(settings, "视频B.md", "BV2TEST012345")
    checksums = {a.name: note_sha256(a), b.name: note_sha256(b)}
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3"), (b, "01-视频/MiniMax-H3")])
    result = organize_batch(settings, plan, confirmed_scope="all", apply=True)
    assert result["status"] == "organized_batch"
    assert [x["status"] for x in result["results"]] == ["organized", "organized"]
    for name in checksums:
        dest = settings.notes_root / "01-视频" / "MiniMax-H3" / name
        assert dest.is_file() and note_sha256(dest) == checksums[name]
    repeated = organize_batch(settings, plan, confirmed_scope="all", apply=True)
    assert repeated["status"] == "organized_batch"
    assert all(x["status"] == "already_organized" for x in repeated["results"])


def test_batch_source_changed_is_safely_blocked(settings: Settings) -> None:
    a = make_note(settings, "改动检测.md")
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3")])
    a.write_text(a.read_text(encoding="utf-8") + "用户新修改\n", encoding="utf-8")
    result = organize_batch(settings, plan, confirmed_scope="single", apply=True)
    assert result["status"] == "partial"
    assert result["results"][0]["reason"] == "source_changed"
    assert a.exists()


def test_batch_broken_explicit_wikilink_blocks_move(settings: Settings) -> None:
    a = make_note(settings, "被引用.md")
    ref = settings.notes_root / "01-视频" / "索引.md"
    ref.parent.mkdir(parents=True)
    ref.write_text("请看 [[00-待整理/被引用]] 的具体参数", encoding="utf-8")
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3")])
    result = organize_batch(settings, plan, confirmed_scope="single")
    assert result["results"][0]["reason"] == "possible_broken_backlinks"
    assert a.exists()


def test_batch_unique_basename_link_remains_valid(settings: Settings) -> None:
    a = make_note(settings, "同名可解析.md")
    ref = settings.notes_root / "01-视频" / "索引.md"
    ref.parent.mkdir(parents=True)
    ref.write_text("请看 [[同名可解析]]", encoding="utf-8")
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3")])
    assert organize_batch(settings, plan, confirmed_scope="single")["results"][0]["status"] == "ready"


def test_batch_duplicate_bvid_waits_for_explicit_cleanup(settings: Settings) -> None:
    a = make_note(settings, "版本1.md")
    other = make_note(settings, "版本2.md")
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3")])
    result = organize_batch(settings, plan, confirmed_scope="single", apply=True)
    assert result["results"][0]["reason"] == "duplicate_bvid_requires_review"
    assert a.exists() and other.exists()


def test_batch_resume_after_link_and_unlink_crash(settings: Settings) -> None:
    a = make_note(settings, "恢复测试.md")
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3")])
    preview = organize_batch(settings, plan, confirmed_scope="single")
    state = settings.runtime_root / "organize-batches" / (preview["plan_id"] + ".json")
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({
        "schema_version": 1,
        "identifier": preview["plan_id"],
        "items": {"00-待整理/恢复测试.md": "started"},
    }), encoding="utf-8")
    dst = settings.notes_root / "01-视频" / "MiniMax-H3" / a.name
    dst.parent.mkdir(parents=True)
    os.link(a, dst)
    a.unlink()
    resumed = organize_batch(settings, plan, confirmed_scope="single", apply=True)
    assert resumed["status"] == "organized_batch"
    assert resumed["results"][0]["status"] == "already_organized"
    assert dst.is_file()


def test_batch_resume_after_hardlink_only_crash(settings: Settings) -> None:
    a = make_note(settings, "双路径恢复.md")
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3")])
    preview = organize_batch(settings, plan, confirmed_scope="single")
    state = settings.runtime_root / "organize-batches" / (preview["plan_id"] + ".json")
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({
        "schema_version": 1,
        "identifier": preview["plan_id"],
        "items": {"00-待整理/双路径恢复.md": "started"},
    }), encoding="utf-8")
    dst = settings.notes_root / "01-视频" / "MiniMax-H3" / a.name
    dst.parent.mkdir(parents=True)
    os.link(a, dst)
    resumed = organize_batch(settings, plan, confirmed_scope="single", apply=True)
    assert resumed["results"][0]["status"] == "recovered"
    assert not a.exists()
    assert dst.is_file()


def test_batch_rejects_escape_and_duplicated_target(settings: Settings) -> None:
    a = make_note(settings, "攻击.md")
    plan = make_plan(settings, [(a, "01-视频/MiniMax-H3")])
    data = json.loads(plan.read_text(encoding="utf-8"))
    data["notes"][0]["destination"] = "../outside"
    plan.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="不安全"):
        organize_batch(settings, plan, confirmed_scope="single")
    assert a.exists()



def test_duplicate_cleanup_never_operates_on_resource_collection(settings: Settings) -> None:
    keep = make_note(settings, "必须保留.md")
    collection = settings.notes_root / "05-资源" / "模型与LoRA.md"
    collection.parent.mkdir(parents=True)
    collection.write_text(
        "# 资源集合\n\n<!-- BILI_RESOURCE_COLLECTION -->\n\n"
        "https://www.bilibili.com/video/BV1TEST012345/\n",
        encoding="utf-8",
    )
    plan = duplicate_plan(settings, keep, collection, "BV1TEST012345")
    with pytest.raises(ValueError, match="资源集合页"):
        recycle_duplicates(settings, plan, apply=True)
    assert collection.exists() and keep.exists()


def test_duplicate_inventory_preview_never_delete(settings: Settings) -> None:
    keep = make_note(settings, "原版.md")
    other = make_note(settings, "新版.md")
    report = duplicates_inventory(settings, "BV1TEST012345")
    assert report["note_count"] == 2
    plan = duplicate_plan(settings, keep, other, "BV1TEST012345")
    preview = recycle_duplicates(settings, plan)
    assert preview["status"] == "duplicates_preview"
    assert keep.exists() and other.exists()


def test_duplicate_cleanup_requires_exact_selection_and_is_resumable(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    keep = make_note(settings, "保留（6）.md")
    other = make_note(settings, "弃用（5）.md")
    plan = duplicate_plan(settings, keep, other, "BV1TEST012345")
    recycled: list[Path] = []

    def fake_recycle(path: Path) -> None:
        to = tmp_path / f"recycle-{len(recycled)}.md"
        path.rename(to)
        recycled.append(to)

    monkeypatch.setattr("bili_learning.organization_duplicates.recycle_file", fake_recycle)
    result = recycle_duplicates(settings, plan, apply=True)
    assert result["status"] == "duplicates_recycled"
    assert result["results"][0]["status"] == "recycled"
    assert keep.exists() and not other.exists() and len(recycled) == 1
    repeat = recycle_duplicates(settings, plan, apply=True)
    assert repeat["status"] == "duplicates_recycled"
    assert repeat["results"][0]["status"] == "already_recycled"
    assert len(recycled) == 1


def test_duplicate_cleanup_detects_changed_keep(settings: Settings) -> None:
    keep = make_note(settings, "保护版本.md")
    other = make_note(settings, "待清理版.md")
    plan = duplicate_plan(settings, keep, other, "BV1TEST012345")
    keep.write_text(keep.read_text(encoding="utf-8") + "\n新内容", encoding="utf-8")
    with pytest.raises(ValueError, match="保留版本"):
        recycle_duplicates(settings, plan, apply=True)
    assert other.exists()


def test_duplicate_cleanup_recycle_failure_never_unlinks(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    keep = make_note(settings, "确认保留.md")
    other = make_note(settings, "确认删除.md")
    plan = duplicate_plan(settings, keep, other, "BV1TEST012345")

    def fail(_path: Path) -> None:
        raise OSError("recycle unavailable")

    monkeypatch.setattr("bili_learning.organization_duplicates.recycle_file", fail)
    result = recycle_duplicates(settings, plan, apply=True)
    assert result["status"] == "partial"
    assert other.exists() and keep.exists()


def test_resource_compression_failed_recycle_restores_original_collection(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    note = make_note(settings, "资源介绍.md")
    card = settings.runtime_root / "resource-cards" / "card.md"
    card.parent.mkdir(parents=True)
    card.write_text("## 工具\n\n- 功能：介绍。\n", encoding="utf-8")

    def fail(_path: Path) -> None:
        raise OSError("no recycle")

    monkeypatch.setattr("bili_learning.organizer.recycle_file", fail)
    with pytest.raises(OSError, match="no recycle"):
        organize_resource_note(settings, note, "网站与灵感", card_path=card, confirmed_scope="single")
    assert note.exists()
    assert not (settings.notes_root / "05-资源" / "网站与灵感.md").exists()





def test_duplicate_crash_after_recycle_intent_requires_manual_review(
    settings: Settings, tmp_path: Path
) -> None:
    keep = make_note(settings, "保留.md")
    other = make_note(settings, "待回收.md")
    plan = duplicate_plan(settings, keep, other, "BV1TEST012345")
    from hashlib import sha256

    plan_data = json.loads(plan.read_text(encoding="utf-8"))
    identity = sha256(json.dumps(plan_data, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    checkpoint = settings.runtime_root / "organize-duplicate-runs" / (identity + ".json")
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text(json.dumps({
        "schema_version": 1,
        "identifier": identity,
        "items": {"00-待整理/待回收.md": "started"},
    }), encoding="utf-8")
    other.rename(tmp_path / "moved-by-external-process.md")
    resumed = recycle_duplicates(settings, plan, apply=True)
    assert resumed["status"] == "partial"
    assert resumed["results"][0]["reason"] == "recycle_outcome_unknown_check_recycle_bin"
    assert keep.exists()


def test_latest_batch_can_resume_after_it_was_moved(settings: Settings) -> None:
    note = make_note(settings, "最近一篇.md")
    plan = make_plan(settings, [(note, "01-视频/MiniMax-H3")])
    result = organize_batch(settings, plan, confirmed_scope="latest", apply=True)
    assert result["status"] == "organized_batch"
    assert organize_batch(settings, plan, confirmed_scope="latest", apply=True)["status"] == "organized_batch"


def test_list_single_requires_explicit_note(settings: Settings) -> None:
    note = make_note(settings, "单篇.md")
    with pytest.raises(ValueError, match="必须"):
        list_inbox(settings, "single")
    result = list_inbox(settings, "single", note=note)
    assert result["note_count"] == 1
    assert result["notes"][0]["source"] == "00-待整理/单篇.md"


def test_navigation_failure_does_not_misreport_as_unmoved(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    note = make_note(settings, "导航异常.md")
    checksum = note_sha256(note)

    def fail_nav(_settings: Settings) -> None:
        raise OSError("test nav error")

    monkeypatch.setattr("bili_learning.organizer.build_navigation", fail_nav)
    with pytest.raises(OrganizerNavigationPending) as caught:
        organize_note(settings, note, destination="01-视频/MiniMax-H3", confirmed_scope="single")
    assert note_sha256(caught.value.target) == checksum
    assert not note.exists()
