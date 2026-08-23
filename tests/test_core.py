from __future__ import annotations

import json
import os
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
    configure_obsidian,
    find_ytdlp,
    load_settings,
    validate_taxonomy,
)
from bili_learning.doctor import doctor_report
from bili_learning.frontmatter import parse_frontmatter, parse_frontmatter_list
from bili_learning.input_resolver import resolve_input
from bili_learning.lifecycle import finalize_note, prepare_note
from bili_learning.note_template import (
    bvid_line,
    metadata_line,
    note_filename,
    quote_description,
    render_note_skeleton,
    render_video_materials,
)
from bili_learning.organizer import organize_note
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
from bili_learning.taxonomy import classify
from bili_learning.transcript import prepare_agent_transcript
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

    assert result["mode"] == "chunked"
    assert result["chunk_count"] > 1
    assert sum(chunk["cue_count"] for chunk in result["chunks"]) == 6
    combined = "".join(Path(chunk["path"]).read_text(encoding="utf-8") for chunk in result["chunks"])
    positions = [combined.index(f"知识点{index}-") for index in range(1, 7)]
    assert positions == sorted(positions)
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["rules"]["semantic_summary"] is False
    assert manifest["rules"]["text_order_preserved"] is True
    assert manifest["rules"]["cue_boundaries_preserved"] is True


def test_prepare_agent_transcript_merges_a_tiny_tail_chunk(tmp_path: Path) -> None:
    subtitle = tmp_path / "tail.ai-zh.srt"
    blocks = [
        "1\n00:00:01,000 --> 00:00:02,000\n" + ("甲" * 22_980),
        "2\n00:00:02,000 --> 00:00:03,000\n" + ("乙" * 22_980),
        "3\n00:00:03,000 --> 00:00:04,000\n尾巴",
    ]
    subtitle.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")

    result = prepare_agent_transcript(subtitle, tmp_path / "agent-work")

    assert result["mode"] == "chunked"
    assert result["chunk_count"] == 2
    assert sum(chunk["cue_count"] for chunk in result["chunks"]) == 3
    combined = "".join(Path(chunk["path"]).read_text(encoding="utf-8") for chunk in result["chunks"])
    assert "尾巴" in combined


def test_agent_handoff_protects_dense_note_fact_relationships(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    handoff = write_handoff(job_dir, {})
    text = handoff.read_text(encoding="utf-8")
    assert "fact_ledger_path" in text
    assert "semantic_draft_path" in text
    assert "layout_plan_path" in text
    assert "Fact Ledger" in text
    assert "章节数量只改变事实如何分组" in text
    assert "Layout Pass" in text
    assert "一个最高优先级 Summary" in text
    assert "重新按 manifest 顺序抽查/复读原 transcript" in text
    assert "配置、耗时与结果" in text


def test_agent_handoff_light_mode_is_short_and_direct(tmp_path: Path) -> None:
    job_dir = tmp_path / "light-job"
    job_dir.mkdir()
    handoff = write_handoff(job_dir, {"workflow_mode": "light"})
    text = handoff.read_text(encoding="utf-8")

    assert "LIGHT-WORKFLOW.md" in text
    assert "直接在 `draft_path`" in text
    assert "内容写完整后" in text
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


def test_resource_access_detects_explicit_conditions_without_inventing_materials(tmp_path: Path) -> None:
    subtitle = tmp_path / "resource.ai-zh.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n这个提示词模板三连后我会发给大家\n\n"
        "2\n00:00:03,000 --> 00:00:04,000\n充电用户可以领取完整工作流\n\n"
        "3\n00:00:05,000 --> 00:00:06,000\n评论区回复H3领取资料\n",
        encoding="utf-8",
    )
    notices = detect_resource_access_notices("", subtitle)
    conditions = {notice["condition"] for notice in notices}
    assert "三连" in conditions
    assert "充电" in conditions
    assert "评论/关键词" in conditions
    assert all(notice["source"] == "subtitle" for notice in notices)


def test_resource_access_prefers_description_and_deduplicates_matching_subtitle(tmp_path: Path) -> None:
    subtitle = tmp_path / "duplicate.ai-zh.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n三连后领取提示词模板\n",
        encoding="utf-8",
    )
    notices = detect_resource_access_notices("三连后领取提示词模板", subtitle)
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
    assert detect_resource_access_notices("", subtitle) == []


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


def test_notes_root_conflicts_with_vault_config(tmp_path: Path, taxonomy: dict) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bilibili-note-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    (config_dir / "local.json").write_text(
        json.dumps({"notes_root": "notes", "vault_root": "vault"}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError) as error:
        load_settings(tmp_path)
    assert error.value.code == "local_config_notes_conflict"


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
        json.dumps({"ytdlp": "tools/yt-dlp.exe", "notes_root": "old/notes", "workflow_mode": "strict"}),
        encoding="utf-8",
    )
    vault = tmp_path / "MyVault"
    (vault / ".obsidian").mkdir(parents=True)

    path = configure_obsidian(tmp_path, vault, "Resources/Bilibili")
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved["ytdlp"] == "tools/yt-dlp.exe"
    assert saved["workflow_mode"] == "strict"
    assert "notes_root" not in saved
    assert saved["vault_root"] == str(vault.resolve())
    assert saved["notes_subdir"] == str(Path("Resources/Bilibili"))


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
        subtitle,
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
    manifest_path = Path(payload["transcript_manifest_path"])
    assert manifest_path.parent == agent_work_dir
    assert payload["transcript_mode"] == "direct"
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
        subtitle,
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
    payload, code = prepare_note(tmp_path, "BV1TXua68EYi")

    assert code == 2
    assert payload["status"] == "configuration_required"
    assert payload["required"] == "vault_root"
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

    payload, code = prepare_note(tmp_path, "BV1TXua68EYi")

    assert code == 1
    assert payload["status"] == "failed"
    assert payload["code"] == "ytdlp_not_configured"
    assert "winget install yt-dlp" in payload["message"]
    assert "不会自动安装" in payload["message"]


def test_prepare_in_progress_returns_bound_job_dir(tmp_path: Path, taxonomy: dict) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    settings = load_settings(tmp_path)
    reservation = claim_reservation(settings.runtime_root, "BV1TXua68EYi")
    job = settings.runtime_root / "BV1TXua68EYi-existing"
    job.mkdir(parents=True)
    (job / "job.json").write_text(json.dumps({"bvid": "BV1TXua68EYi"}), encoding="utf-8")
    bind_reservation(reservation, job)

    payload, code = prepare_note(tmp_path, "BV1TXua68EYi")

    assert code == 2
    assert payload["status"] == "in_progress"
    assert payload["job_dir"] == str(job)
    cleanup_job(settings.runtime_root, job)


def test_prepare_allows_a_new_note_for_an_existing_source(
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
    payload, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and payload["status"] == "materials_ready"
    assert Path(payload["note_path"]).name == "H3 分段工作流.md"
    assert payload["transcript_mode"] == "direct"
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


    (config_dir / "local.json").write_text(json.dumps({"notes_root": "notes/bilibili"}), encoding="utf-8")


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

    repeated, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and repeated["status"] == "materials_ready"
    assert Path(repeated["note_path"]).name == "H3 分段工作流（2）.md"


def test_e2e_strict_mode_still_publishes_after_stage_completion(
    tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    (tmp_path / "config" / "local.json").write_text(
        json.dumps({"notes_root": "notes/bilibili", "workflow_mode": "strict"}),
        encoding="utf-8",
    )
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


def test_finalize_reports_failure_when_cleanup_fails(tmp_path: Path, taxonomy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_e2e_config(tmp_path, taxonomy)
    monkeypatch.setattr("bili_learning.lifecycle.run_ytdlp", _fake_ytdlp)
    monkeypatch.setattr("bili_learning.lifecycle._schedule_failsafe_cleanup", lambda *args: None)
    prepared, code = prepare_note(tmp_path, "BV1TXua68EYi")
    assert code == 0 and prepared["status"] == "materials_ready"
    draft = Path(prepared["draft_path"])
    draft.write_text(_complete_ai_regions(draft.read_text(encoding="utf-8")), encoding="utf-8")
    _write_passed_analysis(Path(prepared["analysis_path"]))

    monkeypatch.setattr(
        "bili_learning.lifecycle.cleanup_job",
        lambda *_args: (_ for _ in ()).throw(PermissionError("WinError 32")),
    )

    result, code = finalize_note(tmp_path, Path(prepared["job_dir"]), draft)

    assert code == 1
    assert result["status"] == "failed"
    assert result["temporary_data_removed"] is False
    assert result["note_path"] == prepared["note_path"]
    assert "WinError 32" in result["cleanup_error"]


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
        _complete_ai_regions(render_note_skeleton(job)).replace("<!-- BILI_AI_SUMMARY_START -->", "").replace("<!-- BILI_AI_SUMMARY_END -->", "").replace("<!-- BILI_AI_BODY_START -->", "").replace("<!-- BILI_AI_BODY_END -->", ""),
        encoding="utf-8",
    )
    target = organize_note(settings, source, "H3 分段生成", "将长视频拆成连续片段生成。")
    assert target == settings.notes_root / "01-视频生成" / "01-MiniMax-H3" / "H3 分段生成.md"
    assert not source.exists()
    organized = target.read_text(encoding="utf-8")
    assert organized.startswith("---")
    assert "# H3 分段生成" in organized
    assert "将长视频拆成连续片段生成。" in organized
    assert metadata_line(job) in organized
    assert (settings.notes_root / "99-导航" / "01-视频生成.md").is_file()
    assert "00-待整理]]（0）" in (settings.notes_root / "99-导航" / "首页.md").read_text(encoding="utf-8")


def test_organize_note_adds_learning_intro_when_source_has_only_resources(tmp_path: Path, taxonomy: dict) -> None:
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
    target = organize_note(settings, source, "整理后标题", "学习后补充的一句简介。")
    text = target.read_text(encoding="utf-8")
    assert metadata_line(job) in text
    assert '<p class="video-note-overview"><strong>视频简介</strong>：学习后补充的一句简介。</p>' in text
    assert text.index("video-note-overview") < text.index('<details class="video-note-source-details">')


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
    assert "## 视频资料" not in text
    assert "### UP 主资源" in text
    assert "- [工作流](<https://example.com/workflow>)" in text
    assert '<details class="video-note-source-details">' in text
    assert "<summary>UP 主原文（完整说明与链接）</summary>" in text


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
