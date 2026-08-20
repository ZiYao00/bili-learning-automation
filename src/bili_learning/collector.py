from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .config import Settings
from .note_template import note_filename, write_skeleton
from .runtime import remove_job
from .taxonomy import classify

MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4", ".webm", ".flv", ".m4s", ".part"}
STALE_SECONDS = 60 * 60
YTDLP_TIMEOUT_SECONDS = 180


def find_existing_note(notes_root: Path, canonical_url: str) -> Path | None:
    if not notes_root.is_dir():
        return None
    for note in notes_root.rglob("*.md"):
        try:
            if canonical_url in note.read_text(encoding="utf-8"):
                return note
        except OSError:
            continue
    return None


def cleanup_stale_jobs(settings: Settings) -> int:
    if not settings.runtime_root.is_dir():
        return 0
    cutoff = time.time() - STALE_SECONDS
    removed = 0
    for child in settings.runtime_root.iterdir():
        if child.name == "locks":
            continue
        if child.is_dir() and not child.is_symlink() and child.stat().st_mtime < cutoff:
            remove_job(settings.runtime_root, child)
            removed += 1
    return removed


def duration_text(seconds: float | int | None) -> str:
    if seconds is None:
        return "00:00"
    total = max(0, round(float(seconds)))
    minutes, second = divmod(total, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{second:02d}" if hours else f"{minute:02d}:{second:02d}"


def run_ytdlp(settings: Settings, job_dir: Path, canonical_url: str) -> None:
    if settings.ytdlp is None or not settings.ytdlp.is_file():
        raise RuntimeError("未找到 yt-dlp；请设置 BILI_LEARNING_YTDLP 或将 yt-dlp 加入 PATH。")
    if not settings.cookie_file.is_file():
        raise RuntimeError("Bilibili Cookie 文件不存在或未配置。")
    command = [
        str(settings.ytdlp),
        "--ignore-config",
        "--no-cache-dir",
        "--cookies",
        str(settings.cookie_file),
        "--skip-download",
        "--no-playlist",
        "--write-info-json",
        "--write-description",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "ai-zh,zh.*",
        "--sub-format",
        "srt/json/best",
        "--no-write-comments",
        "--windows-filenames",
        "--paths",
        str(job_dir),
        "--output",
        "%(id)s.%(ext)s",
        canonical_url,
    ]
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
    candidates = list(job_dir.glob("*.ai-zh.srt")) + list(job_dir.glob("*.zh*.srt"))
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def description_state(info: dict[str, Any]) -> tuple[str, str]:
    if "description" not in info:
        return "failed", ""
    raw = info["description"]
    if raw is None:
        return "confirmed_empty", ""
    if not isinstance(raw, str):
        return "failed", ""
    text = raw.strip()
    return ("present", text) if text else ("confirmed_empty", "")


def create_job(
    settings: Settings,
    bvid: str,
    canonical_url: str,
    info: dict[str, Any],
    subtitle: Path,
    job_dir: Path,
) -> dict[str, Any]:
    status, description = description_state(info)
    if status == "failed":
        raise RuntimeError("无法确认 UP 主原始简介，任务已停止。")
    filing = classify(info, settings.taxonomy)
    note_path = settings.notes_root.joinpath(*filing["category_path"]) / note_filename(
        filing["canonical_title"], bvid
    )
    if note_path.exists():
        text = note_path.read_text(encoding="utf-8", errors="replace")
        if canonical_url not in text:
            raise FileExistsError(f"目标笔记路径已被其他视频占用，拒绝覆盖：{note_path}")
    published = str(info.get("upload_date") or "")
    if len(published) == 8 and published.isdigit():
        published = f"{published[:4]}-{published[4:6]}-{published[6:]}"
    payload: dict[str, Any] = {
        "bvid": bvid,
        "canonical_url": canonical_url,
        "title": str(info.get("title") or "").strip(),
        "author": str(info.get("uploader") or "").strip(),
        "published": published,
        "duration": duration_text(info.get("duration")),
        "source_tags": [str(item) for item in (info.get("tags") or []) if str(item).strip()],
        "description": description,
        "description_status": status,
        "subtitle_path": str(subtitle),
        **filing,
        "note_path": str(note_path),
    }
    (job_dir / "job.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_skeleton(note_path, payload)
    return payload


def new_job_dir(settings: Settings, bvid: str) -> Path:
    settings.runtime_root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{bvid}-", dir=settings.runtime_root))


def write_handoff(job_dir: Path, payload: dict[str, Any]) -> Path:
    handoff = job_dir / "agent_handoff.md"
    handoff.write_text(
        "# Hermes B站视频转笔记任务\n\n"
        "1. 读取 `job.json` 与 `subtitle_path`。\n"
        "2. `note_path` 已由程序生成确定性骨架；不要改 Frontmatter、H1、视频简介、iframe、路径或 tags。\n"
        "3. 只在四组 `BILI_AI_*_START/END` marker 内填写：先看结论、怎么做、容易踩坑、我来实践。\n"
        "4. 正文只使用字幕或原始简介支持的内容，不写临时路径、证据编号或采集细节。\n"
        "5. 写完立刻运行 finalizer；无论写作成功或失败都必须 finalizer 清理 job。\n",
        encoding="utf-8",
    )
    return handoff
