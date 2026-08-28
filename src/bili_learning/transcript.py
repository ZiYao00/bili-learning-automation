from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .source import SOURCE_MODE_ASR, SOURCE_MODE_DESCRIPTION, SOURCE_MODE_SUBTITLE, SourceMaterial

DIRECT_MAX_CHARS = 18_000
CHUNK_TARGET_CHARS = 24_000
MIN_TAIL_CHARS = 2_000
_TIMECODE_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)
_TEXT_SENTENCE_RE = re.compile(r"(?<=[。！？!?；;])\s*|\n+")


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


def _split_oversized_text_segment(segment: str, max_chars: int) -> list[str]:
    if len(segment) <= max_chars:
        return [segment]
    return [segment[index : index + max_chars] for index in range(0, len(segment), max_chars)]


def _parse_plain_text_segments(text: str, *, segment_max_chars: int) -> list[dict[str, str | None]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    raw_segments = [segment.strip() for segment in _TEXT_SENTENCE_RE.split(normalized) if segment.strip()]
    segments: list[dict[str, str | None]] = []
    for raw in raw_segments:
        for piece in _split_oversized_text_segment(raw, segment_max_chars):
            body = piece.strip()
            if body:
                segments.append({"start": None, "end": None, "text": body, "line": body})
    return segments


def _chunk_segments(
    segments: list[dict[str, str | None]], target_chars: int
) -> list[list[dict[str, str | None]]]:
    if target_chars < 1:
        raise ValueError("target_chars 必须大于 0")
    chunks: list[list[dict[str, str | None]]] = []
    current: list[dict[str, str | None]] = []
    current_chars = 0
    for segment in segments:
        line = str(segment["line"])
        line_chars = len(line) + 1
        if current and current_chars + line_chars > target_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(segment)
        current_chars += line_chars
    if current:
        chunks.append(current)
    return chunks


def _group_chars(group: list[dict[str, str | None]]) -> int:
    return sum(len(str(segment["line"])) + 1 for segment in group)


def _merge_tiny_tail(
    groups: list[list[dict[str, str | None]]],
    *,
    chunk_max_chars: int,
    min_tail_chars: int = MIN_TAIL_CHARS,
) -> list[list[dict[str, str | None]]]:
    if len(groups) < 2 or _group_chars(groups[-1]) >= min_tail_chars:
        return groups
    if _group_chars(groups[-2]) + _group_chars(groups[-1]) > chunk_max_chars + min_tail_chars:
        return groups
    return [*groups[:-2], [*groups[-2], *groups[-1]]]


def _write_source_package(
    source: SourceMaterial,
    source_text: str,
    segments: list[dict[str, str | None]],
    agent_work_dir: Path,
    *,
    timestamps_available: bool,
    direct_max_chars: int,
    chunk_target_chars: int,
) -> dict[str, Any]:
    agent_work_dir.mkdir(parents=True, exist_ok=True)
    compact_text = "\n".join(str(segment["line"]) for segment in segments)
    if compact_text:
        compact_text += "\n"

    if not segments:
        package_mode = "none"
        effective_target_chars = 0
        groups: list[list[dict[str, str | None]]] = []
    elif len(compact_text) <= direct_max_chars:
        package_mode = "direct"
        effective_target_chars = len(compact_text)
        groups = [segments]
    else:
        package_mode = "chunked"
        planned_chunks = max(2, (len(compact_text) + chunk_target_chars - 1) // chunk_target_chars)
        effective_target_chars = (len(compact_text) + planned_chunks - 1) // planned_chunks
        groups = _chunk_segments(segments, effective_target_chars)
        groups = _merge_tiny_tail(groups, chunk_max_chars=chunk_target_chars)

    chunks: list[dict[str, Any]] = []
    if groups:
        source_dir = agent_work_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        for index, group in enumerate(groups, start=1):
            chunk_text = "\n".join(str(segment["line"]) for segment in group) + "\n"
            chunk_path = source_dir / f"source-{index:02d}.txt"
            chunk_path.write_text(chunk_text, encoding="utf-8")
            chunks.append(
                {
                    "index": index,
                    "path": str(chunk_path),
                    "start": group[0].get("start"),
                    "end": group[-1].get("end"),
                    "segment_count": len(group),
                    "cue_count": len(group),
                    "chars": len(chunk_text),
                }
            )

    source_path = source.path.resolve() if source.path is not None else None
    source_bytes = source_path.stat().st_size if source_path is not None else len(source_text.encode("utf-8"))
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "source_mode": source.mode,
        "source_location": "job.description" if source.mode == SOURCE_MODE_DESCRIPTION else "runtime_file",
        "package_mode": package_mode,
        # Schema v1 compatibility aliases.
        "source_type": source.mode,
        "mode": package_mode,
        "timestamps_available": timestamps_available,
        "source_path": str(source_path) if source_path is not None else None,
        "source_bytes": source_bytes,
        "source_chars": len(source_text),
        "compact_chars": len(compact_text),
        "segment_count": len(segments),
        "cue_count": len(segments),
        "chunk_max_chars": chunk_target_chars,
        "chunk_target_chars": effective_target_chars,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "rules": {
            "semantic_summary": False,
            "text_order_preserved": True,
            "cue_boundaries_preserved": source.mode == SOURCE_MODE_SUBTITLE,
            "timestamps_fabricated": False,
        },
    }
    manifest_path = agent_work_dir / "source-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**manifest, "manifest_path": str(manifest_path)}


def prepare_agent_source(
    source: SourceMaterial,
    description: str,
    agent_work_dir: Path,
    *,
    direct_max_chars: int = DIRECT_MAX_CHARS,
    chunk_target_chars: int = CHUNK_TARGET_CHARS,
) -> dict[str, Any]:
    """Create one deterministic source package for every supported source mode."""

    if source.mode == SOURCE_MODE_SUBTITLE:
        assert source.path is not None
        source_text = source.path.read_text(encoding="utf-8", errors="replace")
        segments = _parse_srt_blocks(source_text)
        if not segments:
            raise ValueError("字幕无法解析为可读 SRT cue。")
        timestamps_available = True
    elif source.mode == SOURCE_MODE_ASR:
        assert source.path is not None
        source_text = source.path.read_text(encoding="utf-8", errors="replace")
        segments = _parse_plain_text_segments(source_text, segment_max_chars=chunk_target_chars)
        if not segments:
            raise ValueError("ASR transcript 为空或不可读。")
        timestamps_available = False
    else:
        source_text = description
        segments = []
        timestamps_available = False

    return _write_source_package(
        source,
        source_text,
        segments,
        agent_work_dir,
        timestamps_available=timestamps_available,
        direct_max_chars=direct_max_chars,
        chunk_target_chars=chunk_target_chars,
    )


def prepare_agent_transcript(
    subtitle_path: Path,
    agent_work_dir: Path,
    *,
    direct_max_chars: int = DIRECT_MAX_CHARS,
    chunk_target_chars: int = CHUNK_TARGET_CHARS,
) -> dict[str, Any]:
    """Backward-compatible wrapper for SRT source packaging."""

    return prepare_agent_source(
        SourceMaterial(SOURCE_MODE_SUBTITLE, subtitle_path),
        "",
        agent_work_dir,
        direct_max_chars=direct_max_chars,
        chunk_target_chars=chunk_target_chars,
    )


def prepare_agent_text_transcript(
    transcript_path: Path,
    agent_work_dir: Path,
    *,
    direct_max_chars: int = DIRECT_MAX_CHARS,
    chunk_target_chars: int = CHUNK_TARGET_CHARS,
) -> dict[str, Any]:
    """Backward-compatible wrapper for timestamp-free ASR source packaging."""

    return prepare_agent_source(
        SourceMaterial(SOURCE_MODE_ASR, transcript_path),
        "",
        agent_work_dir,
        direct_max_chars=direct_max_chars,
        chunk_target_chars=chunk_target_chars,
    )
