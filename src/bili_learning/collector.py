from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .config import YTDLP_INSTALL_URL, YTDLP_WINDOWS_INSTALL_COMMAND, DependencyError, Settings
from .note_template import note_filename, write_skeleton
from .quality import write_analysis_template
from .resource_access import detect_resource_access_notices
from .runtime import cleanup_job, waiting_file_lock
from .taxonomy import classify
from .transcript import prepare_agent_transcript
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


def run_ytdlp(settings: Settings, job_dir: Path, canonical_url: str) -> None:
    ytdlp = settings.ytdlp.path
    if ytdlp is None:
        raise DependencyError(
            "ytdlp_not_configured",
            "未检测到 yt-dlp；项目不会自动安装或内置可执行文件。"
            f"Windows 推荐先运行 `{YTDLP_WINDOWS_INSTALL_COMMAND}`，安装后重新执行；"
            f"官方安装说明：{YTDLP_INSTALL_URL}。"
            "只有使用自定义位置时，才需要设置 BILI_LEARNING_YTDLP 或 config/local.json 的 ytdlp。",
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
    subtitle: Path,
    job_dir: Path,
    description_sidecar: str | None = None,
    user_supplied_source: dict[str, str] | None = None,
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
        agent_work_dir = job_dir / "agent-work"
        agent_work_dir.mkdir(parents=True, exist_ok=True)
        workflow_paths = write_agent_work_templates(agent_work_dir) if settings.workflow_mode == "strict" else {}
        transcript = prepare_agent_transcript(subtitle, agent_work_dir)
        resource_access_notices = detect_resource_access_notices(description, subtitle)
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
            "resource_access_notices": resource_access_notices,
            "subtitle_path": str(subtitle),
            "canonical_title": canonical_title,
            "note_filename": filename,
            **filing,
            "note_path": str(note_path),
            "draft_path": str(draft_path),
            "analysis_path": str(analysis_path),
            "agent_work_dir": str(agent_work_dir),
            "workflow_mode": settings.workflow_mode,
            **workflow_paths,
            "transcript_manifest_path": transcript["manifest_path"],
            "transcript_mode": transcript["mode"],
            "transcript_chunk_count": transcript["chunk_count"],
        }
        (job_dir / "job.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        write_skeleton(draft_path, payload)
        write_analysis_template(analysis_path)
    return payload


def new_job_dir(settings: Settings, bvid: str) -> Path:
    settings.runtime_root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{bvid}-", dir=settings.runtime_root))


def _write_strict_handoff(job_dir: Path, payload: dict[str, Any]) -> Path:
    handoff = job_dir / "agent_handoff.md"
    handoff.write_text(
        "# B站视频转笔记任务\n\n"
        "1. 先读取 `job.json`、`transcript_manifest_path`、`agent_work_dir`、`fact_ledger_path`、`semantic_draft_path`、`layout_plan_path` 与共享内容标准；知识密集型任务还必须读取 `docs/standards/KNOWLEDGE-DENSE-WORKFLOW.md`。manifest 的 `chunks` 已按 cue 完整边界生成；`direct` 读取唯一 transcript，`chunked` 按 manifest 顺序逐块阅读，不要再把原始 SRT 整份塞入上下文。\n"
        "2. 先判断字幕、B站采集简介以及 job 中明确存在的 `user_supplied_source` 是否足以支撑可信学习笔记，并填写 runtime 的 `analysis_path`。用户补充来源必须与 B站简介分开保留 provenance；两者冲突时标记冲突，不静默覆盖或猜测。来源不足时不要编造正文。\n"
        "3. 长视频、百科型、参数密集或实测证据多的内容，必须先完成 `fact_ledger_path`：按 manifest 顺序记录原子事实，显式保留具体成员、数值/上下限、版本、A/B 关系、来源/继承、适用条件、例外、冲突、兼容性、作者评价，以及“配置 → 耗时 / 质量 / 失败表现”的证据链。`knowledge_outline` 只是 Fact Ledger 的上层索引，不是事实清单或最终目录；不得先压成几个主题名。普通短视频可将 Fact Ledger 的 `workflow_status` 标记为 `not_applicable`，但必须填写 `workflow_reason`；其余情况完成后标记为 `complete`。仍不得用模型常识补全。\n"
        "4. Fact Ledger 完成后，先在 `semantic_draft_path` 写内容完成稿；本阶段不要编辑最终 `draft_path`。Semantic Draft 先用普通 Markdown 自然聚类事实，不为卡片数量或页面简洁删知识；章节数量只改变事实如何分组，不改变事实保留预算。一个 H2 可以通过 H3、表格和列表承载很多事实。内容稿完成后把 Semantic Draft 的 `workflow_status` 标记为 `complete`。不要改 Frontmatter、H1、播放器与来源区、资源获取提示、iframe、文件名、路径、tags、cssclasses 或 marker。\n"
        "5. Semantic Draft 内容完成后才进入 `layout_plan_path` 与 Layout Pass：只把现有关系转换成 Table / Grid / Card / Risk / Meta / Resource / Chip / Metric，不重新摘要或选择事实。整页只保留一个最高优先级 Summary；Grid 内 Card 必须使用嵌套 `> > [!card]`。排版计划完成并确认事实无损后，把 Layout Plan 的 `workflow_status` 标记为 `complete`，再把短结论与完整正文写入 `draft_path` 的两个 AI 区域。正文只能使用字幕、B站采集简介或明确标注的 `user_supplied_source` 支持的事实，并保留来源差异；外部知识除非用户明确要求，否则不得并入。\n"
        "6. 最终排版后重新按 manifest 顺序抽查/复读原 transcript，并同时对照 Fact Ledger、Semantic Draft 与最终正文。重点检查：章节减少时事实是否也被误删；成员是否只剩类别；关系是否只剩名称；原则是否丢了可直接使用值；推荐区间是否丢了例外；实测是否还保留配置、耗时与结果；Layout Pass 前后的事实是否一致。发现遗漏先修正文，再将 `coverage_review.status` 设为 `passed` 并填写 notes。\n"
        "7. 写完立即运行 finalizer；无论成功或失败都由 finalizer 接管 job 的 retire/维护生命周期。\n",
        encoding="utf-8",
    )
    return handoff


def _light_handoff_text() -> str:
    return (
        "# B站视频转笔记任务\n\n"
        "工作模式：`light`。本任务优先让模型完整理解字幕并自然写作，不创建 Fact Ledger、Semantic Draft 或 Layout Plan。\n\n"
        "1. 读取 `job.json`、`transcript_manifest_path` 和 `docs/standards/LIGHT-WORKFLOW.md`。按 manifest 顺序完整读完所有 transcript chunk；不要自行重新切分，也不要跳读。\n"
        "2. 判断字幕、B站采集简介以及 job 中明确存在的 `user_supplied_source` 是否足以支撑可信笔记，并填写 `analysis_path`。用户补充来源必须与 B站简介分开保留 provenance；两者冲突时标记冲突，不静默覆盖或猜测。来源不足时停止，不要用模型常识补具体参数、资源或结论。\n"
        "3. 直接在 `draft_path` 的两个 AI 区域写一篇完整、实用、适合长期查询的笔记。优先保留参数、数值、工具、模型、步骤、条件、比较、兼容性、作者建议和实测结果；章节数量由内容自然决定，不要为了简短主动压缩有价值信息。\n"
        "4. 内容写完整后，再独立做一次版式优化。此时可按需读取 `docs/OBSIDIAN-STYLING.md`，或只查看 `STANDARD-VIDEO-NOTE-EXAMPLE.md` 中与当前关系匹配的局部写法。适度使用表格、列表、Grid / Card、Risk、Meta、Chip 或 Metric；不要求使用任何组件，也不要为了美化改写或删减知识。\n"
        "5. 最后回看 transcript，修正明显遗漏和无来源事实；再将 `coverage_review.status` 设为 `passed` 并填写简短 notes。不要修改 Frontmatter、H1、播放器与来源区、资源、文件名、路径、tags、cssclasses 或 marker。\n"
        "6. 写完立即运行 finalizer；无论成功或失败都由 finalizer 接管 job 的 retire/维护生命周期。\n"
    )


def write_handoff(job_dir: Path, payload: dict[str, Any]) -> Path:
    if payload.get("workflow_mode") != "light":
        return _write_strict_handoff(job_dir, payload)
    handoff = job_dir / "agent_handoff.md"
    handoff.write_text(_light_handoff_text(), encoding="utf-8")
    return handoff
