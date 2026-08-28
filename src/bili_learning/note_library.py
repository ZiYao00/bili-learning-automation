from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings

RESOURCE_COLLECTION_MARKER = "<!-- BILI_RESOURCE_COLLECTION -->"

_BVID_PATTERNS = (
    r"player\.html\?bvid=(BV[0-9A-Za-z]+)",
    r"bilibili\.com/video/(BV[0-9A-Za-z]+)",
    r"\b(BV[0-9A-Za-z]{8,})\b",
)


@dataclass(frozen=True)
class ExistingNote:
    path: Path
    bvid: str
    modified_at: str

    def as_dict(self) -> dict[str, str]:
        return {
            "path": str(self.path),
            "filename": self.path.name,
            "modified_at": self.modified_at,
        }


def extract_bvid(text: str) -> str | None:
    for pattern in _BVID_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def note_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _logical_path(settings: Settings, resolved: Path) -> Path:
    notes_root = settings.notes_root.resolve()
    return settings.notes_root / resolved.relative_to(notes_root)


def find_notes_by_bvid(settings: Settings, bvid: str) -> list[ExistingNote]:
    notes_root = settings.notes_root.resolve()
    navigation_root = (notes_root / settings.navigation_dir).resolve()
    matches: list[ExistingNote] = []
    if not notes_root.is_dir():
        return matches

    for candidate in notes_root.rglob("*.md"):
        resolved = candidate.resolve()
        if resolved == navigation_root or navigation_root in resolved.parents:
            continue
        try:
            text = resolved.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        # Resource collections deliberately aggregate many videos into one page.
        # They are not valid update targets for the normal one-video/one-note lifecycle.
        if RESOURCE_COLLECTION_MARKER in text:
            continue
        if extract_bvid(text) != bvid:
            continue
        modified = datetime.fromtimestamp(resolved.stat().st_mtime, tz=timezone.utc).isoformat()
        matches.append(ExistingNote(_logical_path(settings, resolved), bvid, modified))

    matches.sort(key=lambda item: str(item.path).lower())
    return matches


def validate_update_target(settings: Settings, bvid: str, target: Path) -> Path:
    resolved = target.expanduser().resolve()
    notes_root = settings.notes_root.resolve()
    navigation_root = (notes_root / settings.navigation_dir).resolve()
    if resolved == notes_root or notes_root not in resolved.parents or not resolved.is_file():
        raise ValueError("更新目标必须是 notes_root 内已存在的 Markdown 笔记")
    if resolved == navigation_root or navigation_root in resolved.parents:
        raise ValueError("导航文件不能作为更新目标")
    if resolved.suffix.lower() != ".md":
        raise ValueError("更新目标必须是 Markdown 笔记")
    text = resolved.read_text(encoding="utf-8-sig")
    if RESOURCE_COLLECTION_MARKER in text:
        raise ValueError("资源集合页不能作为普通 BVID 更新目标；请重新生成后在整理阶段更新资源卡")
    if extract_bvid(text) != bvid:
        raise ValueError("更新目标与当前 BVID 不一致")
    return _logical_path(settings, resolved)
