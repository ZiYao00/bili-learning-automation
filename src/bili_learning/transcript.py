from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DIRECT_MAX_CHARS = 18_000
CHUNK_TARGET_CHARS = 24_000
_TIMECODE_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


def _compact_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    return value[:8]


def _parse_srt_blocks(text: str) -> list[dict[str, str | None]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n+", normalized.strip()) if normalized.strip() else []
    cues: list[dict[str, str | None]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0].isdigit():
            lines = lines[1:]
        if not lines:
            continue
        start: str | None = None
        end: str | None = None
        match = _TIMECODE_RE.match(lines[0])
        if match:
            start = _compact_timestamp(match.group("start"))
            end = _compact_timestamp(match.group("end"))
            lines = lines[1:]
        body = " ".join(lines).strip()
        if not body:
            continue
        prefix = f"[{start}] " if start else ""
        cues.append({"start": start, "end": end, "text": body, "line": f"{prefix}{body}"})
    return cues


def _chunk_cues(cues: list[dict[str, str | None]], target_chars: int) -> list[list[dict[str, str | None]]]:
    if target_chars < 1:
        raise ValueError("target_chars 必须大于 0")
    chunks: list[list[dict[str, str | None]]] = []
    current: list[dict[str, str | None]] = []
    current_chars = 0
    for cue in cues:
        line = str(cue["line"])
        line_chars = len(line) + 1
        if current and current_chars + line_chars > target_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(cue)
        current_chars += line_chars
    if current:
        chunks.append(current)
    return chunks


def prepare_agent_transcript(
    subtitle_path: Path,
    agent_work_dir: Path,
    *,
    direct_max_chars: int = DIRECT_MAX_CHARS,
    chunk_target_chars: int = CHUNK_TARGET_CHARS,
) -> dict[str, Any]:
    """Create a deterministic, runtime-only transcript package for the agent.

    The transformation removes SRT numbering, millisecond precision and blank
    lines, but preserves subtitle text, cue order and cue boundaries. It never
    summarizes or semantically filters the source.
    """

    source = subtitle_path.read_text(encoding="utf-8", errors="replace")
    cues = _parse_srt_blocks(source)
    if not cues:
        raise ValueError("字幕无法解析为可读 SRT cue。")

    agent_work_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir = agent_work_dir / "transcript"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    compact_text = "\n".join(str(cue["line"]) for cue in cues) + "\n"
    mode = "direct" if len(compact_text) <= direct_max_chars else "chunked"
    if mode == "direct":
        effective_target_chars = len(compact_text)
        groups = [cues]
    else:
        planned_chunks = max(2, (len(compact_text) + chunk_target_chars - 1) // chunk_target_chars)
        effective_target_chars = (len(compact_text) + planned_chunks - 1) // planned_chunks
        groups = _chunk_cues(cues, effective_target_chars)

    chunks: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        chunk_text = "\n".join(str(cue["line"]) for cue in group) + "\n"
        chunk_path = transcript_dir / f"transcript-{index:02d}.txt"
        chunk_path.write_text(chunk_text, encoding="utf-8")
        chunks.append(
            {
                "index": index,
                "path": str(chunk_path),
                "start": group[0].get("start"),
                "end": group[-1].get("end"),
                "cue_count": len(group),
                "chars": len(chunk_text),
            }
        )

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "mode": mode,
        "source_path": str(subtitle_path),
        "source_bytes": subtitle_path.stat().st_size,
        "source_chars": len(source),
        "compact_chars": len(compact_text),
        "cue_count": len(cues),
        "chunk_max_chars": chunk_target_chars,
        "chunk_target_chars": effective_target_chars,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "rules": {
            "semantic_summary": False,
            "text_order_preserved": True,
            "cue_boundaries_preserved": True,
        },
    }
    manifest_path = agent_work_dir / "transcript-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**manifest, "manifest_path": str(manifest_path)}
