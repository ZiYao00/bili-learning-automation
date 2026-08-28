from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .note_library import note_sha256
from .note_template import strip_ai_markers


class UpdateConflictError(RuntimeError):
    pass


def publish_validated_draft(
    draft_path: Path,
    note_path: Path,
    *,
    allow_existing_identical: bool = False,
) -> bool:
    """Atomically expose a validated draft without replacing different content.

    Returns True when this call creates the note. When retry-safe mode is
    enabled, an identical existing note returns False instead of failing.

    The publish staging file lives beside the runtime draft and is intentionally
    retained with the job. This avoids making successful publication depend on
    unlink/delete permissions in sandboxed agent environments.
    """
    if not draft_path.is_file():
        raise FileNotFoundError(f"草稿文件不存在：{draft_path}")

    published_text = strip_ai_markers(draft_path.read_text(encoding="utf-8"))
    if note_path.exists():
        if allow_existing_identical and note_path.read_text(encoding="utf-8") == published_text:
            return False
        raise FileExistsError(f"目标笔记已存在，拒绝覆盖：{note_path}")

    note_path.parent.mkdir(parents=True, exist_ok=True)
    staging = draft_path.with_name("published-note.md")
    staging.write_text(published_text, encoding="utf-8", newline="\n")
    os.link(staging, note_path)
    return True


def publish_validated_update(draft_path: Path, note_path: Path, *, expected_sha256: str) -> None:
    """Replace one explicitly selected existing note after a hash conflict check."""

    if not draft_path.is_file():
        raise FileNotFoundError(f"草稿文件不存在：{draft_path}")
    if not note_path.is_file():
        raise UpdateConflictError(f"更新目标已不存在：{note_path}")
    if note_sha256(note_path) != expected_sha256:
        raise UpdateConflictError("目标笔记在本次更新期间已被修改，未覆盖现有文件。")

    published_text = strip_ai_markers(draft_path.read_text(encoding="utf-8"))
    note_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staging_name = tempfile.mkstemp(prefix=f".{note_path.stem}.update-", suffix=".md", dir=note_path.parent)
    staging = Path(staging_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(published_text)
        if note_sha256(note_path) != expected_sha256:
            raise UpdateConflictError("目标笔记在本次更新期间已被修改，未覆盖现有文件。")
        os.replace(staging, note_path)
    finally:
        if staging.exists():
            try:
                staging.unlink()
            except OSError:
                pass
