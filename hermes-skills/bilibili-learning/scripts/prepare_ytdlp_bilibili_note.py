#!/usr/bin/env python3
"""Prepare a subtitle-first Bilibili note job without downloading media."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bili_learning.collector import (  # noqa: E402
    cleanup_stale_jobs,
    create_job,
    find_existing_note,
    media_count,
    new_job_dir,
    run_ytdlp,
    select_subtitle,
    write_handoff,
)
from bili_learning.config import load_settings  # noqa: E402
from bili_learning.input_resolver import resolve_input  # noqa: E402
from bili_learning.note_template import PLACEHOLDER_TEXT  # noqa: E402
from bili_learning.runtime import file_lock, remove_job  # noqa: E402

FAILSAFE_SECONDS = 20 * 60

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def emit(payload: dict[str, Any], code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def windowless_python() -> str:
    if sys.platform != "win32":
        return sys.executable
    candidates: list[Path] = []
    base = getattr(sys, "_base_executable", None)
    if base:
        candidates.append(Path(base).with_name("pythonw.exe"))
    candidates.append(Path(sys.executable).with_name("pythonw.exe"))
    for candidate in candidates:
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError:
            continue
    return sys.executable


def schedule_failsafe_cleanup(job_dir: Path) -> None:
    flags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    subprocess.Popen(
        [
            windowless_python(),
            str(Path(__file__).resolve()),
            "--cleanup-job",
            str(job_dir),
            "--after-seconds",
            str(FAILSAFE_SECONDS),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=flags,
    )


def existing_status(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "already_exists"
    return "incomplete_note" if PLACEHOLDER_TEXT in text else "already_exists"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", nargs="?", help="Bilibili copied link, short link, or BV id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cleanup-job", type=Path)
    parser.add_argument("--after-seconds", type=int, default=FAILSAFE_SECONDS)
    args = parser.parse_args()
    runtime_root = PROJECT_ROOT / ".runtime" / "bilibili-learning"

    if args.cleanup_job:
        time.sleep(max(0, args.after_seconds))
        remove_job(runtime_root, args.cleanup_job)
        return
    if not args.message:
        parser.error("需要提供 B站复制链接、短链接、BV 号或 --cleanup-job")

    settings = load_settings(PROJECT_ROOT)
    job_dir: Path | None = None
    ready = False
    try:
        settings.runtime_root.mkdir(parents=True, exist_ok=True)
        stale_removed = cleanup_stale_jobs(settings)
        resolved = resolve_input(args.message)
        lock_path = settings.runtime_root / "locks" / f"{resolved.bvid}.lock"

        with file_lock(lock_path):
            existing = find_existing_note(settings.notes_root, resolved.canonical_url)
            if existing:
                status = existing_status(existing)
                emit(
                    {
                        "status": status,
                        "bvid": resolved.bvid,
                        "note_path": str(existing),
                        "message": (
                            "已存在尚未完成的程序骨架，请先处理该笔记。"
                            if status == "incomplete_note"
                            else "该视频已存在笔记。"
                        ),
                        "stale_jobs_removed": stale_removed,
                    },
                    2 if status == "incomplete_note" else 0,
                )
            if args.dry_run:
                emit(
                    {
                        "status": "ready_to_process",
                        "bvid": resolved.bvid,
                        "canonical_url": resolved.canonical_url,
                        "stale_jobs_removed": stale_removed,
                    }
                )

            job_dir = new_job_dir(settings, resolved.bvid)
            run_ytdlp(settings, job_dir, resolved.canonical_url)
            if media_count(job_dir):
                raise RuntimeError("检测到媒体文件，已中止并清理临时任务。")
            info_files = list(job_dir.glob("*.info.json"))
            if len(info_files) != 1:
                raise RuntimeError("未取得唯一的视频元数据。")
            info = json.loads(info_files[0].read_text(encoding="utf-8"))
            subtitle = select_subtitle(job_dir)
            if not subtitle:
                emit(
                    {
                        "status": "subtitle_unavailable",
                        "bvid": resolved.bvid,
                        "message": "未取得 ai-zh 或 zh 字幕；默认流程未下载音频或视频。",
                    },
                    2,
                )

            payload = create_job(
                settings,
                resolved.bvid,
                resolved.canonical_url,
                info,
                subtitle,
                job_dir,
            )
            handoff = write_handoff(job_dir, payload)
            ready = True
            schedule_failsafe_cleanup(job_dir)
            emit(
                {
                    "status": "materials_ready",
                    "bvid": resolved.bvid,
                    "canonical_url": resolved.canonical_url,
                    "job_dir": str(job_dir),
                    "handoff_path": str(handoff),
                    "note_path": payload["note_path"],
                    "subtitle_path": str(subtitle),
                    "description_status": payload["description_status"],
                    "media_files": 0,
                    "stale_jobs_removed": stale_removed,
                }
            )
    except SystemExit:
        raise
    except Exception as error:
        emit({"status": "failed", "message": str(error)}, 1)
    finally:
        if job_dir and not ready:
            remove_job(settings.runtime_root, job_dir)


if __name__ == "__main__":
    main()
