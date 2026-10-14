from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .config import YTDLP_RELATIVE_PATH, DependencyError, Settings
from .note_template import note_filename, write_skeleton
from .quality import write_analysis_template
from .resource_access import detect_resource_access_notices
from .runtime import cleanup_job, waiting_file_lock
from .source import SOURCE_MODE_ASR, SOURCE_MODE_DESCRIPTION, SOURCE_MODE_SUBTITLE, SourceMaterial
from .taxonomy import classify
from .transcript import prepare_agent_source
from .workflow import write_agent_work_templates

MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4", ".webm", ".flv", ".m4s", ".part"}
STALE_SECONDS = 2 * 60 * 60
YTDLP_TIMEOUT_SECONDS = 180
JOB_SCHEMA_VERSION = 1
NOTE_NAME_LOCK = "note-names.lock"


def cleanup_stale_jobs(settings: Settings) -> int:
    if not settings.runtime_root.is_dir():
        return 0
    cutoff = time.time() - STALE_SECONDS
    removed = 0
    for child in settings.runtime_root.iterdir():
        if child.name in {"locks", "retired"}:
            continue
        if child.is_dir() and not child.is_symlink() and child.stat().st_mtime < cutoff:
            cleanup_job(settings.runtime_root, child)
            removed += 1
    return removed


def duration_text(seconds: float | int | None) -> str:
    if seconds is None:
        return "00:00"
    total = max(0, round(float(seconds)))
    minutes, second = divmod(total, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{second:02d}" if hours else f"{minute:02d}:{second:02d}"


def run_ytdlp(
    settings: Settings,
    job_dir: Path,
    canonical_url: str,
    *,
    include_subtitles: bool = True,
) -> None:
    ytdlp = settings.ytdlp.path
    if ytdlp is None:
        raise DependencyError(
            "ytdlp_not_configured",
            f"项目缺少 {YTDLP_RELATIVE_PATH.as_posix()}；请由 Agent 恢复项目内官方单文件 EXE，禁止回退系统 yt-dlp。",
        )
    if not ytdlp.is_file():
        raise DependencyError("ytdlp_path_invalid", f"yt-dlp 路径不存在或不是文件（来源：{settings.ytdlp.source}）。")
    if not settings.cookie_file.is_file():
        raise DependencyError("cookie_file_missing", "Bilibili Cookie 文件不存在或未配置。")

    command = [
        str(ytdlp),
        "--ignore-config",
        "--no-cache-dir",
        "--cookies",
        str(settings.cookie_file),
        "--skip-download",
        "--no-playlist",
        "--write-info-json",
        "--write-description",
    ]
    if include_subtitles:
        command.extend(
            [
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs",
                "ai-zh,zh.*",
                "--sub-format",
                "srt",
            ]
        )
    command.extend(
        [
            "--no-write-comments",
            "--windows-filenames",
            "--paths",
            str(job_dir),
            "--output",
            "%(id)s.%(ext)s",
            canonical_url,
        ]
    )
    try:
        completed = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=YTDLP_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("yt-dlp 采集超时。") from exc
    if completed.returncode:
        raise RuntimeError("yt-dlp 采集失败；请检查 Cookie 是否失效或链接是否可访问。")


def media_count(job_dir: Path) -> int:
    return sum(1 for path in job_dir.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES)


def select_subtitle(job_dir: Path) -> Path | None:
    candidates = sorted(job_dir.glob("*.ai-zh.srt")) + sorted(job_dir.glob("*.zh*.srt"))
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def description_state(info: dict[str, Any], description_sidecar: str | None = None) -> tuple[str, str]:
    if "description" not in info:
        return "failed", ""
    raw = info["description"]
    if not isinstance(raw, str):
        return "failed", ""
    text = raw.strip()
    if description_sidecar is not None and text != description_sidecar.strip():
        return "failed", ""
    return ("present", text) if text else ("confirmed_empty", "")


def _reserved_note_paths(runtime_root: Path) -> set[Path]:
    reserved: set[Path] = set()
    if not runtime_root.is_dir():
        return reserved
    for job_dir in runtime_root.iterdir():
        if not job_dir.is_dir() or job_dir.name in {"locks", "retired"}:
            continue
        try:
            payload = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
            note_path = payload.get("note_path") if isinstance(payload, dict) else None
            if isinstance(note_path, str) and note_path:
                reserved.add(Path(note_path).resolve())
        except (OSError, json.JSONDecodeError):
            continue
    return reserved


def create_job(
    settings: Settings,
    bvid: str,
    canonical_url: str,
    info: dict[str, Any],
    source: SourceMaterial | Path,
    job_dir: Path,
    description_sidecar: str | None = None,
    user_supplied_source: dict[str, str] | None = None,
    uploader_pinned_comment: dict[str, Any] | None = None,
    *,
    operation_mode: str = "create",
    update_target_path: Path | None = None,
    update_target_sha256: str | None = None,
    existing_note_snapshot_path: Path | None = None,
) -> dict[str, Any]:
    if isinstance(source, Path):
        source = SourceMaterial(SOURCE_MODE_SUBTITLE, source)
    status, description = description_state(info, description_sidecar)
    if status == "failed":
        raise RuntimeError("无法确认 UP 主原始简介，任务已停止。")
    filing = classify(info, settings.taxonomy)
    canonical_title = " ".join(str(info.get("title") or "").split()) or "Bilibili 学习笔记"
    published = str(info.get("upload_date") or "")
    if len(published) == 8 and published.isdigit():
        published = f"{published[:4]}-{published[4:6]}-{published[6:]}"

    with waiting_file_lock(settings.runtime_root / "locks" / NOTE_NAME_LOCK):
        if operation_mode == "update":
            if update_target_path is None or update_target_sha256 is None or existing_note_snapshot_path is None:
                raise ValueError("更新 Job 缺少目标笔记、哈希或快照")
            note_path = update_target_path
        else:
            note_directory = settings.notes_root.joinpath(*filing["category_path"])
            reserved_paths = _reserved_note_paths(settings.runtime_root)
            sequence = 1
            note_path = note_directory / note_filename(canonical_title, sequence)
            while note_path.exists() or note_path.resolve() in reserved_paths:
                sequence += 1
                note_path = note_directory / note_filename(canonical_title, sequence)

        filename = note_path.name
        draft_path = job_dir / filename
        analysis_path = job_dir / "analysis.json"
        agent_work_dir = job_dir / "agent-work"
        agent_work_dir.mkdir(parents=True, exist_ok=True)
        workflow_paths = write_agent_work_templates(agent_work_dir) if settings.workflow_mode == "strict" else {}
        source_package = prepare_agent_source(source, description, agent_work_dir)
        resource_access_notices = detect_resource_access_notices(description, source)
        source_path = str(source.path.resolve()) if source.path is not None else None
        payload: dict[str, Any] = {
            "schema_version": JOB_SCHEMA_VERSION,
            "bvid": bvid,
            "canonical_url": canonical_url,
            "title": str(info.get("title") or "").strip(),
            "author": str(info.get("uploader") or "").strip(),
            "published": published,
            "duration": duration_text(info.get("duration")),
            "source_tags": [str(item) for item in (info.get("tags") or []) if str(item).strip()],
            "description": description,
            "description_status": status,
            "user_supplied_source": user_supplied_source,
            "uploader_pinned_comment": uploader_pinned_comment,
            "resource_access_notices": resource_access_notices,
            "source_mode": source.mode,
            "source_path": source_path,
            "source_manifest_path": source_package["manifest_path"],
            "source_package_mode": source_package["package_mode"],
            "source_chunk_count": source_package["chunk_count"],
            "source_timestamps_available": source_package["timestamps_available"],
            # Schema v1 compatibility aliases. New adapters consume source_* fields.
            "transcript_manifest_path": source_package["manifest_path"],
            "transcript_mode": source_package["package_mode"],
            "transcript_chunk_count": source_package["chunk_count"],
            **({"subtitle_path": source_path} if source.mode == SOURCE_MODE_SUBTITLE else {}),
            "canonical_title": canonical_title,
            "note_filename": filename,
            **filing,
            "note_path": str(note_path),
            "draft_path": str(draft_path),
            "analysis_path": str(analysis_path),
            "agent_work_dir": str(agent_work_dir),
            "workflow_mode": settings.workflow_mode,
            "operation_mode": operation_mode,
            **(
                {
                    "update_target_path": str(update_target_path),
                    "update_target_sha256": update_target_sha256,
                    "existing_note_snapshot_path": str(existing_note_snapshot_path),
                }
                if operation_mode == "update"
                else {}
            ),
            **workflow_paths,
        }
        (job_dir / "job.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        write_skeleton(draft_path, payload)
        write_analysis_template(analysis_path)
    return payload


def new_job_dir(settings: Settings, bvid: str) -> Path:
    settings.runtime_root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{bvid}-", dir=settings.runtime_root))


def _source_mode(payload: dict[str, Any]) -> str:
    if payload.get("source_mode"):
        return str(payload["source_mode"])
    if payload.get("transcript_source_type"):
        return str(payload["transcript_source_type"])
    return SOURCE_MODE_SUBTITLE


def _source_guidance(payload: dict[str, Any]) -> str:
    mode = _source_mode(payload)
    if mode == SOURCE_MODE_DESCRIPTION:
        return (
            "来源模式：`description_only`。这是用户当前消息明确指定的【纯资源分享】短记；"
            "source manifest 没有正文 chunk，事实只能来自 job 中的标题、元数据、UP 主简介和明确的用户补充来源。"
            "不要推断视频口播、画面参数或尚未提供的资源内容，正文按实际资料量保持简洁。"
        )
    if mode == SOURCE_MODE_ASR:
        return (
            "来源模式：`asr_text`。按 source manifest 顺序完整读取全部 source chunk；"
            "纯文本没有真实时间戳，不得制造时间定位。专名不确定时保留不确定性。"
        )
    return (
        "来源模式：`subtitle_srt`。按 source manifest 顺序完整读取全部 source chunk；"
        "SRT 的 cue 顺序和真实秒级时间定位已经保留。"
    )


def _operation_guidance(payload: dict[str, Any]) -> str:
    operation = str(payload.get("operation_mode") or "create")
    if operation == "update":
        return (
            "任务操作：`update`。先完整读取 `existing_note_snapshot_path`；以旧笔记为基线，"
            "合并当前新来源和用户补充内容，保留仍受来源支持的旧知识与人工修改。"
            "不要为了重新排版而缩短或删除旧笔记已有的高价值信息。"
        )
    if operation == "rerun":
        return "任务操作：`rerun`。用户已明确要求重新执行一次；这是独立新笔记，不覆盖已有笔记。"
    return "任务操作：`create`。这是首次生成。"


def _write_strict_handoff(job_dir: Path, payload: dict[str, Any]) -> Path:
    handoff = job_dir / "agent_handoff.md"
    guidance = _source_guidance(payload)
    operation_guidance = _operation_guidance(payload)
    handoff.write_text(
        "# B站视频转笔记任务\n\n"
        f"{guidance}\n\n{operation_guidance}\n\n"
        "1. 读取 `job.json`、`source_manifest_path`（旧 Job 使用 `transcript_manifest_path`）、`agent_work_dir`、`fact_ledger_path`、`semantic_draft_path`、`layout_plan_path` 与共享内容标准。manifest 会标明来源模式、chunk 和是否存在真实时间戳；只读取实际列出的 chunk，不自行重新切分。\n"
        "2. 判断当前来源、B站简介及明确存在的 `user_supplied_source` 是否足以支撑可信笔记，并填写 `analysis_path`。来源不足时不要编造正文。\n"
        "3. 长视频、百科型、参数密集或实测证据多的内容，先完成 Fact Ledger；简单短记可按规则标记 `not_applicable` 并填写原因。仍须保留参数、关系、条件、例外、冲突与实测证据。\n"
        "4. 完成 Semantic Draft 后再做 Layout Plan；排版只转换表达形式，不重新摘要或删减事实。\n"
        "5. 把短结论与完整正文写入 `draft_path` 的两个 AI 区域。正文只能使用当前 Job 允许的来源，并保留来源差异。\n"
        "6. 最终排版后重新对照 source manifest、阶段文件与正文，完成 `coverage_review`。\n"
        "7. 写完立即运行 finalizer；无论成功或失败都由 finalizer 接管 Job 生命周期。\n",
        encoding="utf-8",
    )
    return handoff


def _light_handoff_text(payload: dict[str, Any]) -> str:
    guidance = _source_guidance(payload)
    operation_guidance = _operation_guidance(payload)
    return (
        "# B站视频转笔记任务\n\n"
        "工作模式：`light`。不创建 Fact Ledger、Semantic Draft 或 Layout Plan。\n\n"
        f"{guidance}\n\n{operation_guidance}\n\n"
        "1. 读取 `job.json`、`source_manifest_path`（旧 Job 使用 `transcript_manifest_path`）和 `docs/standards/LIGHT-WORKFLOW.md`。按 manifest 完整读取实际存在的 source chunk，不自行重新切分或跳读。\n"
        "2. 判断当前来源、B站简介及明确存在的 `user_supplied_source` 是否足以支撑可信笔记，并填写 `analysis_path`。来源不足时停止，不用模型常识补参数、资源或结论。\n"
        "3. 直接在 `draft_path` 的两个 AI 区域写完整内容；优先保留参数、工具、步骤、条件、比较、兼容性、作者建议和实测结果。`description_only` 只写来源支持的纯资源分享短记。\n"
        "4. 内容完成后再做一次版式优化，不为了美化改写或删减知识。\n"
        "5. 最后回看当前来源，修正遗漏和无来源事实；将 `coverage_review.status` 设为 `passed` 并填写 notes。不要修改确定性区域。\n"
        "6. 写完立即运行 finalizer；无论成功或失败都由 finalizer 接管 Job 生命周期。\n"
    )


def write_handoff(job_dir: Path, payload: dict[str, Any]) -> Path:
    if payload.get("workflow_mode") != "light":
        return _write_strict_handoff(job_dir, payload)
    handoff = job_dir / "agent_handoff.md"
    handoff.write_text(_light_handoff_text(payload), encoding="utf-8")
    return handoff
