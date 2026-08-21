from __future__ import annotations

import os
import uuid
from pathlib import Path

from .note_template import strip_ai_markers


def publish_validated_draft(draft_path: Path, note_path: Path) -> None:
    """Atomically expose a validated draft without replacing an existing note.

    A temporary file is created beside the final note.  The final path is then
    created as a hard link, which is an atomic no-overwrite operation on the
    local NTFS volumes used by this Windows workflow.  The runtime draft is
    intentionally retained until the caller's normal job cleanup runs.
    """
    if not draft_path.is_file():
        raise FileNotFoundError(f"草稿文件不存在：{draft_path}")
    if note_path.exists():
        raise FileExistsError(f"目标笔记已存在，拒绝覆盖：{note_path}")

    note_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = note_path.with_name(f".{note_path.name}.{uuid.uuid4().hex}.publishing")
    try:
        temporary.write_text(strip_ai_markers(draft_path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
        os.link(temporary, note_path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
