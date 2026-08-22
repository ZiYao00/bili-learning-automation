from __future__ import annotations

import json
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
from .config import load_settings
from .input_resolver import resolve_input
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
from .validator import validate_note

FAILSAFE_SECONDS = 2 * 60 * 60
STATUS_SCHEMA_VERSION = 1


def _status(payload: dict[str, Any], code: int = 0) -> tuple[dict[str, Any], int]:
    payload.setdefault("schema_version", STATUS_SCHEMA_VERSION)
    return payload, code


def _windowless_python() -> str:
    if sys.platform != "win32":
        return sys.executable
    for candidate in (Path(getattr(sys, "_base_executable", sys.executable)).with_name("pythonw.exe"), Path(sys.executable).with_name("pythonw.exe")):
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


def prepare_note(
    project_root: Path,
    message: str | None,
    *,
    dry_run: bool = False,
    cleanup_job_path: Path | None = None,
    after_seconds: int = FAILSAFE_SECONDS,
    cleanup_runner: Path | None = None,
) -> tuple[dict[str, Any], int]:
    settings = load_settings(project_root)
    if cleanup_job_path is not None:
        time.sleep(max(0, after_seconds))
        cleanup_job(settings.runtime_root, cleanup_job_path)
        return _status({"status": "temporary_data_removed"})
    if not message:
        return _status({"status": "failed", "message": "需要提供 B站复制链接、短链接或 BV 号。"}, 2)

    job_dir: Path | None = None
    reservation: Reservation | None = None
    ready = False
    try:
        settings.runtime_root.mkdir(parents=True, exist_ok=True)
        stale_removed = cleanup_stale_jobs(settings)
        resolved = resolve_input(message)
        reservation = claim_reservation(settings.runtime_root, resolved.bvid)
        if dry_run:
            return _status(
                {
                    "status": "ready_to_process",
                    "bvid": resolved.bvid,
                    "canonical_url": resolved.canonical_url,
                    "stale_jobs_removed": stale_removed,
                }
            )

        job_dir = new_job_dir(settings, resolved.bvid)
        bind_reservation(reservation, job_dir)
        run_ytdlp(settings, job_dir, resolved.canonical_url)
        if media_count(job_dir):
            raise RuntimeError("检测到媒体文件，已中止并清理临时任务。")
        info_files = list(job_dir.glob("*.info.json"))
        if len(info_files) != 1:
            raise RuntimeError("未取得唯一的视频元数据。")
        info = json.loads(info_files[0].read_text(encoding="utf-8"))
        description_files = list(job_dir.glob("*.description"))
        if len(description_files) > 1:
            raise RuntimeError("取得多个视频简介文件，无法确认原始简介。")
        description_sidecar = description_files[0].read_text(encoding="utf-8") if description_files else None
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
        job = create_job(
            settings,
            resolved.bvid,
            resolved.canonical_url,
            info,
            subtitle,
            job_dir,
            description_sidecar=description_sidecar,
        )
        handoff = write_handoff(job_dir, job)
        ready = True
        _schedule_failsafe_cleanup(job_dir, project_root, cleanup_runner)
        return _status(
            {
                "status": "materials_ready",
                "bvid": resolved.bvid,
                "canonical_url": resolved.canonical_url,
                "job_dir": str(job_dir),
                "handoff_path": str(handoff),
                "note_path": job["note_path"],
                "draft_path": job["draft_path"],
                "analysis_path": job["analysis_path"],
                "agent_work_dir": job["agent_work_dir"],
                "transcript_manifest_path": job["transcript_manifest_path"],
                "transcript_mode": job["transcript_mode"],
                "transcript_chunk_count": job["transcript_chunk_count"],
                "subtitle_path": str(subtitle),
                "description_status": job["description_status"],
                "media_files": 0,
                "stale_jobs_removed": stale_removed,
            }
        )
    except ReservationBusyError as error:
        return _status(
            {
                "status": "in_progress",
                "bvid": error.bvid,
                "message": "该视频已有活动任务，暂不重复处理。",
                "reservation_age_seconds": error.age_seconds,
                "job_dir": error.job_dir,
            },
            2,
        )
    except Exception as error:
        return _status({"status": "failed", "message": str(error)}, 1)
    finally:
        if job_dir and not ready:
            cleanup_job(settings.runtime_root, job_dir)
        elif reservation and not ready:
            release_reservation(settings.runtime_root, reservation.bvid)


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
                publish_validated_draft(note_path, Path(job["note_path"]))
                build_navigation(settings)
                payload = {"status": "note_ready", "note_path": job["note_path"]}
    except Exception as error:
        payload, code = {"status": "failed", "message": str(error)}, 1
    try:
        cleanup_job(settings.runtime_root, job_dir)
        payload["temporary_data_removed"] = True
    except Exception as error:
        payload["temporary_data_removed"] = False
        payload["cleanup_error"] = str(error)
        if code == 0:
            payload, code = {
                **payload,
                "status": "failed",
                "message": "笔记已写入但临时数据清理失败",
            }, 1
    return _status(payload, code)
