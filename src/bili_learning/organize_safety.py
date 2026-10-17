"""Non-destructive organizer checks and Windows-only recycle-bin operations.

File content and titles are never modified by these helpers.
"""
from __future__ import annotations

import ctypes
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from .config import Settings

_WIKI_LINK = re.compile(r"!?\[\[([^\]\r\n]+)\]\]")
_MD_LINK = re.compile(r"(?<!!)\]\(([^)]+)\)")


def note_within_root(settings: Settings, path: Path) -> Path:
    """Resolve an existing note, rejecting junctions/symlinks outside notes_root."""
    root = settings.notes_root.resolve()
    if path.is_symlink():
        raise ValueError("不允许操作符号链接文件")
    resolved = path.expanduser().resolve()
    navigation = (root / settings.navigation_dir).resolve()
    if (
        not resolved.is_file()
        or resolved.suffix.lower() != ".md"
        or root not in resolved.parents
        or resolved == navigation
        or navigation in resolved.parents
    ):
        raise ValueError("笔记必须是 notes_root 内的现有 Markdown 文件，且不能是导航文件")
    return resolved


def safe_target_directory(settings: Settings, relative_parts: tuple[str, ...]) -> Path:
    root = settings.notes_root.resolve()
    directory = root.joinpath(*relative_parts)
    resolved = directory.resolve(strict=False)
    if root not in resolved.parents or resolved == root:
        raise ValueError("目标目录经 Junction/符号链接解析后超出 notes_root")
    return resolved


def affected_backlinks(settings: Settings, source: Path, destination: Path) -> list[str]:
    """Conservatively report references that can break when a note is moved.

    Only inspect notes_root, never the rest of the user's Vault. Generated navigation
    pages are excluded because they will be rebuilt. Unqualified wiki links remain
    valid if their basename is globally unique and the filename is unchanged.
    """
    root = settings.notes_root.resolve()
    source = source.resolve()
    destination = destination.resolve(strict=False)
    if source == destination:
        return []
    try:
        original = source.relative_to(root).with_suffix("").as_posix().casefold()
    except ValueError as error:
        raise ValueError("来源不在 notes_root") from error
    stem = source.stem.casefold()
    is_name_preserved = source.name == destination.name
    navigation = (root / settings.navigation_dir).resolve()
    candidates: list[Path] = []
    risks: list[str] = []
    for note in root.rglob("*.md"):
        resolved = note.resolve()
        if navigation in resolved.parents or resolved == source:
            continue
        if note.is_symlink() or root not in resolved.parents:
            # Never read through an unexpected link into another workspace.
            risks.append(f"{note.relative_to(root).as_posix()}:unsafe_link")
            continue
        candidates.append(resolved)
    same_stem = sum(1 for p in [source, *candidates] if p.stem.casefold() == stem)
    for note in candidates:
        try:
            data = note.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            # Fail closed: a note we cannot read might reference this path.
            risks.append(f"{note.relative_to(root).as_posix()}:unreadable")
            continue
        for wiki in _WIKI_LINK.findall(data):
            target = unquote(wiki.split("|", 1)[0].split("#", 1)[0].strip()).replace("\\", "/")
            if not target:
                continue
            target = target.removesuffix(".md").lstrip("/")
            qualified = "/" in target
            normalized = target.casefold()
            if (qualified and (normalized == original or original.endswith("/" + normalized))) or (
                not qualified and normalized == stem and (not is_name_preserved or same_stem != 1)
            ):
                risks.append(f"{note.relative_to(root).as_posix()}:wikilink:{target}")
                break
        else:
            for url in _MD_LINK.findall(data):
                path = unquote(url.split("#", 1)[0].strip().strip("<>"))
                if "://" in path or not path.lower().endswith(".md"):
                    continue
                try:
                    resolved_link = (note.parent / path).resolve(strict=False)
                except (OSError, ValueError):
                    continue
                if resolved_link == source:
                    risks.append(f"{note.relative_to(root).as_posix()}:markdown:{path}")
                    break
    return sorted(set(risks))


def recycle_file(path: Path) -> None:
    """Send exactly one verified file to the Windows Recycle Bin.

    Never fall back to unlink / permanent deletion, even on unsupported hosts.
    """
    if path.is_symlink():
        raise ValueError("回收站操作禁止作用于符号链接")
    path = path.resolve()
    if not path.is_file():
        raise ValueError("回收站操作仅接受现有普通文件")
    if sys.platform != "win32":
        raise OSError("只有 Windows 系统回收站可用；不允许退化为永久删除")

    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", ctypes.c_uint),
            ("pFrom", ctypes.c_wchar_p),
            ("pTo", ctypes.c_wchar_p),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", ctypes.c_wchar_p),
        ]

    # FO_DELETE + FOF_ALLOWUNDO + no dialog/confirmation; any failure is fatal.
    source_buffer = ctypes.create_unicode_buffer(str(path) + "\0\0")
    operation = SHFILEOPSTRUCTW()
    operation.wFunc = 0x0003
    operation.pFrom = ctypes.cast(source_buffer, ctypes.c_wchar_p)
    operation.fFlags = 0x0040 | 0x0010 | 0x0004 | 0x0400
    shell = ctypes.windll.shell32
    shell.SHFileOperationW.argtypes = [ctypes.POINTER(SHFILEOPSTRUCTW)]
    shell.SHFileOperationW.restype = ctypes.c_int
    code = shell.SHFileOperationW(ctypes.byref(operation))
    if code or operation.fAnyOperationsAborted or path.exists():
        raise OSError(f"移入 Windows 回收站失败（code={code}，aborted={operation.fAnyOperationsAborted}）")
