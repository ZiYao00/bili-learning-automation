from __future__ import annotations

import os
import uuid
from pathlib import Path

from .note_template import strip_ai_markers


def publish_validated_draft(
    draft_path: Path,
    note_path: Path,
    *,
    allow_existing_identical: bool = False,
) -> bool:
    """Atomically expose a validated draft without replacing different content.

    Returns True when this call creates the note. When retry-safe mode is
    enabled, an identical existing note returns False instead of failing.
    """
    if not draft_path.is_file():
        raise FileNotFoundError(f"草稿文件不存在：{draft_path}")

    published_text = strip_ai_markers(draft_path.read_text(encoding="utf-8"))
    if note_path.exists():
        if allow_existing_identical and note_path.read_text(encoding="utf-8") == published_text:
            return False
        raise FileExistsError(f"目标笔记已存在，拒绝覆盖：{note_path}")

    note_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = note_path.with_name(f".{note_path.name}.{uuid.uuid4().hex}.publishing")
    try:
        temporary.write_text(published_text, encoding="utf-8", newline="\n")
        os.link(temporary, note_path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return True
