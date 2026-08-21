from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .config import DependencyError, Settings
from .note_template import note_filename, write_skeleton
from .quality import write_analysis_template
from .runtime import cleanup_job, waiting_file_lock
from .taxonomy import classify

MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4", ".webm", ".flv", ".m4s", ".part"}
STALE_SECONDS = 60 * 60
YTDLP_TIMEOUT_SECONDS = 180
JOB_SCHEMA_VERSION = 1
NOTE_NAME_LOCK = "note-names.lock"


def cleanup_stale_jobs(settings: Settings) -> int:
    if not settings.runtime_root.is_dir():
        return 0
    cutoff = time.time() - STALE_SECONDS
    removed = 0
    for child in settings.runtime_root.iterdir():
        if child.name == "locks":
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


def run_ytdlp(settings: Settings, job_dir: Path, canonical_url: str) -> None:
    ytdlp = settings.ytdlp.path
    if ytdlp is None:
        raise DependencyError("ytdlp_not_configured", "未找到 yt-dlp；请设置 BILI_LEARNING_YTDLP、config/local.json 或将 yt-dlp 加入 PATH。")
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
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "ai-zh,zh.*",
        "--sub-format",
        "srt",
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
        if not job_dir.is_dir() or job_dir.name == "locks":
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
    subtitle: Path,
    job_dir: Path,
    description_sidecar: str | None = None,
) -> dict[str, Any]:
    status, description = description_state(info, description_sidecar)
    if status == "failed":
        raise RuntimeError("无法确认 UP 主原始简介，任务已停止。")
    filing = classify(info, settings.taxonomy)
    canonical_title = " ".join(str(info.get("title") or "").split()) or "Bilibili 学习笔记"
    published = str(info.get("upload_date") or "")
    if len(published) == 8 and published.isdigit():
        published = f"{published[:4]}-{published[4:6]}-{published[6:]}"
    with waiting_file_lock(settings.runtime_root / "locks" / NOTE_NAME_LOCK):
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
            "subtitle_path": str(subtitle),
            "canonical_title": canonical_title,
            "note_filename": filename,
            **filing,
            "note_path": str(note_path),
            "draft_path": str(draft_path),
            "analysis_path": str(analysis_path),
        }
        (job_dir / "job.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        write_skeleton(draft_path, payload)
        write_analysis_template(analysis_path)
    return payload


def new_job_dir(settings: Settings, bvid: str) -> Path:
    settings.runtime_root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{bvid}-", dir=settings.runtime_root))


def write_handoff(job_dir: Path, payload: dict[str, Any]) -> Path:
    handoff = job_dir / "agent_handoff.md"
    handoff.write_text(
        "# B站视频转笔记任务\n\n"
        "1. 读取 `job.json`、`subtitle_path` 与共享内容标准。\n"
        "2. 先判断字幕与简介是否足以支撑可信学习笔记，并填写 runtime 的 `analysis_path`。来源不足时不要编造正文。\n"
        "3. 来源充分时，先在 `knowledge_outline` 中列出应保护的重要知识，再编辑 `draft_path`。不要改 Frontmatter、H1、视频简介、iframe、文件名、路径、tags、cssclasses 或 marker。\n"
        "4. 只填写两个 AI 区域：短的“先看结论”和根据视频内容动态组织的知识正文；不要强制套用步骤、坑点或实践清单。按共享标准根据知识关系选择 Table / Grid / Card / Risk / Resource / Chip，不为了好看强行卡片化。Grid 内的 Card 必须使用嵌套 Markdown：外层 `> [!grid-3]`，子卡片必须以 `> > [!card]` 开始，不能写成单层 `> [!card]`。\n"
        "5. 正文只使用字幕或原始简介支持的事实。参数、公式、限制、专名、比较、作者明确推荐、兼容性、资源等高价值信息不能仅为缩短篇幅而删除；有检索价值的同类成员和“原则 + 可直接使用值”也要避免二次压缩。\n"
        "6. 成稿后重新对照字幕/knowledge_outline 做覆盖复核；确认无重要遗漏和无来源外补写后，将 `coverage_review.status` 设为 `passed` 并填写 notes。\n"
        "7. 写完立即运行 finalizer；无论成功或失败都必须 finalizer 清理 job。\n",
        encoding="utf-8",
    )
    return handoff
