"""Explicit duplicate BVID inventory and opt-in, recoverable recycle-bin cleanup."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .config import Settings
from .navigation import atomic_write, build_navigation
from .note_library import RESOURCE_COLLECTION_MARKER, extract_bvid, find_notes_by_bvid, note_sha256
from .organize_safety import affected_backlinks, note_within_root, recycle_file
from .organizer import organizer_lock

_BVID = re.compile(r"^BV[0-9A-Za-z]{8,}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")


def duplicates_inventory(settings: Settings, bvid: str) -> dict[str, Any]:
    if not _BVID.fullmatch(bvid):
        raise ValueError("无效 BVID")
    notes = find_notes_by_bvid(settings, bvid)
    root = settings.notes_root.resolve()
    return {
        "schema_version": 1,
        "status": "duplicates_inventory",
        "bvid": bvid,
        "note_count": len(notes),
        "notes": [
            {"path": p.path.resolve().relative_to(root).as_posix(), "sha256": note_sha256(p.path)}
            for p in notes
        ],
    }


def _validate_plan_path(settings: Settings, plan_path: Path) -> Path:
    plan = plan_path.expanduser().resolve()
    runtime = (settings.runtime_root / "organize-plans").resolve()
    if runtime not in plan.parents or plan.suffix.lower() != ".json" or not plan.is_file():
        raise ValueError("重复清理计划必须存放在 runtime/organize-plans 下")
    return plan


def _validate_item(settings: Settings, raw: object, *, bvid: str) -> tuple[Path, str, str]:
    if not isinstance(raw, dict):
        raise ValueError("重复清理的文件项必须包含 path 与 sha256")
    name, expected = raw.get("path"), raw.get("sha256")
    if not isinstance(name, str) or not isinstance(expected, str) or not _SHA.fullmatch(expected):
        raise ValueError("重复清理文件项必须有相对路径与 SHA-256")
    if "\\" in name or not name or any(not p or p in {".", ".."} or ":" in p for p in name.split("/")):
        raise ValueError("重复清理仅允许 notes_root 内的相对路径")
    root = settings.notes_root.resolve()
    p = root.joinpath(*name.split("/"))
    if root not in p.resolve(strict=False).parents or p.suffix.lower() != ".md":
        raise ValueError("重复清理文件路径超出 notes_root 或不是 Markdown")
    if p.is_file() and RESOURCE_COLLECTION_MARKER in p.read_text(encoding="utf-8-sig"):
        raise ValueError("资源集合页不能作为重复版本清理目标或保留对象")
    return p, expected, name


def recycle_duplicates(settings: Settings, plan_path: Path, *, apply: bool = False) -> dict[str, Any]:
    plan = _validate_plan_path(settings, plan_path)
    data = json.loads(plan.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("重复清理计划需要 schema_version=1")
    bvid = data.get("bvid")
    if not isinstance(bvid, str) or not _BVID.fullmatch(bvid):
        raise ValueError("重复清理计划必须指定有效的 BVID")
    keep, keep_hash, keep_name = _validate_item(settings, data.get("keep"), bvid=bvid)
    items = data.get("recycle")
    if not isinstance(items, list) or not items or len(items) > 100:
        raise ValueError("必须逐文件显式指定要回收的 1 至 100 篇重复笔记")
    targets = [_validate_item(settings, item, bvid=bvid) for item in items]
    names = [item[2].casefold() for item in targets]
    if len(names) != len(set(names)) or keep_name.casefold() in names:
        raise ValueError("不能重复列出回收目标或将保留文件列为回收对象")

    identity = hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:24]
    checkpoint = settings.runtime_root / "organize-duplicate-runs" / (identity + ".json")
    records: dict[str, str] = {}
    if checkpoint.is_file():
        previous = json.loads(checkpoint.read_text(encoding="utf-8"))
        if previous.get("identifier") != identity or not isinstance(previous.get("items"), dict):
            raise ValueError("重复清理恢复记录不一致")
        records = {str(k): str(v) for k, v in previous["items"].items()}

    def save() -> None:
        atomic_write(
            checkpoint,
            json.dumps({"schema_version": 1, "identifier": identity, "items": records}, ensure_ascii=False, indent=2) + "\n",
        )

    def checked_keep() -> None:
        note_within_root(settings, keep)
        if note_sha256(keep) != keep_hash or extract_bvid(keep.read_text(encoding="utf-8-sig")) != bvid:
            raise ValueError("保留版本已发生变化或 BVID 不一致；停止清理")

    checked_keep()
    results: list[dict[str, str]] = []
    navigation = "not_requested"
    with organizer_lock(settings):
        for target, expected, name in targets:
            checked_keep()
            item = {"path": name, "status": "ready"}
            if not target.is_file():
                if records.get(name) == "recycled":
                    item["status"] = "already_recycled"
                elif records.get(name) == "started":
                    item.update(status="blocked", reason="recycle_outcome_unknown_check_recycle_bin")
                else:
                    item.update(status="blocked", reason="missing_unverified_file")
            else:
                try:
                    note_within_root(settings, target)
                    if note_sha256(target) != expected or extract_bvid(target.read_text(encoding="utf-8-sig")) != bvid:
                        raise ValueError("待回收版本内容已变化或 BVID 不一致")
                    links = affected_backlinks(settings, target, keep)
                    if links:
                        raise ValueError("其他笔记仍引用此文件：" + "; ".join(links[:5]))
                except (OSError, ValueError, UnicodeError) as error:
                    item.update(status="blocked", reason=str(error))
            if apply and item["status"] == "ready":
                try:
                    # Write intent BEFORE the recycle operation. A crash must never
                    # silently cause a second uncertain destructive attempt.
                    records[name] = "started"
                    save()
                    recycle_file(target)
                    records[name] = "recycled"
                    save()
                    item["status"] = "recycled"
                except (OSError, ValueError) as error:
                    item.update(status="blocked", reason=str(error))
            results.append(item)
            if apply and item["status"] == "blocked":
                # Stop, do not retry paid/unsafe/destructive actions implicitly.
                break

        if apply:
            try:
                build_navigation(settings)
                navigation = "refreshed"
            except (OSError, ValueError, TimeoutError) as error:
                navigation = f"needs_refresh: {error}"

    blocked = sum(item["status"] == "blocked" for item in results)
    return {
        "schema_version": 1,
        "status": "duplicates_preview" if not apply else (
            "duplicates_recycled" if blocked == 0 and len(results) == len(targets) and navigation == "refreshed" else "partial"
        ),
        "applied": apply,
        "bvid": bvid,
        "keep": keep_name,
        "count": len(targets),
        "navigation": navigation,
        "results": results,
    }
