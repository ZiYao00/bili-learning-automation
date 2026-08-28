from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .collector import (
    cleanup_stale_jobs,
    create_job,
    media_count,
    new_job_dir,
    run_ytdlp,
    select_subtitle,
    write_handoff,
)
from .config import DependencyError, load_settings
from .doctor import onboarding_report
from .input_resolver import extract_user_supplied_source, resolve_input
from .navigation import build_navigation
from .publisher import publish_validated_draft
from .quality import load_analysis_report, validate_analysis_report
from .runtime import (
    Reservation,
    ReservationBusyError,
    bind_reservation,
    claim_reservation,
    cleanup_job,
    release_reservation,
    safe_job_path,
)
from .source import (
    SOURCE_MODE_ASR,
    SOURCE_MODE_DESCRIPTION,
    SOURCE_MODE_SUBTITLE,
    SOURCE_MODES,
    SourceMaterial,
)
from .validator import validate_note

FAILSAFE_SECONDS = 2 * 60 * 60
STATUS_SCHEMA_VERSION = 1


def _status(payload: dict[str, Any], code: int = 0) -> tuple[dict[str, Any], int]:
    payload.setdefault("schema_version", STATUS_SCHEMA_VERSION)
    return payload, code


def _windowless_python() -> str:
    if sys.platform != "win32":
        return sys.executable
    for candidate in (
        Path(getattr(sys, "_base_executable", sys.executable)).with_name("pythonw.exe"),
        Path(sys.executable).with_name("pythonw.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _schedule_failsafe_cleanup(job_dir: Path, project_root: Path, runner: Path | None) -> None:
    flags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    if runner is not None:
        command = [
            _windowless_python(),
            str(runner),
            "--cleanup-job",
            str(job_dir),
            "--after-seconds",
            str(FAILSAFE_SECONDS),
        ]
    else:
        command = [
            _windowless_python(),
            "-m",
            "bili_learning.cli",
            "--project-root",
            str(project_root),
            "prepare",
            "--cleanup-job",
            str(job_dir),
            "--after-seconds",
            str(FAILSAFE_SECONDS),
        ]
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=flags,
    )


def _job_source_mode(job: dict[str, Any]) -> str:
    if job.get("source_mode"):
        return str(job["source_mode"])
    if job.get("transcript_source_type"):
        return str(job["transcript_source_type"])
    return SOURCE_MODE_SUBTITLE


def _job_source_path(job: dict[str, Any]) -> str | None:
    value = job.get("source_path") or job.get("transcript_source_path") or job.get("subtitle_path")
    return str(value) if value else None


def _job_source_manifest_path(job: dict[str, Any]) -> str | None:
    value = job.get("source_manifest_path") or job.get("transcript_manifest_path")
    return str(value) if value else None


def _job_source_package_mode(job: dict[str, Any]) -> str | None:
    value = job.get("source_package_mode") or job.get("transcript_mode")
    return str(value) if value else None


def _job_source_chunk_count(job: dict[str, Any]) -> int | None:
    value = job.get("source_chunk_count")
    if value is None:
        value = job.get("transcript_chunk_count")
    return int(value) if isinstance(value, int) else None


def _job_source_timestamps_available(job: dict[str, Any]) -> bool:
    value = job.get("source_timestamps_available")
    if isinstance(value, bool):
        return value
    return _job_source_mode(job) == SOURCE_MODE_SUBTITLE


def _materials_payload(job_dir: Path, job: dict[str, Any], handoff: Path, *, recovered: bool) -> dict[str, Any]:
    source_manifest_path = _job_source_manifest_path(job)
    source_package_mode = _job_source_package_mode(job)
    source_chunk_count = _job_source_chunk_count(job)
    if source_manifest_path is None or source_package_mode is None or source_chunk_count is None:
        raise ValueError("Job 缺少完整 source package 契约")

    payload: dict[str, Any] = {
        "status": "materials_ready",
        "bvid": job["bvid"],
        "canonical_url": job["canonical_url"],
        "job_dir": str(job_dir),
        "handoff_path": str(handoff),
        "note_path": job["note_path"],
        "draft_path": job["draft_path"],
        "analysis_path": job["analysis_path"],
        "agent_work_dir": job["agent_work_dir"],
        "workflow_mode": job["workflow_mode"],
        **{
            key: job[key]
            for key in ("fact_ledger_path", "semantic_draft_path", "layout_plan_path")
            if key in job
        },
        "source_mode": _job_source_mode(job),
        "source_path": _job_source_path(job),
        "source_manifest_path": source_manifest_path,
        "source_package_mode": source_package_mode,
        "source_chunk_count": source_chunk_count,
        "source_timestamps_available": _job_source_timestamps_available(job),
        # Schema v1 compatibility aliases for already-installed adapters.
        "transcript_manifest_path": source_manifest_path,
        "transcript_mode": source_package_mode,
        "transcript_chunk_count": source_chunk_count,
        "transcript_source_type": _job_source_mode(job),
        "transcript_source_path": _job_source_path(job),
        "asr_fallback_used": _job_source_mode(job) == SOURCE_MODE_ASR,
        "description_status": job["description_status"],
        "media_files": 0,
    }
    if job.get("subtitle_path"):
        payload["subtitle_path"] = job["subtitle_path"]
    if recovered:
        payload["recovered"] = True
    return payload


def _manifest_files_complete(manifest_path: Path) -> bool:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    chunks = manifest.get("chunks") if isinstance(manifest, dict) else None
    if not isinstance(chunks, list):
        return False
    for chunk in chunks:
        if not isinstance(chunk, dict) or not chunk.get("path"):
            return False
        if not Path(str(chunk["path"])).is_file():
            return False
    return True


def _recover_materials_ready(
    project_root: Path,
    job_dir: Path,
    *,
    cleanup_runner: Path | None,
    expected_source_mode: str | None = None,
) -> tuple[dict[str, Any], int] | None:
    try:
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(job, dict):
        return None

    required_keys = (
        "bvid",
        "canonical_url",
        "note_path",
        "draft_path",
        "analysis_path",
        "agent_work_dir",
        "workflow_mode",
        "description_status",
    )
    if any(key not in job or job[key] in (None, "") for key in required_keys):
        return None

    source_mode = _job_source_mode(job)
    if expected_source_mode is not None and source_mode != expected_source_mode:
        return None
    source_manifest = _job_source_manifest_path(job)
    source_package_mode = _job_source_package_mode(job)
    source_chunk_count = _job_source_chunk_count(job)
    if source_manifest is None or source_package_mode is None or source_chunk_count is None:
        return None

    required_files = [
        Path(str(job["draft_path"])),
        Path(str(job["analysis_path"])),
        Path(source_manifest),
    ]
    source_path = _job_source_path(job)
    if source_mode in {SOURCE_MODE_SUBTITLE, SOURCE_MODE_ASR}:
        if source_path is None:
            return None
        required_files.append(Path(source_path))
    if any(not path.is_file() for path in required_files):
        return None
    if not _manifest_files_complete(Path(source_manifest)):
        return None

    handoff = job_dir / "agent_handoff.md"
    if not handoff.is_file():
        handoff = write_handoff(job_dir, job)
    _schedule_failsafe_cleanup(job_dir, project_root, cleanup_runner)
    payload = _materials_payload(job_dir, job, handoff, recovered=True)
    payload["stale_jobs_removed"] = 0
    return _status(payload)


def _load_collected_metadata(job_dir: Path) -> tuple[dict[str, Any], str | None]:
    info_files = list(job_dir.glob("*.info.json"))
    if len(info_files) != 1:
        raise RuntimeError("未取得唯一的视频元数据。")
    info = json.loads(info_files[0].read_text(encoding="utf-8"))
    description_files = list(job_dir.glob("*.description"))
    if len(description_files) > 1:
        raise RuntimeError("取得多个视频简介文件，无法确认原始简介。")
    description_sidecar = description_files[0].read_text(encoding="utf-8") if description_files else None
    return info, description_sidecar


def _prepare_materials(
    project_root: Path,
    message: str | None,
    *,
    source_mode: str,
    source_path: Path | None = None,
    dry_run: bool = False,
    cleanup_runner: Path | None = None,
) -> tuple[dict[str, Any], int]:
    settings = load_settings(project_root)
    if source_mode not in SOURCE_MODES:
        return _status({"status": "failed", "message": f"不支持的 source_mode：{source_mode}"}, 2)
    if not message:
        return _status({"status": "failed", "message": "需要提供 B站复制链接、短链接或 BV 号。"}, 2)
    if dry_run and source_mode != SOURCE_MODE_SUBTITLE:
        return _status({"status": "failed", "message": "dry-run 仅适用于默认字幕流程。"}, 2)

    if not dry_run:
        onboarding = onboarding_report(settings)
        if onboarding["status"] == "action_required":
            return _status(
                {
                    "status": "onboarding_required",
                    "message": "首次使用环境尚未准备完成；请先处理必需配置，再重试原链接。",
                    "actions": onboarding["actions"],
                    "warnings": onboarding["warnings"],
                },
                2,
            )
    if settings.notes_is_fallback and not dry_run:
        return _status(
            {
                "status": "configuration_required",
                "message": "尚未配置 Obsidian Vault；为避免把私人笔记长期写进代码仓库，本次未启动采集。",
                "temporary_notes_root": str(settings.notes_root),
                "config_path": str(settings.local_config_path),
                "required": "vault_root",
            },
            2,
        )

    external_source = source_path.expanduser().resolve() if source_path is not None else None
    job_dir: Path | None = None
    reservation: Reservation | None = None
    ready = False
    try:
        settings.runtime_root.mkdir(parents=True, exist_ok=True)
        stale_removed = cleanup_stale_jobs(settings)
        resolved = resolve_input(message)
        reservation = claim_reservation(settings.runtime_root, resolved.bvid)
        if dry_run:
            release_reservation(settings.runtime_root, reservation.bvid)
            ready = True
            return _status(
                {
                    "status": "ready_to_process",
                    "bvid": resolved.bvid,
                    "canonical_url": resolved.canonical_url,
                    "source_mode": source_mode,
                    "stale_jobs_removed": stale_removed,
                }
            )

        if source_mode == SOURCE_MODE_ASR and (
            external_source is None or not external_source.is_file() or external_source.stat().st_size == 0
        ):
            raise RuntimeError("ASR transcript 不存在或为空。")

        job_dir = new_job_dir(settings, resolved.bvid)
        bind_reservation(reservation, job_dir)
        run_ytdlp(
            settings,
            job_dir,
            resolved.canonical_url,
            include_subtitles=source_mode == SOURCE_MODE_SUBTITLE,
        )
        if media_count(job_dir):
            raise RuntimeError("检测到媒体文件，已中止并清理临时任务。")
        info, description_sidecar = _load_collected_metadata(job_dir)

        if source_mode == SOURCE_MODE_SUBTITLE:
            subtitle = select_subtitle(job_dir)
            if not subtitle:
                return _status(
                    {
                        "status": "subtitle_unavailable",
                        "bvid": resolved.bvid,
                        "message": "未取得 ai-zh 或 zh 字幕；默认流程未下载音频或视频。",
                    },
                    2,
                )
            source = SourceMaterial(SOURCE_MODE_SUBTITLE, subtitle)
        elif source_mode == SOURCE_MODE_ASR:
            assert external_source is not None
            runtime_source = job_dir / "asr-transcript.txt"
            shutil.copyfile(external_source, runtime_source)
            source = SourceMaterial(SOURCE_MODE_ASR, runtime_source)
        else:
            source = SourceMaterial(SOURCE_MODE_DESCRIPTION)

        job = create_job(
            settings,
            resolved.bvid,
            resolved.canonical_url,
            info,
            source,
            job_dir,
            description_sidecar=description_sidecar,
            user_supplied_source=extract_user_supplied_source(message),
        )
        handoff = write_handoff(job_dir, job)
        ready = True
        _schedule_failsafe_cleanup(job_dir, project_root, cleanup_runner)
        payload = _materials_payload(job_dir, job, handoff, recovered=False)
        payload["stale_jobs_removed"] = stale_removed
        return _status(payload)
    except DependencyError as error:
        return _status({"status": "failed", "code": error.code, "message": str(error)}, 1)
    except ReservationBusyError as error:
        if error.recoverable and error.job_dir:
            recovered = _recover_materials_ready(
                project_root,
                Path(error.job_dir),
                cleanup_runner=cleanup_runner,
                expected_source_mode=source_mode,
            )
            if recovered is not None:
                return recovered
        return _status(
            {
                "status": "in_progress",
                "bvid": error.bvid,
                "message": "该视频已有活动任务，暂不重复处理。",
                "requested_source_mode": source_mode,
                "reservation_age_seconds": error.age_seconds,
                "job_dir": error.job_dir,
            },
            2,
        )
    except Exception as error:
        return _status({"status": "failed", "message": str(error)}, 1)
    finally:
        if job_dir and not ready:
            try:
                cleanup_job(settings.runtime_root, job_dir)
            except Exception:
                pass
        elif reservation and not ready:
            try:
                release_reservation(settings.runtime_root, reservation.bvid)
            except Exception:
                pass


def prepare_note(
    project_root: Path,
    message: str | None,
    *,
    dry_run: bool = False,
    cleanup_job_path: Path | None = None,
    after_seconds: int = FAILSAFE_SECONDS,
    cleanup_runner: Path | None = None,
) -> tuple[dict[str, Any], int]:
    if cleanup_job_path is not None:
        settings = load_settings(project_root)
        time.sleep(max(0, after_seconds))
        retired = cleanup_job(settings.runtime_root, cleanup_job_path)
        return _status(
            {
                "status": "temporary_data_retired",
                "retired_path": str(retired) if retired else None,
            }
        )
    return _prepare_materials(
        project_root,
        message,
        source_mode=SOURCE_MODE_SUBTITLE,
        dry_run=dry_run,
        cleanup_runner=cleanup_runner,
    )


def prepare_transcript_note(
    project_root: Path,
    message: str | None,
    transcript_path: Path,
    *,
    cleanup_runner: Path | None = None,
) -> tuple[dict[str, Any], int]:
    return _prepare_materials(
        project_root,
        message,
        source_mode=SOURCE_MODE_ASR,
        source_path=transcript_path,
        cleanup_runner=cleanup_runner,
    )


def prepare_description_note(
    project_root: Path,
    message: str | None,
    *,
    cleanup_runner: Path | None = None,
) -> tuple[dict[str, Any], int]:
    return _prepare_materials(
        project_root,
        message,
        source_mode=SOURCE_MODE_DESCRIPTION,
        cleanup_runner=cleanup_runner,
    )


def finalize_note(project_root: Path, job_path: Path, note_path: Path) -> tuple[dict[str, Any], int]:
    settings = load_settings(project_root)
    job_dir = safe_job_path(settings.runtime_root, job_path)
    payload: dict[str, Any] = {}
    code = 0
    try:
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        report = load_analysis_report(Path(job["analysis_path"]))
        report_errors = validate_analysis_report(report)
        source_status = report.get("source_assessment", {}).get("status")
        if source_status == "insufficient" and not report_errors:
            payload, code = {
                "status": "source_insufficient",
                "message": report["source_assessment"]["reason"],
            }, 2
        else:
            errors = validate_note(note_path, job)
            if errors:
                payload, code = {"status": "note_invalid", "message": "；".join(errors)}, 2
            else:
                published_now = publish_validated_draft(
                    note_path,
                    Path(job["note_path"]),
                    allow_existing_identical=True,
                )
                build_navigation(settings)
                payload = {
                    "status": "note_ready",
                    "note_path": job["note_path"],
                    "publish_state": "published" if published_now else "already_published",
                }
    except Exception as error:
        payload, code = {"status": "failed", "message": str(error)}, 1
    try:
        retired = cleanup_job(settings.runtime_root, job_dir)
        payload["temporary_data_retired"] = True
        payload["retired_path"] = str(retired) if retired else None
        payload["temporary_data_removed"] = False
    except Exception as error:
        payload["temporary_data_retired"] = False
        payload["temporary_data_removed"] = False
        payload["cleanup_warning"] = str(error)
    return _status(payload, code)
