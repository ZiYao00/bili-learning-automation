from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

import bili_learning.navigation as navigation
from bili_learning.collector import (
    STALE_SECONDS,
    cleanup_stale_jobs,
    create_job,
    description_state,
    run_ytdlp,
    select_subtitle,
    write_handoff,
)
from bili_learning.config import (
    ConfigurationError,
    ExecutableResolution,
    Settings,
    configure_cookie_file,
    configure_obsidian,
    configure_ytdlp_path,
    find_ytdlp,
    load_settings,
    validate_taxonomy,
)
from bili_learning.doctor import doctor_report, onboarding_report
from bili_learning.frontmatter import parse_frontmatter, parse_frontmatter_list
from bili_learning.input_resolver import extract_user_supplied_source, resolve_input
from bili_learning.lifecycle import finalize_note, prepare_description_note, prepare_note, prepare_transcript_note
from bili_learning.note_library import find_notes_by_bvid
from bili_learning.note_template import (
    metadata_line,
    note_filename,
    quote_description,
    render_note_skeleton,
    render_video_materials,
)
from bili_learning.organizer import find_duplicate_bvid_notes, organize_note, organize_resource_note
from bili_learning.publisher import publish_validated_draft
from bili_learning.resource_access import detect_resource_access_notices
from bili_learning.runtime import (
    ReservationBusyError,
    bind_reservation,
    claim_reservation,
    cleanup_job,
    file_lock,
    safe_job_path,
)
from bili_learning.source import SOURCE_MODE_ASR, SOURCE_MODE_DESCRIPTION, SOURCE_MODE_SUBTITLE, SourceMaterial
from bili_learning.taxonomy import classify
from bili_learning.transcript import prepare_agent_source, prepare_agent_text_transcript, prepare_agent_transcript
from bili_learning.validator import validate_note
from bili_learning.workflow import validate_agent_workflow, write_agent_work_templates


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
                "path": ["01-视频", "MiniMax-H3"],
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


def test_extract_user_supplied_source_requires_an_explicit_label() -> None:
    message = (
        "转换该视频：\nhttps://www.bilibili.com/video/BV1TXua68EYi/\n\n"
        "下面内容是up主的附加内容：\n工作流：https://pan.quark.cn/s/example"
    )
    source = extract_user_supplied_source(message)
    assert source is not None
    assert "up主" in source["label"].lower()
    assert source["text"] == "工作流：https://pan.quark.cn/s/example"
    assert extract_user_supplied_source("转换该视频：https://www.bilibili.com/video/BV1TXua68EYi/") is None


def test_reject_non_bilibili_url_without_bvid() -> None:
    with pytest.raises(ValueError):
        resolve_input("https://example.com/video/123")


def test_taxonomy_classification(taxonomy: dict) -> None:
    filing = classify({"title": "H3 分段工作流", "description": "", "tags": []}, taxonomy)
    assert filing["suggested_title"] == "分段生成"
    assert filing["category_path"] == ["00-待整理"]
    assert filing["suggested_category_path"] == ["01-视频", "MiniMax-H3"]
    assert filing["suggested_route_id"] == "h3_segment"


def test_note_filename_uses_a_clean_title_and_collision_sequence() -> None:
    assert note_filename("MiniMax-H3 分段生成") == "MiniMax-H3 分段生成.md"
    assert note_filename("MiniMax-H3 分段生成", 2) == "MiniMax-H3 分段生成（2）.md"


def test_taxonomy_uses_a_specific_topic_title_in_the_inbox(taxonomy: dict) -> None:
    taxonomy["routes"].insert(
        0,
        {
            "id": "h3_grid",
            "path": ["01-视频", "MiniMax-H3"],
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
            "path": ["01-视频", "MiniMax-H3"],
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


def test_prepare_agent_transcript_chunks_long_srt_without_losing_order(tmp_path: Path) -> None:
    subtitle = tmp_path / "long.ai-zh.srt"
    blocks = []
    for index in range(1, 7):
        blocks.append(
            f"{index}\n00:00:{index:02d},000 --> 00:00:{index:02d},900\n知识点{index}-" + ("参数与限制" * 12)
        )
    subtitle.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    work = tmp_path / "agent-work"

    result = prepare_agent_transcript(subtitle, work, direct_max_chars=80, chunk_target_chars=180)

    assert result["source_mode"] == SOURCE_MODE_SUBTITLE
    assert result["package_mode"] == "chunked"
    assert result["chunk_count"] > 1
    assert sum(chunk["segment_count"] for chunk in result["chunks"]) == 6
    combined = "".join(Path(chunk["path"]).read_text(encoding="utf-8") for chunk in result["chunks"])
    positions = [combined.index(f"知识点{index}-") for index in range(1, 7)]
    assert positions == sorted(positions)
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["rules"]["semantic_summary"] is False
    assert manifest["rules"]["text_order_preserved"] is True
    assert manifest["rules"]["cue_boundaries_preserved"] is True
    assert manifest["timestamps_available"] is True


def test_prepare_agent_transcript_merges_a_tiny_tail_chunk(tmp_path: Path) -> None:
    subtitle = tmp_path / "tail.ai-zh.srt"
    blocks = [
        "1\n00:00:01,000 --> 00:00:02,000\n" + ("甲" * 22_980),
        "2\n00:00:02,000 --> 00:00:03,000\n" + ("乙" * 22_980),
        "3\n00:00:03,000 --> 00:00:04,000\n尾巴",
    ]
    subtitle.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")

    result = prepare_agent_transcript(subtitle, tmp_path / "agent-work")

    assert result["package_mode"] == "chunked"
    assert result["chunk_count"] == 2
    assert sum(chunk["segment_count"] for chunk in result["chunks"]) == 3
    combined = "".join(Path(chunk["path"]).read_text(encoding="utf-8") for chunk in result["chunks"])
    assert "尾巴" in combined


def test_prepare_agent_text_transcript_chunks_long_plain_text_without_fake_timestamps(tmp_path: Path) -> None:
    transcript = tmp_path / "asr.txt"
    transcript.write_text(("第一句。" * 7000) + "最后一句。", encoding="utf-8")

    result = prepare_agent_text_transcript(transcript, tmp_path / "agent-work")

    assert result["source_mode"] == SOURCE_MODE_ASR
    assert result["timestamps_available"] is False
    assert result["chunk_count"] > 1
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["rules"]["timestamps_fabricated"] is False
    combined = "".join(Path(chunk["path"]).read_text(encoding="utf-8") for chunk in result["chunks"])
    assert "最后一句。" in combined
    assert "[00:00:00]" not in combined


def test_prepare_agent_description_source_has_no_fake_transcript_chunks(tmp_path: Path) -> None:
    result = prepare_agent_source(
        SourceMaterial(SOURCE_MODE_DESCRIPTION),
        "纯资源分享简介",
        tmp_path / "agent-work",
    )

    assert result["source_mode"] == SOURCE_MODE_DESCRIPTION
    assert result["source_location"] == "job.description"
    assert result["package_mode"] == "none"
    assert result["chunk_count"] == 0
    assert result["chunks"] == []
    assert result["timestamps_available"] is False
    assert Path(result["manifest_path"]).is_file()


def test_agent_handoff_routes_strict_workflow_through_source_manifest(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    handoff = write_handoff(job_dir, {})
    text = handoff.read_text(encoding="utf-8")

    assert "source_manifest_path" in text
    assert "fact_ledger_path" in text
    assert "semantic_draft_path" in text
    assert "layout_plan_path" in text
    assert "Fact Ledger" in text
    assert "Semantic Draft" in text
    assert "Layout Plan" in text
    assert "当前 Job 允许的来源" in text
    assert "finalizer" in text


def test_agent_handoff_light_mode_is_short_and_source_aware(tmp_path: Path) -> None:
    job_dir = tmp_path / "light-job"
    job_dir.mkdir()
    handoff = write_handoff(job_dir, {"workflow_mode": "light"})
    text = handoff.read_text(encoding="utf-8")

    assert "LIGHT-WORKFLOW.md" in text
    assert "source_manifest_path" in text
    assert "直接在 `draft_path`" in text
    assert "内容完成后" in text
    assert "description_only" in text
    assert "Fact Ledger、Semantic Draft 或 Layout Plan" in text
    assert "fact_ledger_path" not in text
    assert "workflow_status" not in text


def test_light_workflow_defines_semantic_quality_without_length_target() -> None:
    workflow = Path("docs/standards/LIGHT-WORKFLOW.md").read_text(encoding="utf-8")

    assert "不要预设章节数量、文章字数、KB 大小或压缩比" in workflow
    assert "关系、选择条件、原因、实测证据、失败表现和作者判断" in workflow
    assert "不得根据模型记忆静默修正为某个看起来合理的正式名称" in workflow
    assert "应显式保留冲突" in workflow
    assert "不要在正文末尾追加“来源提供的资源”" in workflow


def test_public_docs_keep_model_choice_neutral() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    development = Path("docs/DEVELOPMENT.md").read_text(encoding="utf-8")

    assert "本项目**不绑定特定 LLM**" in readme
    assert "README 不维护固定模型排名" in readme
    assert "项目不指定默认或必选 LLM" in development
    assert "当前真实回归测试的默认基准是" not in readme
    assert "当前默认基准为" not in development


def test_description_renders_compact_resources_and_preserves_raw_source() -> None:
    description = "节点升级说明\n工作流地址：\nhttps://example.com/workflow\n仓库：https://example.com/repo"
    rendered = quote_description(description, "present")
    assert "## 视频资料" not in rendered
    assert '<p class="video-note-overview"><strong>视频简介</strong>：节点升级说明</p>' in rendered
    assert "### UP 主资源" in rendered
    assert "- [工作流地址](<https://example.com/workflow>)" in rendered
    assert "- [仓库](<https://example.com/repo>)" in rendered
    assert '<details class="video-note-source-details">' in rendered
    assert "<summary>UP 主原文（完整说明与链接）</summary>" in rendered
    assert description in rendered


def test_description_resource_labels_include_section_type_and_platform() -> None:
    description = (
        "涉及插件：\n"
        "MieNodes: https://github.com/MieMieeeee/ComfyUI-MieNodes\n"
        "资料：\n"
        "MiniMax H3 模型提示词指令：https://example.feishu.cn/wiki/prompt\n"
        "工作流：https://pan.quark.cn/s/workflow"
    )
    rendered = quote_description(description, "present")
    assert "- [GitHub 插件 · MieNodes](<https://github.com/MieMieeeee/ComfyUI-MieNodes>)" in rendered
    assert "- [MiniMax H3 模型提示词指令（飞书）](<https://example.feishu.cn/wiki/prompt>)" in rendered
    assert "- [工作流（夸克网盘）](<https://pan.quark.cn/s/workflow>)" in rendered
    assert description in rendered


def test_video_materials_filter_separator_context_deduplicate_and_normalize_entities() -> None:
    description = (
        "AITUDOU官网：https://aitudou.cn\n"
        "--------------在线工作流区域--------------\n"
        "国际站：\n"
        "工作流：AITUDOU-MiniMax H3(全能参考)\n"
        "体验地址：https://example.com/demo\n"
        "国内站：\n"
        "体验地址：https://example.cn/demo\n"
        "夸克网盘：https://pan.quark.cn/s/demo\n"
        "备用下载：https://pan.quark.cn/s/demo\n"
        "本地工作流&amp;模型&amp;提示词模板"
    )
    rendered = render_video_materials(
        {
            "bvid": "BV1EXAMPLE",
            "description": description,
            "description_status": "present",
            "resource_access_notices": [],
        }
    )
    compact = rendered.split("<details", 1)[0]
    assert "video-note-overview" not in compact
    assert "在线工作流区域" not in compact
    assert "- [国际站 · 体验地址](<https://example.com/demo>)" in rendered
    assert "- [国内站 · 体验地址](<https://example.cn/demo>)" in rendered
    assert "夸克网盘（夸克网盘）" not in rendered
    compact_resources = rendered.split('<details class="video-note-source-details">', 1)[0]
    assert compact_resources.count("https://pan.quark.cn/s/demo") == 1
    assert "&amp;amp;" not in rendered
    assert "本地工作流&amp;模型&amp;提示词模板" in rendered


def test_resource_label_does_not_append_quark_platform_twice() -> None:
    rendered = quote_description("模型库（夸克）：https://pan.quark.cn/s/models", "present")
    assert "- [模型库（夸克）](<https://pan.quark.cn/s/models>)" in rendered
    assert "模型库（夸克）（夸克网盘）" not in rendered


def test_video_materials_keep_real_overview_before_resource_section() -> None:
    rendered = render_video_materials(
        {
            "bvid": "BV1EXAMPLE",
            "description": "视频简介：\n这是一个新的工作流教程\n工作流：https://example.com/workflow",
            "description_status": "present",
            "resource_access_notices": [],
        }
    )
    assert '<p class="video-note-overview"><strong>视频简介</strong>：这是一个新的工作流教程</p>' in rendered


def test_video_materials_omit_empty_overview_but_keep_player_and_resources() -> None:
    rendered = render_video_materials(
        {
            "bvid": "BV1EXAMPLE",
            "description": "工作流：https://example.com/workflow",
            "description_status": "present",
            "resource_access_notices": [],
        }
    )
    assert "### 原视频" not in rendered
    assert "player.bilibili.com/player.html?bvid=BV1EXAMPLE" in rendered
    assert "### UP 主资源" in rendered
    assert "video-note-overview" not in rendered


def test_video_materials_keep_user_supplied_source_separate_from_bilibili_description() -> None:
    rendered = render_video_materials(
        {
            "bvid": "BV1EXAMPLE",
            "description": "平台采集到的简介",
            "description_status": "present",
            "resource_access_notices": [],
            "user_supplied_source": {
                "label": "下面内容是up主的附加内容",
                "text": "工作流：https://pan.quark.cn/s/example",
            },
        }
    )
    assert "平台采集到的简介" in rendered
    assert "### 用户补充资源" in rendered
    assert "https://pan.quark.cn/s/example" in rendered
    assert "未与 B站简介合并" in rendered
    assert "下面内容是up主的附加内容" in rendered


def test_resource_access_detects_explicit_conditions_without_inventing_materials(tmp_path: Path) -> None:
    subtitle = tmp_path / "resource.ai-zh.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n这个提示词模板三连后我会发给大家\n\n"
        "2\n00:00:03,000 --> 00:00:04,000\n充电用户可以领取完整工作流\n\n"
        "3\n00:00:05,000 --> 00:00:06,000\n评论区回复H3领取资料\n",
        encoding="utf-8",
    )
    notices = detect_resource_access_notices("", SourceMaterial(SOURCE_MODE_SUBTITLE, subtitle))
    conditions = {notice["condition"] for notice in notices}
    assert "三连" in conditions
    assert "充电" in conditions
    assert "评论/关键词" in conditions
    assert all(notice["source"] == "subtitle" for notice in notices)


def test_resource_access_preserves_asr_provenance(tmp_path: Path) -> None:
    transcript = tmp_path / "asr.txt"
    transcript.write_text("三连后领取工作流。", encoding="utf-8")

    notices = detect_resource_access_notices("", SourceMaterial(SOURCE_MODE_ASR, transcript))

    assert notices and notices[0]["source"] == "asr"
    rendered = render_video_materials(
        {
            "bvid": "BV1EXAMPLE",
            "description": "",
            "description_status": "confirmed_empty",
            "resource_access_notices": notices,
        }
    )
    assert "来源：ASR 转写" in rendered


def test_resource_access_description_only_uses_description_provenance() -> None:
    notices = detect_resource_access_notices(
        "三连后领取工作流",
        SourceMaterial(SOURCE_MODE_DESCRIPTION),
    )

    assert notices and all(notice["source"] == "description" for notice in notices)


def test_resource_access_prefers_description_and_deduplicates_matching_subtitle(tmp_path: Path) -> None:
    subtitle = tmp_path / "duplicate.ai-zh.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n三连后领取提示词模板\n",
        encoding="utf-8",
    )
    notices = detect_resource_access_notices(
        "三连后领取提示词模板",
        SourceMaterial(SOURCE_MODE_SUBTITLE, subtitle),
    )
    matching = [notice for notice in notices if notice["resource"] == "提示词模板"]
    assert len(matching) == 1
    assert matching[0]["source"] == "description"


def test_resource_access_does_not_join_generic_engagement_with_unrelated_template(tmp_path: Path) -> None:
    subtitle = tmp_path / "generic.ai-zh.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n大家喜欢的话记得一键三连\n\n"
        "2\n00:00:10,000 --> 00:00:11,000\n下面讲一下提示词模板的结构\n\n"
        "3\n00:00:20,000 --> 00:00:21,000\n关注我们，这个工作流可以直接下载\n",
        encoding="utf-8",
    )
    assert detect_resource_access_notices("", SourceMaterial(SOURCE_MODE_SUBTITLE, subtitle)) == []


def test_note_skeleton_places_materials_before_knowledge_body() -> None:
    job = {
        "author": "示例UP主",
        "published": "2026-08-22",
        "duration": "11:36",
        "canonical_url": "https://www.bilibili.com/video/BV1EXAMPLE/",
        "required_tags": ["视频生成"],
        "canonical_title": "示例视频标题",
        "bvid": "BV1EXAMPLE",
        "description": "教程说明",
        "description_status": "present",
        "resource_access_notices": [],
    }
    rendered = render_note_skeleton(job)
    assert metadata_line(job) in rendered
    summary_at = rendered.index("[!summary] 先看结论")
    body_at = rendered.index("BILI_AI_BODY_START")
    player_at = rendered.index("player.bilibili.com")
    assert summary_at < player_at < body_at


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


def test_vault_root_and_notes_subdir_override_taxonomy_fallback(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (config_dir / "local.json").write_text(
        json.dumps({"vault_root": str(vault), "notes_subdir": "03-Resources/Bilibili"}),
        encoding="utf-8",
    )
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_VAULT_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_NOTES_SUBDIR", raising=False)

    settings = load_settings(tmp_path)

    assert settings.vault_root == vault
    assert settings.notes_subdir == Path("03-Resources/Bilibili")
    assert settings.notes_root == vault / "03-Resources" / "Bilibili"
    assert settings.notes_source == "local_vault"
    assert settings.notes_is_fallback is False


def test_taxonomy_notes_root_is_marked_as_repository_fallback(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_VAULT_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_NOTES_SUBDIR", raising=False)

    settings = load_settings(tmp_path)

    assert settings.notes_root == tmp_path / "notes" / "bilibili"
    assert settings.notes_is_fallback is True
    assert settings.notes_source == "taxonomy_fallback"


def test_legacy_notes_root_remains_supported(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    (config_dir / "local.json").write_text(json.dumps({"notes_root": "legacy/notes"}), encoding="utf-8")
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_VAULT_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_NOTES_SUBDIR", raising=False)

    settings = load_settings(tmp_path)

    assert settings.notes_root == tmp_path / "legacy" / "notes"
    assert settings.vault_root is None
    assert settings.notes_source == "local_notes_root"
    assert settings.notes_is_fallback is False


def test_notes_root_can_pair_with_vault_metadata(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (config_dir / "local.json").write_text(
        json.dumps({"notes_root": "notes/bilibili", "vault_root": str(vault), "notes_subdir": "bilibili"}),
        encoding="utf-8",
    )
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_VAULT_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_NOTES_SUBDIR", raising=False)

    settings = load_settings(tmp_path)

    assert settings.notes_root == tmp_path / "notes" / "bilibili"
    assert settings.vault_root == vault
    assert settings.notes_subdir == Path("bilibili")
    assert settings.notes_source == "local_notes_root_with_vault"
    assert settings.notes_is_fallback is False


def test_doctor_reports_hybrid_notes_mapping(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    vault = tmp_path / "vault"
    mapped_notes = vault / "bilibili"
    mapped_notes.mkdir(parents=True)
    (vault / ".obsidian").mkdir()
    (config_dir / "local.json").write_text(
        json.dumps({"notes_root": str(mapped_notes), "vault_root": str(vault), "notes_subdir": "bilibili"}),
        encoding="utf-8",
    )
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_VAULT_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_NOTES_SUBDIR", raising=False)

    report = doctor_report(load_settings(tmp_path))
    checks = {check["code"]: check for check in report["checks"]}

    assert checks["obsidian_notes_mapping"]["status"] == "OK"


def test_onboarding_blocks_invalid_hybrid_notes_mapping(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    notes_root = tmp_path / "notes" / "bilibili"
    notes_root.mkdir(parents=True)
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / "bilibili").mkdir()
    (config_dir / "local.json").write_text(
        json.dumps({"notes_root": str(notes_root), "vault_root": str(vault), "notes_subdir": "bilibili"}),
        encoding="utf-8",
    )
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_VAULT_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_NOTES_SUBDIR", raising=False)

    report = onboarding_report(load_settings(tmp_path))
    action_codes = {action["code"] for action in report["actions"]}

    assert "obsidian_notes_mapping_invalid" in action_codes


def test_load_settings_accepts_utf8_bom_in_local_config(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    (config_dir / "local.json").write_text(json.dumps({"notes_root": "notes/bilibili"}), encoding="utf-8-sig")
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)

    settings = load_settings(tmp_path)

    assert settings.notes_root == tmp_path / "notes" / "bilibili"


def test_workflow_mode_defaults_to_light(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    monkeypatch.delenv("BILI_LEARNING_WORKFLOW_MODE", raising=False)

    settings = load_settings(tmp_path)

    assert settings.workflow_mode == "light"


def test_workflow_mode_local_and_environment_override(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    (config_dir / "local.json").write_text(json.dumps({"workflow_mode": "strict"}), encoding="utf-8")
    monkeypatch.delenv("BILI_LEARNING_WORKFLOW_MODE", raising=False)

    assert load_settings(tmp_path).workflow_mode == "strict"

    monkeypatch.setenv("BILI_LEARNING_WORKFLOW_MODE", "light")
    assert load_settings(tmp_path).workflow_mode == "light"


def test_workflow_mode_rejects_invalid_value(tmp_path: Path, taxonomy: dict) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    (config_dir / "local.json").write_text(json.dumps({"workflow_mode": "auto"}), encoding="utf-8")

    with pytest.raises(ConfigurationError) as error:
        load_settings(tmp_path)
    assert error.value.code == "workflow_mode_invalid"


def test_configure_obsidian_preserves_other_local_values(tmp_path: Path, taxonomy: dict) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    (config_dir / "local.json").write_text(
        json.dumps(
            {
                "ytdlp": "tools/yt-dlp.exe",
                "notes_root": "old/notes",
                "workflow_mode": "strict",
                "siliconflow": {"api_key": "local-only-test-key"},
            }
        ),
        encoding="utf-8",
    )
    vault = tmp_path / "MyVault"
    (vault / ".obsidian").mkdir(parents=True)

    path = configure_obsidian(tmp_path, vault, "Resources/Bilibili")
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved["ytdlp"] == "tools/yt-dlp.exe"
    assert saved["workflow_mode"] == "strict"
    assert saved["siliconflow"] == {"api_key": "local-only-test-key"}
    assert saved["notes_root"] == "old/notes"
    assert saved["vault_root"] == str(vault.resolve())
    assert saved["notes_subdir"] == str(Path("Resources/Bilibili"))


def test_onboarding_reports_required_actions(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    monkeypatch.delenv("BILI_LEARNING_NOTES_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_VAULT_ROOT", raising=False)
    monkeypatch.delenv("BILI_LEARNING_NOTES_SUBDIR", raising=False)
    monkeypatch.delenv("BILI_LEARNING_COOKIE_FILE", raising=False)
    monkeypatch.delenv("BILI_LEARNING_YTDLP", raising=False)

    report = onboarding_report(load_settings(tmp_path))
    action_codes = {action["code"] for action in report["actions"]}

    assert report["status"] == "action_required"
    assert "obsidian_vault_required" in action_codes
    assert "ytdlp_required" in action_codes
    assert "cookie_file_required" in action_codes


def test_onboarding_css_warning_does_not_block_ready_state(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    cookie = tmp_path / "cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    ytdlp = tmp_path / "yt-dlp.exe"
    ytdlp.write_text("stub", encoding="utf-8")
    (config_dir / "local.json").write_text(
        json.dumps({"vault_root": str(vault), "notes_subdir": "bilibili", "cookie_file": str(cookie), "ytdlp": str(ytdlp)}),
        encoding="utf-8",
    )
    monkeypatch.setattr("bili_learning.doctor.subprocess.run", lambda *args, **kwargs: type("Result", (), {"returncode": 0, "stdout": "2026.01.01\n", "stderr": ""})())

    report = onboarding_report(load_settings(tmp_path))

    assert report["status"] == "ready"
    assert report["actions"] == []
    assert any(warning["code"] == "obsidian_css_missing" for warning in report["warnings"])
    assert report["summary"]["obsidian"]["status"] == "ready"
    assert report["summary"]["bilibili_cookie"]["status"] == "ready"
    assert report["summary"]["css"]["status"] == "missing_optional"


def test_onboarding_ytdlp_version_timeout_stays_ready_without_user_warning(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, taxonomy)
    monkeypatch.setattr(
        "bili_learning.doctor.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(cmd="yt-dlp", timeout=10)),
    )

    report = onboarding_report(settings)

    assert report["status"] == "ready"
    assert not any(warning["code"] == "ytdlp_version_check_timeout" for warning in report["warnings"])
    assert report["summary"]["yt_dlp"]["status"] == "ready"


def test_configure_cookie_and_ytdlp_preserve_existing_local_values(tmp_path: Path, taxonomy: dict) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (config_dir / "local.json").write_text(
        json.dumps({"vault_root": str(vault), "notes_subdir": "bilibili", "workflow_mode": "strict"}),
        encoding="utf-8",
    )
    cookie = tmp_path / "cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    ytdlp = tmp_path / "yt-dlp.exe"
    ytdlp.write_text("stub", encoding="utf-8")

    configure_cookie_file(tmp_path, cookie)
    configure_ytdlp_path(tmp_path, ytdlp)
    saved = json.loads((config_dir / "local.json").read_text(encoding="utf-8"))

    assert saved["vault_root"] == str(vault)
    assert saved["notes_subdir"] == "bilibili"
    assert saved["workflow_mode"] == "strict"
    assert saved["cookie_file"] == str(cookie.resolve())
    assert saved["ytdlp"] == str(ytdlp.resolve())


def _complete_ai_regions(text: str) -> str:
    return (
        text.replace("> 待智能体根据字幕填写。", "> 这是结论。")
        .replace(
            "待智能体根据字幕填写。根据视频实际内容组织知识正文；不要套固定章节。",
            "## 核心知识\n\n这是根据字幕整理的动态正文。",
        )
    )


def _write_passed_analysis(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_assessment": {"status": "sufficient", "reason": "字幕连续且足以支撑示例笔记。"},
                "knowledge_outline": ["核心知识"],
                "coverage_review": {"status": "passed", "notes": "已对照知识清单复核正文。"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _complete_agent_workflow(payload: dict[str, object]) -> None:
    fact_ledger = Path(str(payload["fact_ledger_path"]))
    fact_text = fact_ledger.read_text(encoding="utf-8")
    fact_text = fact_text.replace("workflow_status: pending", "workflow_status: complete", 1)
    fact_text = fact_text.replace(
        "| F001 |  |  |  | pending |",
        "| F001 | transcript-01 / 00:00:00 | 核心知识与关键限制。 | 来源充分，正文需保留。 | 正文已保留 |",
        1,
    )
    fact_ledger.write_text(fact_text, encoding="utf-8")

    semantic_draft = Path(str(payload["semantic_draft_path"]))
    semantic_text = semantic_draft.read_text(encoding="utf-8")
    semantic_text = semantic_text.replace("workflow_status: pending", "workflow_status: complete", 1)
    semantic_text += "\n## 核心知识\n\n这是根据字幕完成的语义内容稿，保留关键参数、限制、比较关系与使用条件。\n"
    semantic_draft.write_text(semantic_text, encoding="utf-8")

    layout_plan = Path(str(payload["layout_plan_path"]))
    layout_text = layout_plan.read_text(encoding="utf-8")
    layout_text = layout_text.replace("workflow_status: pending", "workflow_status: complete", 1)
    layout_text = layout_text.replace(
        "|  |  |  | pending |",
        "| 核心知识 | 普通标题与列表 | 没有需要强制卡片化的并列关系 | passed |",
        1,
    )
    layout_plan.write_text(layout_text, encoding="utf-8")


def test_agent_workflow_light_mode_does_not_require_stage_files() -> None:
    assert validate_agent_workflow({"workflow_mode": "light"}) == []


def test_agent_workflow_stage_gate_requires_completed_runtime_files(tmp_path: Path) -> None:
    agent_work_dir = tmp_path / "agent-work"
    paths = write_agent_work_templates(agent_work_dir)
    payload: dict[str, object] = {"workflow_mode": "strict", "agent_work_dir": str(agent_work_dir), **paths}

    pending_errors = validate_agent_workflow(payload)
    assert sum("尚未完成" in error for error in pending_errors) == 3

    _complete_agent_workflow(payload)
    assert validate_agent_workflow(payload) == []


def test_agent_workflow_allows_simple_video_to_skip_fact_ledger_with_reason(tmp_path: Path) -> None:
    agent_work_dir = tmp_path / "agent-work"
    paths = write_agent_work_templates(agent_work_dir)
    payload: dict[str, object] = {"workflow_mode": "strict", "agent_work_dir": str(agent_work_dir), **paths}
    _complete_agent_workflow(payload)

    fact_ledger = Path(str(payload["fact_ledger_path"]))
    fact_text = fact_ledger.read_text(encoding="utf-8")
    fact_text = fact_text.replace("workflow_status: complete", "workflow_status: not_applicable", 1)
    fact_text = fact_text.replace('workflow_reason: ""', 'workflow_reason: "短视频只有一个简单观点，无需独立事实账本。"', 1)
    fact_ledger.write_text(fact_text, encoding="utf-8")

    assert validate_agent_workflow(payload) == []


def test_dense_note_standard_keeps_execution_and_empirical_evidence() -> None:
    guide = (Path(__file__).parents[1] / "docs" / "standards" / "CODEX-VIDEO-NOTE-GUIDE.md").read_text(
        encoding="utf-8"
    )
    integration = (Path(__file__).parents[1] / "docs" / "AGENT-INTEGRATION.md").read_text(encoding="utf-8")

    for text in (guide, integration):
        assert "运行入口" in text
        assert "实测" in text
        assert "配置 → 耗时" in text
    assert "960×544" in guide
    assert "84 秒" in guide


def test_note_standard_prevents_fixed_section_templates() -> None:
    root = Path(__file__).parents[1]
    guide = (root / "docs" / "standards" / "CODEX-VIDEO-NOTE-GUIDE.md").read_text(encoding="utf-8")
    integration = (root / "docs" / "AGENT-INTEGRATION.md").read_text(encoding="utf-8")
    example = (root / "docs" / "standards" / "STANDARD-VIDEO-NOTE-EXAMPLE.md").read_text(encoding="utf-8")
    dense_workflow = (root / "docs" / "standards" / "KNOWLEDGE-DENSE-WORKFLOW.md").read_text(encoding="utf-8")

    assert "不存在一一对应关系" in guide
    assert "没有“目标章节数量”" in guide
    assert "自然聚类" in guide
    assert "workflow_mode" in integration
    assert "LIGHT-WORKFLOW.md" in integration
    assert "结构片段库（不是目录模板）" in example
    assert "## 01 · 核心规格" not in example
    assert "## 05 · 提示词结构" not in example
    assert "Fact Ledger" in guide
    assert "Semantic Draft" in guide
    assert "不得改变事实保留预算" in guide
    assert "Layout Pass" in guide
    assert "fact_ledger_path" in integration
    assert "semantic_draft_path" in integration
    assert "layout_plan_path" in integration
    assert "少章节不等于少知识" in example
    assert "Source Assessment" in dense_workflow
    assert "Layout Pass" in dense_workflow
    assert "第二次摘要" in dense_workflow


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
        "analysis_path": str(tmp_path / "analysis.json"),
    }
    _write_passed_analysis(Path(job["analysis_path"]))
    note.write_text(_complete_ai_regions(render_note_skeleton(job)), encoding="utf-8")
    assert validate_note(note, job) == []
    note.write_text(
        note.read_text(encoding="utf-8").replace('author: "UP"', 'author: "OTHER"'), encoding="utf-8"
    )
    assert any("author" in error for error in validate_note(note, job))


def test_validator_rejects_multiple_summary_callouts(tmp_path: Path) -> None:
    note = tmp_path / "重复总结.md"
    analysis = tmp_path / "analysis.json"
    job = {
        "schema_version": 1,
        "bvid": "BV1TXua68EYi",
        "canonical_url": "https://www.bilibili.com/video/BV1TXua68EYi/",
        "author": "UP",
        "published": "2026-08-11",
        "duration": "07:05",
        "description": "原始简介",
        "description_status": "present",
        "canonical_title": "重复总结",
        "note_filename": note.name,
        "required_tags": ["视频生成"],
        "note_path": str(note),
        "analysis_path": str(analysis),
    }
    _write_passed_analysis(analysis)
    base = _complete_ai_regions(render_note_skeleton(job))
    note.write_text(base + "\n> [!summary] 第二个总结\n> 不应出现。\n", encoding="utf-8")
    assert any("只允许一个最高优先级 Summary" in error for error in validate_note(note, job))


def test_validator_rejects_a_card_without_grid_nesting(tmp_path: Path) -> None:
    note = tmp_path / "卡片嵌套.md"
    analysis = tmp_path / "analysis.json"
    job = {
        "schema_version": 1,
        "bvid": "BV1TXua68EYi",
        "canonical_url": "https://www.bilibili.com/video/BV1TXua68EYi/",
        "author": "UP",
        "published": "2026-08-11",
        "duration": "07:05",
        "description": "原始简介",
        "description_status": "present",
        "canonical_title": "卡片嵌套",
        "note_filename": note.name,
        "required_tags": ["视频生成"],
        "note_path": str(note),
        "analysis_path": str(analysis),
    }
    _write_passed_analysis(analysis)
    base = _complete_ai_regions(render_note_skeleton(job))
    note.write_text(base + "\n> [!card] 错误\n> 单层卡片\n", encoding="utf-8")
    assert any("Card 必须嵌套" in error for error in validate_note(note, job))

    note.write_text(
        base + "\n> [!grid-2]\n>\n> > [!card] 正确\n> > 嵌套卡片\n",
        encoding="utf-8",
    )
    assert validate_note(note, job) == []

    note.write_text(base + "\n详见 fact-ledger.md。\n", encoding="utf-8")
    assert any("fact-ledger.md" in error for error in validate_note(note, job))


def test_validator_rejects_unfinished_quality_review(tmp_path: Path) -> None:
    note = tmp_path / "质量复核.md"
    analysis = tmp_path / "analysis.json"
    job = {
        "schema_version": 1,
        "bvid": "BV1TXua68EYi",
        "canonical_url": "https://www.bilibili.com/video/BV1TXua68EYi/",
        "author": "UP",
        "published": "2026-08-11",
        "duration": "07:05",
        "description": "原始简介",
        "description_status": "present",
        "canonical_title": "质量复核",
        "note_filename": note.name,
        "required_tags": ["视频生成"],
        "note_path": str(note),
        "analysis_path": str(analysis),
    }
    note.write_text(_complete_ai_regions(render_note_skeleton(job)), encoding="utf-8")
    analysis.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_assessment": {"status": "sufficient", "reason": "字幕足够。"},
                "knowledge_outline": ["核心知识"],
                "coverage_review": {"status": "pending", "notes": ""},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert any("coverage_review" in error for error in validate_note(note, job))


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
        vault_root=None,
        notes_subdir=None,
        notes_source="test",
        notes_is_fallback=False,
        navigation_dir="99-导航",
        runtime_root=runtime_root,
        cookie_file=cookie_file,
        ytdlp=ExecutableResolution(ytdlp, "test", ("test",)),
        local_config_path=tmp_path / "config" / "local.json",
    )


def test_doctor_missing_ytdlp_only_reports_install_guidance(tmp_path: Path, taxonomy: dict) -> None:
    settings = replace(_settings(tmp_path, taxonomy), ytdlp=ExecutableResolution(None, "missing", ("PATH:yt-dlp",)))

    report = doctor_report(settings)
    check = next(item for item in report["checks"] if item["code"] == "ytdlp_not_configured")

    assert check["status"] == "FAIL"
    assert check["windows_install_command"] == "winget install yt-dlp"
    assert "不会自动安装" in check["detail"]
    assert "github.com/yt-dlp/yt-dlp/wiki/Installation" in check["install_url"]


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
        SourceMaterial(SOURCE_MODE_SUBTITLE, subtitle),
        job_dir,
    )
    note_path = Path(payload["note_path"])
    draft_path = Path(payload["draft_path"])
    assert note_path.name == "H3 分段工作流.md"
    assert not note_path.exists()
    assert draft_path.parent == job_dir
    assert draft_path.name == note_path.name
    analysis_path = Path(payload["analysis_path"])
    assert analysis_path.parent == job_dir
    agent_work_dir = Path(payload["agent_work_dir"])
    assert agent_work_dir.parent == job_dir
    assert agent_work_dir.is_dir()
    assert payload["workflow_mode"] == "light"
    assert "fact_ledger_path" not in payload
    assert "semantic_draft_path" not in payload
    assert "layout_plan_path" not in payload
    assert not (agent_work_dir / "fact-ledger.md").exists()
    assert not (agent_work_dir / "semantic-draft.md").exists()
    assert not (agent_work_dir / "layout-plan.md").exists()
    manifest_path = Path(payload["source_manifest_path"])
    assert manifest_path.parent == agent_work_dir
    assert payload["source_package_mode"] == "direct"
    assert payload["transcript_chunk_count"] == 1
    assert manifest_path.is_file()
    assert json.loads(analysis_path.read_text(encoding="utf-8"))["source_assessment"]["status"] == "pending"
    draft_text = draft_path.read_text(encoding="utf-8")
    assert 'source: "https://www.bilibili.com/video/BV1TXua68EYi/"' in draft_text
    assert '<small class="video-note-meta">UP · 2026-08-11 · 07:05 · BV1TXua68EYi</small>' in draft_text
    assert parse_frontmatter_list(draft_text, "cssclasses") == ["learning-page", "video-note"]
    assert (
        draft_text.find("<!-- BILI_AI_SUMMARY_START -->")
        < draft_text.find("https://player.bilibili.com/player.html")
        < draft_text.find("<!-- BILI_AI_BODY_START -->")
    )


def test_create_job_strict_mode_writes_stage_files(tmp_path: Path, taxonomy: dict) -> None:
    settings = replace(_settings(tmp_path, taxonomy), workflow_mode="strict")
    job_dir = settings.runtime_root / "strict-job"
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
        SourceMaterial(SOURCE_MODE_SUBTITLE, subtitle),
        job_dir,
    )

    assert payload["workflow_mode"] == "strict"
    agent_work_dir = Path(payload["agent_work_dir"])
    fact_ledger_path = Path(payload["fact_ledger_path"])
    semantic_draft_path = Path(payload["semantic_draft_path"])
    layout_plan_path = Path(payload["layout_plan_path"])
    for runtime_path in (fact_ledger_path, semantic_draft_path, layout_plan_path):
        assert runtime_path.parent == agent_work_dir
        assert runtime_path.is_file()
    assert "原子事实" in fact_ledger_path.read_text(encoding="utf-8")
    assert "章节数量只决定事实如何分组" in semantic_draft_path.read_text(encoding="utf-8")
    assert "排版只转换完整内容的表达形式" in layout_plan_path.read_text(encoding="utf-8")


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
    assert parse_frontmatter_list(text, "cssclasses") == ["learning-page", "video-note"]


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
    old = time.time() - (STALE_SECONDS + 120)
    os.utime(stale_job, (old, old))
    os.utime(locks, (old, old))
    assert cleanup_stale_jobs(settings) == 1
    assert not stale_job.exists()
    assert locks.is_dir()


def test_reservation_spans_job_lifecycle_and_cleanup_releases_it(tmp_path: Path) -> None:
    runtime = tmp_path / ".runtime" / "bilibili-learning"
    reservation = claim_reservation(runtime, "BV1TXua68EYi")
    with pytest.raises(ReservationBusyError):
        claim_reservation(runtime, "BV1TXua68EYi")

    job = runtime / "BV1TXua68EYi-job"
    job.mkdir()
    agent_work = job / "agent-work"
    agent_work.mkdir()
    (agent_work / "subtitle-flat.txt").write_text("temporary", encoding="utf-8")
    (job / "job.json").write_text(json.dumps({"bvid": "BV1TXua68EYi"}), encoding="utf-8")
    bind_reservation(reservation, job)
    with pytest.raises(ReservationBusyError) as busy:
        claim_reservation(runtime, "BV1TXua68EYi")
    assert busy.value.job_dir == str(job)
    cleanup_job(runtime, job)
    assert not job.exists()
    assert claim_reservation(runtime, "BV1TXua68EYi").path.is_file()


def test_reservation_claim_is_atomic_across_concurrent_callers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import bili_learning.runtime as runtime_module

    runtime = tmp_path / ".runtime" / "bilibili-learning"
    barrier = threading.Barrier(2)
    original_write = runtime_module._write_json_atomic

    def delayed_write(path: Path, payload: dict[str, object]) -> None:
        time.sleep(0.05)
        original_write(path, payload)

    monkeypatch.setattr(runtime_module, "_write_json_atomic", delayed_write)

    def attempt_claim() -> str:
        barrier.wait()
        try:
            claim_reservation(runtime, "BV1TXua68EYi")
        except ReservationBusyError:
            return "busy"
        return "claimed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: attempt_claim(), range(2)))

    assert sorted(results) == ["busy", "claimed"]


def test_reservation_default_stale_window_is_two_hours(tmp_path: Path) -> None:
    runtime = tmp_path / ".runtime" / "bilibili-learning"
    reservation = claim_reservation(runtime, "BV1TXua68EYi")
    payload = json.loads(reservation.path.read_text(encoding="utf-8"))

    payload["updated_at"] = time.time() - 3700
    reservation.path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ReservationBusyError):
        claim_reservation(runtime, "BV1TXua68EYi")

    payload["updated_at"] = time.time() - 7300
    reservation.path.write_text(json.dumps(payload), encoding="utf-8")
    replacement = claim_reservation(runtime, "BV1TXua68EYi")
    assert replacement.path.is_file()


def test_claim_reservation_reclaims_missing_bound_job_without_waiting(tmp_path: Path) -> None:
    runtime = tmp_path / ".runtime" / "bilibili-learning"
    reservation = claim_reservation(runtime, "BV1TXua68EYi")
    missing_job = runtime / "BV1TXua68EYi-missing"
    bind_reservation(reservation, missing_job)

    replacement = claim_reservation(runtime, "BV1TXua68EYi")
    assert replacement.path.is_file()


def test_cleanup_incomplete_job_releases_bound_reservation(tmp_path: Path) -> None:
    runtime = tmp_path / ".runtime" / "bilibili-learning"
    reservation = claim_reservation(runtime, "BV1TXua68EYi")
    job = runtime / "BV1TXua68EYi-incomplete"
    job.mkdir()
    (job / "partial.info.json").write_text("{}", encoding="utf-8")
    bind_reservation(reservation, job)

    cleanup_job(runtime, job)

    assert not job.exists()
    replacement = claim_reservation(runtime, "BV1TXua68EYi")
    assert replacement.path.is_file()


def test_dead_incomplete_reservation_is_reclaimed_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path / ".runtime" / "bilibili-learning"
    reservation = claim_reservation(runtime, "BV1TXua68EYi")
    job = runtime / "BV1TXua68EYi-incomplete"
    job.mkdir()
    bind_reservation(reservation, job)
    monkeypatch.setattr("bili_learning.runtime._process_is_alive", lambda _pid: False)

    replacement = claim_reservation(runtime, "BV1TXua68EYi")

    assert replacement.path.is_file()
    assert not job.exists()


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
    reservations = list(locks.glob("*.reservation.json"))
    assert len(reservations) == 1
    assert json.loads(reservations[0].read_text(encoding="utf-8"))["state"] == "released"


def test_prepare_requires_explicit_notes_location_before_collection(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    called = False

    def fail_if_called(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        raise AssertionError("yt-dlp should not run before explicit notes configuration")

    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", fail_if_called)
    payload, code = prepare_note(tmp_path, "BV1TXua68EYi", on_existing="rerun")

    assert code == 2
    assert payload["status"] == "onboarding_required"
    action_codes = {action["code"] for action in payload["actions"]}
    assert "obsidian_vault_required" in action_codes
    assert called is False


def test_prepare_reports_ytdlp_dependency_code_without_auto_install(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    (config_dir / "local.json").write_text(json.dumps({"notes_root": "notes/bilibili"}), encoding="utf-8")
    monkeypatch.delenv("BILI_LEARNING_YTDLP", raising=False)
    monkeypatch.setattr("bili_learning.config.shutil.which", lambda _name: None)

    payload, code = prepare_note(tmp_path, "BV1TXua68EYi", on_existing="rerun")

    assert code == 2
    assert payload["status"] == "onboarding_required"
    ytdlp_action = next(action for action in payload["actions"] if action["code"] == "ytdlp_required")
    assert ytdlp_action["recommended_command"] == "winget install yt-dlp"
    assert "不会自动安装" in ytdlp_action["message"]


def test_prepare_in_progress_returns_bound_job_dir(tmp_path: Path, taxonomy: dict) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    settings = load_settings(tmp_path)
    reservation = claim_reservation(settings.runtime_root, "BV1TXua68EYi")
    job = settings.runtime_root / "BV1TXua68EYi-existing"
    job.mkdir(parents=True)
    (job / "job.json").write_text(json.dumps({"bvid": "BV1TXua68EYi"}), encoding="utf-8")
    bind_reservation(reservation, job)

    payload, code = prepare_note(tmp_path, "BV1TXua68EYi", on_existing="rerun")

    assert code == 2
    assert payload["status"] == "in_progress"
    assert payload["job_dir"] == str(job)
    cleanup_job(settings.runtime_root, job)


def test_prepare_recovers_complete_job_from_dead_owner_without_recollecting(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)
    prepared, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and prepared["status"] == "materials_ready"

    handoff = Path(prepared["handoff_path"])
    handoff.replace(handoff.with_name("agent_handoff.saved"))
    monkeypatch.setattr("bili_learning.runtime._process_is_alive", lambda _pid: False)

    def fail_if_recollected(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("recoverable job must not run yt-dlp again")

    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", fail_if_recollected)
    recovered, recover_code = prepare_note(tmp_path, "BV1TXua68EYi")

    assert recover_code == 0
    assert recovered["status"] == "materials_ready"
    assert recovered["recovered"] is True
    assert recovered["job_dir"] == prepared["job_dir"]
    assert Path(recovered["handoff_path"]).is_file()


def test_prepare_rerun_allows_a_new_note_for_an_existing_source(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    existing = tmp_path / "notes" / "bilibili" / "archived.md"
    existing.parent.mkdir(parents=True)
    existing.write_text(
        '---\nsource: "https://www.bilibili.com/video/BV1TXua68EYi/"\n---\n\n# 已归档\n', encoding="utf-8"
    )
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)
    payload, code = prepare_note(tmp_path, "BV1TXua68EYi", on_existing="rerun")
    assert code == 0 and payload["status"] == "materials_ready"
    assert Path(payload["note_path"]).name == "H3 分段工作流.md"
    assert payload["source_package_mode"] == "direct"
    assert payload["transcript_chunk_count"] == 1
    assert Path(payload["transcript_manifest_path"]).is_file()
    assert payload["workflow_mode"] == "light"
    assert "fact_ledger_path" not in payload
    assert "semantic_draft_path" not in payload
    assert "layout_plan_path" not in payload


def _write_e2e_config(project_root: Path, taxonomy: dict) -> None:
    config_dir = project_root / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")


    cookie = project_root / "cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    ytdlp = Path(sys.executable)
    (config_dir / "local.json").write_text(
        json.dumps({"notes_root": "notes/bilibili", "cookie_file": str(cookie), "ytdlp": str(ytdlp)}),
        encoding="utf-8",
    )


def _fake_ytdlp(
    _settings: Settings,
    job_dir: Path,
    canonical_url: str,
    *,
    include_subtitles: bool = True,
) -> None:
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
    if include_subtitles:
        (job_dir / f"{bvid}.ai-zh.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n字幕\n", encoding="utf-8")


def _finalize_prepared_note(project_root: Path, prepared: dict) -> tuple[dict, int]:
    draft = Path(prepared["draft_path"])
    draft.write_text(_complete_ai_regions(draft.read_text(encoding="utf-8")), encoding="utf-8")
    _write_passed_analysis(Path(prepared["analysis_path"]))
    return finalize_note(project_root, Path(prepared["job_dir"]), draft)


def test_duplicate_bvid_stops_before_collection_and_requests_user_choice(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)
    first, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0
    completed, finalize_code = _finalize_prepared_note(tmp_path, first)
    assert finalize_code == 0 and completed["status"] == "note_ready"

    def fail_if_collected(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("duplicate preflight must run before yt-dlp")

    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", fail_if_collected)
    duplicate, duplicate_code = prepare_note(tmp_path, "BV1TXua68EYi")

    assert duplicate_code == 2
    assert duplicate["status"] == "existing_note_found"
    assert duplicate["existing_note_count"] == 1
    assert duplicate["allowed_actions"] == ["update", "rerun", "cancel"]
    assert duplicate["update_target_required"] is False
    assert Path(duplicate["existing_notes"][0]["path"]).resolve() == Path(first["note_path"]).resolve()


def test_update_existing_note_preserves_path_and_uses_snapshot(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)
    first, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0
    completed, finalize_code = _finalize_prepared_note(tmp_path, first)
    assert finalize_code == 0 and completed["status"] == "note_ready"
    original_path = Path(first["note_path"])
    original_text = original_path.read_text(encoding="utf-8")

    update, update_code = prepare_note(tmp_path, "BV1TXua68EYi", on_existing="update")

    assert update_code == 0 and update["status"] == "materials_ready"
    assert update["operation_mode"] == "update"
    assert Path(update["note_path"]).resolve() == original_path.resolve()
    snapshot = Path(update["existing_note_snapshot_path"])
    assert snapshot.read_text(encoding="utf-8") == original_text
    assert "任务操作：`update`" in Path(update["handoff_path"]).read_text(encoding="utf-8")

    completed, finalize_code = _finalize_prepared_note(tmp_path, update)
    assert finalize_code == 0
    assert completed["status"] == "note_ready"
    assert completed["publish_state"] == "updated"
    assert Path(completed["note_path"]).resolve() == original_path.resolve()
    assert not original_path.with_name("H3 分段工作流（2）.md").exists()


def test_update_requires_target_when_multiple_same_bvid_notes_exist(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)
    first, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0
    assert _finalize_prepared_note(tmp_path, first)[1] == 0
    second, code = prepare_note(tmp_path, "BV1TXua68EYi", on_existing="rerun")
    assert code == 0
    assert _finalize_prepared_note(tmp_path, second)[1] == 0

    result, result_code = prepare_note(tmp_path, "BV1TXua68EYi", on_existing="update")

    assert result_code == 2
    assert result["status"] == "update_target_required"
    assert len(result["existing_notes"]) == 2

    selected = Path(result["existing_notes"][1]["path"])
    update, update_code = prepare_note(
        tmp_path,
        "BV1TXua68EYi",
        on_existing="update",
        update_target=selected,
    )
    assert update_code == 0 and update["status"] == "materials_ready"
    assert Path(update["note_path"]).resolve() == selected.resolve()


def test_update_conflict_does_not_overwrite_manual_change(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)
    first, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0
    assert _finalize_prepared_note(tmp_path, first)[1] == 0
    target = Path(first["note_path"])

    update, code = prepare_note(tmp_path, "BV1TXua68EYi", on_existing="update")
    assert code == 0
    target.write_text(target.read_text(encoding="utf-8") + "\nmanual change\n", encoding="utf-8")
    draft = Path(update["draft_path"])
    draft.write_text(_complete_ai_regions(draft.read_text(encoding="utf-8")), encoding="utf-8")
    _write_passed_analysis(Path(update["analysis_path"]))

    result, finalize_code = finalize_note(tmp_path, Path(update["job_dir"]), draft)

    assert finalize_code == 2
    assert result["status"] == "update_conflict"
    assert "manual change" in target.read_text(encoding="utf-8")


def test_same_title_different_bvid_does_not_trigger_duplicate_prompt(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    existing = tmp_path / "notes" / "bilibili" / "00-待整理" / "H3 分段工作流.md"
    existing.parent.mkdir(parents=True)
    existing.write_text(
        '---\nsource: "https://www.bilibili.com/video/BV1DIFFERENT/"\n---\n\n# H3 分段工作流\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    prepared, code = prepare_note(tmp_path, "BV1TXua68EYi")

    assert code == 0 and prepared["status"] == "materials_ready"
    assert prepared["operation_mode"] == "create"
    assert Path(prepared["note_path"]).name == "H3 分段工作流（2）.md"


def test_prepare_transcript_builds_standard_job_and_finalizes(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    transcript = tmp_path / "sensevoice.txt"
    transcript.write_text("这是 ASR 转写。三连后领取工作流。", encoding="utf-8")
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    prepared, code = prepare_transcript_note(tmp_path, "BV1TXua68EYi", transcript)

    assert code == 0 and prepared["status"] == "materials_ready"
    assert prepared["asr_fallback_used"] is True
    assert prepared["transcript_source_type"] == "asr_text"
    assert "subtitle_path" not in prepared
    runtime_source = Path(prepared["transcript_source_path"])
    assert runtime_source.name == "asr-transcript.txt"
    assert runtime_source.read_text(encoding="utf-8") == transcript.read_text(encoding="utf-8")
    manifest = json.loads(Path(prepared["transcript_manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["source_type"] == "asr_text"
    assert manifest["timestamps_available"] is False

    draft = Path(prepared["draft_path"])
    draft.write_text(_complete_ai_regions(draft.read_text(encoding="utf-8")), encoding="utf-8")
    _write_passed_analysis(Path(prepared["analysis_path"]))
    completed, finalize_code = finalize_note(tmp_path, Path(prepared["job_dir"]), draft)
    assert finalize_code == 0 and completed["status"] == "note_ready"
    assert Path(prepared["note_path"]).is_file()


def test_prepare_transcript_recovers_complete_job_after_external_transcript_disappears(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    transcript = tmp_path / "sensevoice.txt"
    transcript.write_text("可恢复的 ASR 文本。", encoding="utf-8")
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    prepared, code = prepare_transcript_note(tmp_path, "BV1TXua68EYi", transcript)
    assert code == 0 and prepared["status"] == "materials_ready"
    transcript.unlink()
    monkeypatch.setattr("bili_learning.runtime._process_is_alive", lambda _pid: False)

    def fail_if_recollected(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("recoverable ASR job must not run yt-dlp again")

    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", fail_if_recollected)
    recovered, recover_code = prepare_transcript_note(tmp_path, "BV1TXua68EYi", transcript)

    assert recover_code == 0
    assert recovered["status"] == "materials_ready"
    assert recovered["recovered"] is True
    assert recovered["asr_fallback_used"] is True
    assert recovered["job_dir"] == prepared["job_dir"]
    assert Path(recovered["transcript_source_path"]).is_file()


def test_prepare_description_builds_standard_resource_job_and_finalizes(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    include_subtitles_calls: list[bool] = []

    def fake_ytdlp(
        settings: Settings,
        job_dir: Path,
        canonical_url: str,
        *,
        include_subtitles: bool = True,
    ) -> None:
        include_subtitles_calls.append(include_subtitles)
        _fake_ytdlp(settings, job_dir, canonical_url, include_subtitles=include_subtitles)

    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    prepared, code = prepare_description_note(
        tmp_path,
        "纯资源分享，只整理简介，不用字幕：BV1TXua68EYi",
    )

    assert code == 0 and prepared["status"] == "materials_ready"
    assert include_subtitles_calls == [False]
    assert prepared["source_mode"] == SOURCE_MODE_DESCRIPTION
    assert prepared["source_path"] is None
    assert prepared["source_package_mode"] == "none"
    assert prepared["source_chunk_count"] == 0
    assert prepared["source_timestamps_available"] is False
    assert "subtitle_path" not in prepared
    manifest = json.loads(Path(prepared["source_manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["source_mode"] == SOURCE_MODE_DESCRIPTION
    assert manifest["source_location"] == "job.description"
    assert manifest["chunks"] == []
    handoff = Path(prepared["handoff_path"]).read_text(encoding="utf-8")
    assert "纯资源分享" in handoff
    assert "不要推断视频口播" in handoff

    draft = Path(prepared["draft_path"])
    draft.write_text(_complete_ai_regions(draft.read_text(encoding="utf-8")), encoding="utf-8")
    _write_passed_analysis(Path(prepared["analysis_path"]))
    completed, finalize_code = finalize_note(tmp_path, Path(prepared["job_dir"]), draft)
    assert finalize_code == 0 and completed["status"] == "note_ready"
    assert Path(prepared["note_path"]).is_file()


def test_prepare_description_recovers_without_a_source_file(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    prepared, code = prepare_description_note(tmp_path, "纯资源分享：BV1TXua68EYi")
    assert code == 0 and prepared["status"] == "materials_ready"
    monkeypatch.setattr("bili_learning.runtime._process_is_alive", lambda _pid: False)

    def fail_if_recollected(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("recoverable description-only job must not run yt-dlp again")

    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", fail_if_recollected)
    recovered, recover_code = prepare_description_note(tmp_path, "纯资源分享：BV1TXua68EYi")

    assert recover_code == 0
    assert recovered["status"] == "materials_ready"
    assert recovered["recovered"] is True
    assert recovered["source_mode"] == SOURCE_MODE_DESCRIPTION
    assert recovered["source_path"] is None
    assert recovered["job_dir"] == prepared["job_dir"]


def test_e2e_draft_publish_navigation_and_repeated_video(
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
    _write_passed_analysis(Path(first["analysis_path"]))
    completed, code = finalize_note(tmp_path, Path(first["job_dir"]), draft)
    assert code == 0 and completed["status"] == "note_ready"
    assert target.is_file()
    assert "BILI_AI_" not in target.read_text(encoding="utf-8")
    assert not Path(first["job_dir"]).exists()
    nav = tmp_path / "notes" / "bilibili" / "99-导航" / "首页.md"
    assert nav.is_file()

    repeated, code = prepare_note(tmp_path, "BV1TXua68EYi", on_existing="rerun")
    assert code == 0 and repeated["status"] == "materials_ready"
    assert Path(repeated["note_path"]).name == "H3 分段工作流（2）.md"


def test_e2e_strict_mode_still_publishes_after_stage_completion(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    local_path = tmp_path / "config" / "local.json"
    local_config = json.loads(local_path.read_text(encoding="utf-8"))
    local_config["workflow_mode"] = "strict"
    local_path.write_text(json.dumps(local_config), encoding="utf-8")
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    prepared, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and prepared["status"] == "materials_ready"
    assert prepared["workflow_mode"] == "strict"
    for key in ("fact_ledger_path", "semantic_draft_path", "layout_plan_path"):
        assert Path(prepared[key]).is_file()

    draft = Path(prepared["draft_path"])
    draft.write_text(_complete_ai_regions(draft.read_text(encoding="utf-8")), encoding="utf-8")
    _write_passed_analysis(Path(prepared["analysis_path"]))
    _complete_agent_workflow(prepared)

    completed, code = finalize_note(tmp_path, Path(prepared["job_dir"]), draft)

    assert code == 0 and completed["status"] == "note_ready"
    assert Path(prepared["note_path"]).is_file()


def test_finalize_keeps_note_ready_when_cleanup_fails(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)
    prepared, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and prepared["status"] == "materials_ready"
    draft = Path(prepared["draft_path"])
    draft.write_text(_complete_ai_regions(draft.read_text(encoding="utf-8")), encoding="utf-8")
    _write_passed_analysis(Path(prepared["analysis_path"]))

    cleanup_attempts = 0

    def flaky_cleanup(runtime_root: Path, job_dir: Path) -> None:
        nonlocal cleanup_attempts
        cleanup_attempts += 1
        if cleanup_attempts == 1:
            raise PermissionError("WinError 32")
        cleanup_job(runtime_root, job_dir)

    monkeypatch.setattr("bili_learning.lifecycle.cleanup_job", flaky_cleanup)

    result, code = finalize_note(tmp_path, Path(prepared["job_dir"]), draft)

    assert code == 0
    assert result["status"] == "note_ready"
    assert result["publish_state"] == "published"
    assert result["temporary_data_retired"] is False
    assert result["temporary_data_removed"] is False
    assert result["note_path"] == prepared["note_path"]
    assert "WinError 32" in result["cleanup_warning"]

    retried, retry_code = finalize_note(tmp_path, Path(prepared["job_dir"]), draft)
    assert retry_code == 0
    assert retried["status"] == "note_ready"
    assert retried["publish_state"] == "already_published"
    assert retried["temporary_data_retired"] is True
    assert retried["temporary_data_removed"] is False
    assert not Path(prepared["job_dir"]).exists()


def test_safe_delete_failures_do_not_break_prepare_or_finalize(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    def blocked_delete(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise OSError("windows-sandbox-recycle-bin-unavailable")

    monkeypatch.setattr(Path, "unlink", blocked_delete)
    monkeypatch.setattr("shutil.rmtree", blocked_delete)

    prepared, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and prepared["status"] == "materials_ready"
    draft = Path(prepared["draft_path"])
    draft.write_text(_complete_ai_regions(draft.read_text(encoding="utf-8")), encoding="utf-8")
    _write_passed_analysis(Path(prepared["analysis_path"]))

    completed, finalize_code = finalize_note(tmp_path, Path(prepared["job_dir"]), draft)

    assert finalize_code == 0
    assert completed["status"] == "note_ready"
    assert completed["temporary_data_retired"] is True
    assert Path(prepared["note_path"]).is_file()


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
    _write_passed_analysis(Path(finished["analysis_path"]))

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


def test_source_insufficient_is_cleaned_without_publishing(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)

    prepared, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and prepared["status"] == "materials_ready"
    analysis = Path(prepared["analysis_path"])
    analysis.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_assessment": {"status": "insufficient", "reason": "关键参数只能从画面确认。"},
                "knowledge_outline": [],
                "coverage_review": {"status": "not_applicable", "notes": ""},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result, code = finalize_note(tmp_path, Path(prepared["job_dir"]), Path(prepared["draft_path"]))
    assert code == 2
    assert result["status"] == "source_insufficient"
    assert not Path(prepared["note_path"]).exists()
    assert not Path(prepared["job_dir"]).exists()


def test_organize_note_requires_explicit_scope_confirmation(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    with pytest.raises(ValueError, match="整理功能默认不执行"):
        organize_note(
            settings,
            settings.notes_root / "00-待整理" / "不会执行.md",
            "不会执行",
            destination="01-视频/MiniMax-H3",
            confirmed_scope="",
        )


def test_organize_latest_rejects_a_non_latest_inbox_note(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    inbox = settings.notes_root / "00-待整理"
    inbox.mkdir(parents=True)
    older = inbox / "older.md"
    newer = inbox / "newer.md"
    older.write_text("# older\n", encoding="utf-8")
    newer.write_text("# newer\n", encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    with pytest.raises(ValueError, match="不是最近一篇"):
        organize_note(
            settings,
            older,
            "older",
            destination="01-视频/MiniMax-H3",
            confirmed_scope="latest",
        )


def test_duplicate_bvid_detection_reports_other_notes_without_blocking(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    inbox = settings.notes_root / "00-待整理"
    archive = settings.notes_root / "01-视频生成" / "01-MiniMax-H3"
    inbox.mkdir(parents=True)
    archive.mkdir(parents=True)
    source = inbox / "source.md"
    duplicate = archive / "duplicate.md"
    other = archive / "other.md"
    source.write_text("https://www.bilibili.com/video/BV1TXua68EYi/", encoding="utf-8")
    duplicate.write_text('<iframe src="https://player.bilibili.com/player.html?bvid=BV1TXua68EYi"></iframe>', encoding="utf-8")
    other.write_text("https://www.bilibili.com/video/BV1DIFFERENT/", encoding="utf-8")

    bvid, duplicates = find_duplicate_bvid_notes(settings, source)

    assert bvid == "BV1TXua68EYi"
    assert duplicates == [duplicate.resolve()]


def test_agent_skill_requires_organize_scope_confirmation() -> None:
    root = Path(__file__).parents[1]
    text = (root / "skill/bili-learning-automation/SKILL.md").read_text(encoding="utf-8")
    assert "默认关闭" in text
    assert "指定" in text
    assert "最近一篇" in text
    assert "全部待整理笔记" in text
    assert "single" in text
    assert "--filename" in text
    assert "--destination" in text
    assert "不得修改笔记内容" in text
    assert "--confirmed-scope" in text
    assert "prepare-transcript" in text
    assert "不得把纯文本伪造成 SRT" in text
    assert "不得制造时间戳" in text
    assert "existing_note_found" in text
    assert "--on-existing rerun" in text
    assert "--on-existing update" in text
    assert "--update-target" in text
    assert "原始完整消息" in text
    assert "update_conflict" in text


def test_organize_note_only_renames_moves_and_rebuilds_navigation(tmp_path: Path, taxonomy: dict) -> None:
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
        _complete_ai_regions(render_note_skeleton(job)).replace("<!-- BILI_AI_SUMMARY_START -->", "").replace("<!-- BILI_AI_SUMMARY_END -->", "").replace("<!-- BILI_AI_BODY_START -->", "").replace("<!-- BILI_AI_BODY_END -->", ""),
        encoding="utf-8",
    )
    before = source.read_bytes()
    target = organize_note(
        settings,
        source,
        "工作流：MiniMax H3 分段生成",
        destination="01-视频/MiniMax-H3",
        confirmed_scope="single",
    )
    assert target == settings.notes_root / "01-视频" / "MiniMax-H3" / "工作流：MiniMax H3 分段生成.md"
    assert not source.exists()
    assert target.read_bytes() == before
    organized = target.read_text(encoding="utf-8")
    assert organized.startswith("---")
    assert "# H3 分段工作流" in organized
    assert "原始说明" in organized
    assert metadata_line(job) in organized
    assert 'class="video-note-original-title"' not in organized
    _, organized_tags = parse_frontmatter(organized)
    assert organized_tags == ["视频生成", "工作流", "MiniMax-H3"]
    assert "待整理" not in organized_tags
    assert (settings.notes_root / "99-导航" / "01-视频.md").is_file()
    assert "00-待整理]]（0）" in (settings.notes_root / "99-导航" / "首页.md").read_text(encoding="utf-8")


def test_organize_note_does_not_add_learning_intro_when_source_has_only_resources(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    source = settings.notes_root / "00-待整理" / "资源型简介.md"
    source.parent.mkdir(parents=True)
    job = {
        "bvid": "BV1TXua68EYi",
        "author": "UP",
        "published": "2026-08-11",
        "duration": "07:05",
        "canonical_url": "https://www.bilibili.com/video/BV1TXua68EYi/",
        "required_tags": ["视频生成", "工作流", "MiniMax-H3"],
        "description": "工作流：https://example.com/workflow",
        "description_status": "present",
        "canonical_title": "资源型简介",
    }
    source.write_text(
        _complete_ai_regions(render_note_skeleton(job))
        .replace("<!-- BILI_AI_SUMMARY_START -->", "")
        .replace("<!-- BILI_AI_SUMMARY_END -->", "")
        .replace("<!-- BILI_AI_BODY_START -->", "")
        .replace("<!-- BILI_AI_BODY_END -->", ""),
        encoding="utf-8",
    )
    before = source.read_bytes()
    target = organize_note(
        settings,
        source,
        "教程：资源型简介",
        destination="01-视频/MiniMax-H3",
        confirmed_scope="latest",
    )
    text = target.read_text(encoding="utf-8")
    assert target.read_bytes() == before
    assert metadata_line(job) in text
    assert "学习后补充的一句简介。" not in text
    assert target.name == "教程：资源型简介.md"


def test_organize_note_does_not_migrate_legacy_content(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    source = settings.notes_root / "00-待整理" / "旧标题__BV1TXua68EYi.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "---\nsource: \"https://www.bilibili.com/video/BV1TXua68EYi/\"\ntags:\n  - \"视频生成\"\n  - \"工作流\"\n---\n\n"
        "# 旧标题\n\n> **视频简介**\n>\n> 原始说明\n> 工作流：\n> https://example.com/workflow\n\n"
        "<iframe src=\"https://player.bilibili.com/player.html?bvid=BV1TXua68EYi\"></iframe>\n",
        encoding="utf-8",
    )
    before = source.read_bytes()
    target = organize_note(
        settings,
        source,
        "教程：旧笔记示例",
        destination="01-视频/MiniMax-H3",
        confirmed_scope="latest",
    )
    text = target.read_text(encoding="utf-8")
    assert target.name == "教程：旧笔记示例.md"
    assert target.read_bytes() == before
    assert "## 视频资料" not in text
    assert "> **视频简介**" in text
    assert "https://example.com/workflow" in text
    assert '<details class="video-note-source-details">' not in text
    assert "<summary>UP 主原文（完整说明与链接）</summary>" not in text
    assert "# 旧标题" in text


def test_organize_note_keeps_same_name_versions_without_overwriting(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    inbox = settings.notes_root / "00-待整理"
    destination = settings.notes_root / "02-图像" / "Krea2"
    inbox.mkdir(parents=True)
    destination.mkdir(parents=True)
    existing = destination / "百科：Krea-2 生图模型全解.md"
    existing.write_text("existing\n", encoding="utf-8")
    source = inbox / "source.md"
    source.write_text("new version\n", encoding="utf-8")

    target = organize_note(
        settings,
        source,
        "百科：Krea-2 生图模型全解.md",
        destination="02-图像/Krea2",
        confirmed_scope="single",
    )

    assert target.name == "百科：Krea-2 生图模型全解（2）.md"
    assert existing.read_text(encoding="utf-8") == "existing\n"
    assert target.read_text(encoding="utf-8") == "new version\n"


def test_organize_note_rejects_more_than_two_destination_levels(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    source = settings.notes_root / "00-待整理" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("content\n", encoding="utf-8")

    with pytest.raises(ValueError, match="最多允许 2 层"):
        organize_note(
            settings,
            source,
            "简单文件名",
            destination="02-图像/Krea2/模型与LoRA",
            confirmed_scope="single",
        )

    assert source.exists()


def test_organize_resource_note_compacts_into_collection_and_keeps_recovery_backup(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    source = settings.notes_root / "00-待整理" / "纯资源分享.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        '---\nauthor: "UP"\npublished: "2026-08-28"\nduration: "00:40"\nsource: "https://www.bilibili.com/video/BV1RESOURCE01/"\ntags:\n  - "Agent"\ncssclasses:\n  - "learning-page"\n  - "video-note"\n---\n\n'
        '# 纯资源分享\n\n<iframe src="https://player.bilibili.com/player.html?bvid=BV1RESOURCE01"></iframe>\n',
        encoding="utf-8",
    )
    card = settings.runtime_root / "resource-cards" / "card.md"
    card.parent.mkdir(parents=True)
    card.write_text(
        "## VideoShotCraft\n\n- **功能**：AI Agent 镜头编排与剪映工程导出。\n- **获取**：https://github.com/example/video-shotcraft\n- **状态**：待测试\n",
        encoding="utf-8",
    )

    result = organize_resource_note(
        settings,
        source,
        "AI工具与项目",
        card_path=card,
        confirmed_scope="single",
    )

    collection = settings.notes_root / "05-资源" / "AI工具与项目.md"
    text = collection.read_text(encoding="utf-8")
    assert result["collection_path"] == collection
    assert result["updated_existing_card"] is False
    assert not source.exists()
    assert not card.exists()
    assert Path(result["backup_path"]).is_file()
    assert "<!-- BILI_RESOURCE_COLLECTION -->" in text
    assert "## VideoShotCraft" in text
    assert "BV1RESOURCE01" in text
    assert find_notes_by_bvid(settings, "BV1RESOURCE01") == []
    assert "05-资源]]（1）" in (settings.notes_root / "99-导航" / "首页.md").read_text(encoding="utf-8")


def test_organize_resource_note_updates_same_bvid_card_without_duplication(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    inbox = settings.notes_root / "00-待整理"
    inbox.mkdir(parents=True)

    def compact(body: str) -> dict[str, object]:
        source = inbox / "resource.md"
        source.write_text(
            '---\nauthor: "UP"\npublished: "2026-08-28"\nduration: "00:40"\nsource: "https://www.bilibili.com/video/BV1RESOURCE02/"\ntags:\n  - "Agent"\ncssclasses:\n  - "learning-page"\n  - "video-note"\n---\n\n'
            '# 资源更新\n\n<iframe src="https://player.bilibili.com/player.html?bvid=BV1RESOURCE02"></iframe>\n',
            encoding="utf-8",
        )
        card = settings.runtime_root / "resource-cards" / "card.md"
        card.parent.mkdir(parents=True, exist_ok=True)
        card.write_text(body, encoding="utf-8")
        return organize_resource_note(settings, source, "Skills", card_path=card, confirmed_scope="single")

    first = compact("## AI电影 Skills\n\n- **状态**：待下载\n")
    second = compact("## AI电影 Skills\n\n- **状态**：已下载\n")
    collection = settings.notes_root / "05-资源" / "Skills.md"
    text = collection.read_text(encoding="utf-8")

    assert first["updated_existing_card"] is False
    assert second["updated_existing_card"] is True
    assert text.count("## AI电影 Skills") == 1
    assert "已下载" in text
    assert "待下载" not in text


def test_navigation_uses_meta_marker_to_distinguish_same_title_notes(tmp_path: Path, taxonomy: dict) -> None:
    settings = _settings(tmp_path, taxonomy)
    category = settings.notes_root / "01-视频" / "MiniMax-H3"
    category.mkdir(parents=True)
    first = category / "同名笔记.md"
    second = category / "同名笔记（2）.md"
    base = '---\ntags:\n  - "MiniMax-H3"\n---\n\n# 同名笔记\n\n'
    first.write_text(base + '<small class="video-note-meta">UP · 2026-08-24 · 01:00 · BV1FIRST</small>\n', encoding="utf-8")
    second.write_text(base + '<small class="video-note-meta">(workbuddy) UP · 2026-08-24 · 01:00 · BV1SECOND</small>\n', encoding="utf-8")

    navigation.build_navigation(settings)

    category_nav = (settings.notes_root / "99-导航" / "01-视频.md").read_text(encoding="utf-8")
    model_nav = (settings.notes_root / "99-导航" / "模型索引.md").read_text(encoding="utf-8")
    assert "|同名笔记]]" in category_nav
    assert "|同名笔记 (workbuddy)]]" in category_nav
    assert "|同名笔记 (workbuddy)]]" in model_nav


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


def test_ytdlp_metadata_only_mode_skips_subtitle_requests(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path, taxonomy)
    job_dir = settings.runtime_root / "metadata-job"
    job_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0

    def fake_run(command, **_kwargs):  # type: ignore[no-untyped-def]
        captured["command"] = command
        return Completed()

    monkeypatch.setattr("bili_learning.collector.subprocess.run", fake_run)
    run_ytdlp(
        settings,
        job_dir,
        "https://www.bilibili.com/video/BV1TXua68EYi/",
        include_subtitles=False,
    )

    command = captured["command"]
    assert isinstance(command, list)
    assert "--skip-download" in command
    assert "--write-info-json" in command
    assert "--write-description" in command
    assert "--write-subs" not in command
    assert "--write-auto-subs" not in command
    assert "--sub-langs" not in command
    assert "--sub-format" not in command


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
    assert lock.is_file()


def test_file_lock_recovers_fresh_dead_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock = tmp_path / "locks" / "BV1TXua68EYi.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("12345", encoding="ascii")
    monkeypatch.setattr("bili_learning.runtime._process_is_alive", lambda _pid: False)

    with file_lock(lock):
        assert lock.is_file()

    assert lock.is_file()


def test_file_lock_recovers_stale_file(tmp_path: Path) -> None:
    lock = tmp_path / "locks" / "BV1TXua68EYi.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("old", encoding="utf-8")
    old = time.time() - 7200
    os.utime(lock, (old, old))
    with file_lock(lock, stale_seconds=3600):
        assert lock.is_file()
    assert lock.is_file()
