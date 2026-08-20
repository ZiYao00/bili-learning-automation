#!/usr/bin/env python3
"""Prepare a temporary, subtitle-first Bilibili note job without media download."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
YTDLP = Path(os.environ.get("BILI_LEARNING_YTDLP", r"G:\Program\yt-dlp\yt-dlp.exe"))
COOKIE_FILE = Path(os.environ.get("BILI_LEARNING_COOKIE_FILE", str(PROJECT_ROOT / "key" / "bilibili_cookies.txt")))
NOTES_DIR = PROJECT_ROOT / "notes" / "bilibili"
RUNTIME_ROOT = PROJECT_ROOT / ".runtime" / "bilibili-learning"
TAXONOMY = Path(os.environ.get("BILI_LEARNING_TAXONOMY", str(PROJECT_ROOT / "config" / "bilibili-note-taxonomy.json")))
MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4", ".webm", ".flv", ".m4s", ".part"}
STALE_SECONDS = 60 * 60
FAILSAFE_SECONDS = 20 * 60

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def emit(payload: dict[str, Any], code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def canonicalize(value: str) -> tuple[str, str]:
    match = re.search(r"\b(BV[0-9A-Za-z]{10})\b", value, re.IGNORECASE)
    if not match:
        raise ValueError("未识别到 Bilibili BVID；请发送复制后的 B站链接或 BV 号。")
    bvid = match.group(1)
    return bvid, f"https://www.bilibili.com/video/{bvid}/"


def safe_job_path(path: Path) -> Path:
    root = RUNTIME_ROOT.resolve()
    candidate = path.resolve()
    if candidate == root or root not in candidate.parents:
        raise ValueError("拒绝清理运行目录之外的路径。")
    return candidate


def remove_job(path: Path) -> None:
    candidate = safe_job_path(path)
    if candidate.exists() and not candidate.is_symlink():
        shutil.rmtree(candidate)


def cleanup_stale_jobs() -> int:
    if not RUNTIME_ROOT.is_dir():
        return 0
    cutoff = time.time() - STALE_SECONDS
    removed = 0
    for child in RUNTIME_ROOT.iterdir():
        if child.is_dir() and not child.is_symlink() and child.stat().st_mtime < cutoff:
            remove_job(child)
            removed += 1
    return removed


def windowless_python() -> str:
    """Resolve a console-free interpreter.

    On Windows a venv's python.exe/pythonw.exe may be a thin redirector (uv, py-launcher)
    that re-launches the base interpreter's python.exe without inheriting creation flags,
    which pops an empty console. Prefer the base interpreter's pythonw.exe via
    sys._base_executable, then fall back to a sibling pythonw.exe.
    """
    if sys.platform != "win32":
        return sys.executable
    candidates = []
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
        [windowless_python(), str(Path(__file__).resolve()), "--cleanup-job", str(job_dir), "--after-seconds", str(FAILSAFE_SECONDS)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=flags,
    )


def find_existing_note(canonical_url: str) -> Path | None:
    if not NOTES_DIR.is_dir():
        return None
    for note in NOTES_DIR.rglob("*.md"):
        try:
            if canonical_url in note.read_text(encoding="utf-8"):
                return note
        except OSError:
            continue
    return None


def safe_filename(title: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", title).strip().rstrip(".")
    return f"{name or 'Bilibili 学习笔记'}.md"


def classify(info: dict[str, Any]) -> dict[str, Any]:
    if not TAXONOMY.is_file():
        raise RuntimeError("未找到 B站笔记分类配置。")
    config = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    source = " ".join([str(info.get("title") or ""), str(info.get("description") or ""), *map(str, info.get("tags") or [])]).lower()
    model = next((item["canonical"] for item in config["models"] if any(alias.lower() in source for alias in item["aliases"])), None)
    route = next((item for item in config["routes"] if all(pattern.lower() in source for pattern in item.get("all_patterns", [])) and (not item.get("any_patterns") or any(pattern.lower() in source for pattern in item["any_patterns"]))), config["fallback"])
    task = route["task"]
    title = f"{model} {task}" if model else task
    required_tags = list(dict.fromkeys([*route["tags"], *( [model] if model else [])]))
    return {"category_path": route["path"], "canonical_title": title, "required_tags": required_tags}


def duration_text(seconds: float | int | None) -> str:
    if seconds is None:
        return "00:00"
    total = max(0, round(float(seconds)))
    minutes, second = divmod(total, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{second:02d}" if hours else f"{minute:02d}:{second:02d}"


def run_ytdlp(job_dir: Path, canonical_url: str) -> None:
    if not YTDLP.is_file():
        raise RuntimeError("yt-dlp 未安装在预期位置。")
    if not COOKIE_FILE.is_file():
        raise RuntimeError("Bilibili Cookie 文件不存在或未配置。")
    command = [
        str(YTDLP), "--ignore-config", "--no-cache-dir", "--cookies", str(COOKIE_FILE),
        "--skip-download", "--no-playlist", "--write-info-json", "--write-description",
        "--write-subs", "--write-auto-subs", "--sub-langs", "ai-zh,zh.*",
        "--sub-format", "srt/json/best", "--no-write-comments", "--windows-filenames",
        "--paths", str(job_dir), "--output", "%(id)s.%(ext)s", canonical_url,
    ]
    completed = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if completed.returncode:
        raise RuntimeError("yt-dlp 采集失败；请检查 Cookie 是否失效或链接是否可访问。")


def media_count(job_dir: Path) -> int:
    return sum(1 for path in job_dir.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES)


def select_subtitle(job_dir: Path) -> Path | None:
    candidates = list(job_dir.glob("*.ai-zh.srt")) + list(job_dir.glob("*.zh*.srt"))
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def write_handoff(job_dir: Path, bvid: str, canonical_url: str, info: dict[str, Any], subtitle: Path) -> Path:
    description = str(info.get("description") or "").strip()
    title = str(info.get("title") or "").strip()
    author = str(info.get("uploader") or "").strip()
    published = str(info.get("upload_date") or "")
    if len(published) == 8:
        published = f"{published[:4]}-{published[4:6]}-{published[6:]}"
    tags = [str(item) for item in (info.get("tags") or []) if str(item).strip()]
    filing = classify(info)
    note_path = NOTES_DIR.joinpath(*filing["category_path"]) / safe_filename(filing["canonical_title"])
    note_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bvid": bvid,
        "canonical_url": canonical_url,
        "title": title,
        "author": author,
        "published": published,
        "duration": duration_text(info.get("duration")),
        "tags": tags,
        "description": description,
        "description_available": bool(description),
        "subtitle_path": str(subtitle),
        **filing,
        "note_path": str(note_path),
    }
    (job_dir / "job.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    handoff = job_dir / "agent_handoff.md"
    handoff.write_text(
        "# Hermes B站学习笔记任务\n\n"
        "1. 读取 `job.json` 与其中的 `subtitle_path`。\n"
        "2. 按项目标准、分类规范和标准样例写入 `note_path`。\n"
        "3. 原始简介必须完整放在标题后、iframe 前；所有 URL 改为可点击 Markdown。若 `description_available` 为 false，写 `> 本视频未提供简介。`。\n"
        "4. 正文只使用字幕支持的内容；不要写机器资料路径或证据编号。\n"
        "5. H1、文件名与路径必须分别等于 `canonical_title`、`canonical_title.md`、`note_path`；tags 必须包含 `required_tags`。\n"
        "6. 写完立刻运行 `finalize_ytdlp_bilibili_note.py --job <job_dir> --note <note_path>`；无论成败都必须运行。\n",
        encoding="utf-8",
    )
    return handoff


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", nargs="?", help="Bilibili URL or text containing a BV id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cleanup-job", type=Path)
    parser.add_argument("--after-seconds", type=int, default=FAILSAFE_SECONDS)
    args = parser.parse_args()
    if args.cleanup_job:
        time.sleep(max(0, args.after_seconds))
        remove_job(args.cleanup_job)
        return
    if not args.message:
        parser.error("需要提供 B站链接、BV 号或 --cleanup-job")
    job_dir: Path | None = None
    try:
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        stale_removed = cleanup_stale_jobs()
        bvid, canonical_url = canonicalize(args.message)
        existing = find_existing_note(canonical_url)
        if existing:
            emit({"status": "already_exists", "bvid": bvid, "note_path": str(existing), "stale_jobs_removed": stale_removed})
        if args.dry_run:
            emit({"status": "ready_to_process", "bvid": bvid, "canonical_url": canonical_url, "stale_jobs_removed": stale_removed})
        job_dir = Path(tempfile.mkdtemp(prefix=f"{bvid}-", dir=RUNTIME_ROOT))
        run_ytdlp(job_dir, canonical_url)
        if media_count(job_dir):
            raise RuntimeError("检测到媒体文件，已中止并清理临时任务。")
        info_files = list(job_dir.glob("*.info.json"))
        if len(info_files) != 1:
            raise RuntimeError("未取得唯一的视频元数据。")
        info = json.loads(info_files[0].read_text(encoding="utf-8"))
        subtitle = select_subtitle(job_dir)
        if not subtitle:
            emit({"status": "subtitle_unavailable", "bvid": bvid, "message": "未取得 ai-zh 或 zh 字幕；默认流程未下载音频或视频。"}, 2)
        handoff = write_handoff(job_dir, bvid, canonical_url, info, subtitle)
        schedule_failsafe_cleanup(job_dir)
        emit({
            "status": "materials_ready", "bvid": bvid, "canonical_url": canonical_url,
            "job_dir": str(job_dir), "handoff_path": str(handoff),
            "note_path": str(json.loads((job_dir / "job.json").read_text(encoding="utf-8"))["note_path"]),
            "subtitle_path": str(subtitle), "media_files": 0, "stale_jobs_removed": stale_removed,
        })
    except SystemExit:
        raise
    except Exception as error:
        emit({"status": "failed", "message": str(error)}, 1)
    finally:
        # A ready job is kept only while Hermes writes the note; finalization removes it.
        if job_dir and not (job_dir / "agent_handoff.md").exists():
            remove_job(job_dir)


if __name__ == "__main__":
    main()
