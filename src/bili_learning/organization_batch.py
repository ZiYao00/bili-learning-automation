"""Agent-reviewed organization plans, byte-preserving batch moves and resumable checkpoints.

No LLM classification happens in this module. An Agent must read each note and
supply its chosen destination in an explicit manifest under runtime/organize-plans.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .config import Settings
from .navigation import atomic_write, build_navigation
from .note_library import extract_bvid, find_notes_by_bvid, note_sha256
from .organize_safety import affected_backlinks, note_within_root, safe_target_directory
from .organizer import _validated_destination, organize_note
from .runtime import waiting_file_lock

_HASH = re.compile(r"^[0-9a-f]{64}$")
PLAN_LIMIT = 500


def _relpath(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("计划路径必须使用 notes_root 下的 POSIX 相对路径")
    parts = value.split("/")
    if any(not p or p in {".", ".."} or ":" in p for p in parts):
        raise ValueError("计划包含不安全的路径组件")
    return tuple(parts)


def list_inbox(settings: Settings, scope: str, note: Path | None = None) -> dict[str, object]:
    if scope not in {"single", "latest", "all"}:
        raise ValueError("必须明确指定 single、latest 或 all")
    inbox = (settings.notes_root.resolve() / settings.taxonomy["fallback"]["path"][0]).resolve()
    candidates = [p for p in inbox.glob("*.md") if p.is_file() and not p.is_symlink()]
    candidates.sort(key=lambda p: (p.stat().st_mtime_ns, p.name.casefold()), reverse=True)
    if scope == "latest":
        candidates = candidates[:1]
    elif scope == "single":
        if note is None:
            raise ValueError("single 必须通过 --note 指定一篇文件")
        selected = note_within_root(settings, note)
        candidates = [selected]
    return {
        "schema_version": 1,
        "status": "inventory",
        "scope": scope,
        "note_count": len(candidates),
        "notes": [
            {
                "source": p.relative_to(settings.notes_root.resolve()).as_posix(),
                "sha256": note_sha256(p),
                "bvid": extract_bvid(p.read_text(encoding="utf-8-sig")),
                "suggested_destination": None,
            }
            for p in candidates
        ],
    }


def _load_plan(settings: Settings, plan_path: Path) -> tuple[list[dict[str, str]], str]:
    plan = plan_path.expanduser().resolve()
    runtime = (settings.runtime_root / "organize-plans").resolve()
    if runtime not in plan.parents or not plan.is_file() or plan.suffix.lower() != ".json":
        raise ValueError("整理计划必须是 runtime/organize-plans 下的 JSON 文件")
    raw = plan.read_bytes()
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("整理计划必须声明 schema_version: 1")
    entries = payload.get("notes")
    if not isinstance(entries, list) or not 1 <= len(entries) <= PLAN_LIMIT:
        raise ValueError(f"整理计划必须包含 1 至 {PLAN_LIMIT} 篇笔记")
    root = settings.notes_root.resolve()
    sources: set[str] = set()
    targets: set[str] = set()
    prepared: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("每项整理计划必须是对象")
        if not {"source", "destination", "sha256"} <= entry.keys():
            raise ValueError("每项必须包含 source、destination、sha256")
        source_parts = _relpath(entry["source"])
        destination_parts = _relpath(entry["destination"])
        expected = entry["sha256"]
        if not isinstance(expected, str) or not _HASH.fullmatch(expected):
            raise ValueError("每项必须携带源笔记的 64 位 SHA-256")
        if not source_parts[-1].lower().endswith(".md"):
            raise ValueError("只能整理 Markdown 笔记")
        _validated_destination(settings, "/".join(destination_parts))
        source = root.joinpath(*source_parts)
        dest = safe_target_directory(settings, destination_parts) / source_parts[-1]
        # Compare resolved destinations, but do NOT resolve source at this stage:
        # resume needs to handle an already-moved, now-missing source.
        if root not in source.resolve(strict=False).parents:
            raise ValueError("来源路径不能指向 notes_root 之外")
        skey = source.as_posix().casefold()
        tkey = dest.as_posix().casefold()
        if skey in sources or tkey in targets:
            raise ValueError("同一批次不允许重复来源或目标文件")
        sources.add(skey)
        targets.add(tkey)
        prepared.append({
            "source": "/".join(source_parts),
            "destination": "/".join(destination_parts),
            "sha256": expected,
        })
    # A stable operation identifier only depends on validated content, not plan location.
    identity = hashlib.sha256(
        json.dumps(prepared, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:24]
    return prepared, identity


def _location(settings: Settings, entry: dict[str, str]) -> tuple[Path, Path]:
    root = settings.notes_root.resolve()
    source = root.joinpath(*entry["source"].split("/"))
    target = safe_target_directory(settings, tuple(entry["destination"].split("/"))) / source.name
    return source, target


def _inspect(settings: Settings, entry: dict[str, str], was_started: bool) -> dict[str, str]:
    source, target = _location(settings, entry)
    common = {"source": entry["source"], "target": target.relative_to(settings.notes_root.resolve()).as_posix()}
    expected = entry["sha256"]

    if not source.exists():
        if was_started and target.is_file() and note_sha256(target) == expected:
            return {**common, "status": "already_organized"}
        return {**common, "status": "blocked", "reason": "source_missing_or_unverified_move"}

    try:
        source = note_within_root(settings, source)
        if note_sha256(source) != expected:
            return {**common, "status": "blocked", "reason": "source_changed"}
        if target.exists() or target.is_symlink():
            if was_started and target.is_file() and os.path.samefile(source, target) and note_sha256(target) == expected:
                return {**common, "status": "repairable_link"}
            return {**common, "status": "blocked", "reason": "destination_exists"}
        bvid = extract_bvid(source.read_text(encoding="utf-8-sig"))
        if bvid and len(find_notes_by_bvid(settings, bvid)) > 1:
            return {**common, "status": "blocked", "reason": "duplicate_bvid_requires_review"}
        links = affected_backlinks(settings, source, target)
        if links:
            return {**common, "status": "blocked", "reason": "possible_broken_backlinks", "detail": "; ".join(links[:8])}
    except (OSError, ValueError, UnicodeError) as error:
        return {**common, "status": "blocked", "reason": str(error)}
    return {**common, "status": "ready"}


def _checkpoint(settings: Settings, identifier: str) -> Path:
    return settings.runtime_root / "organize-batches" / f"{identifier}.json"


def _read_checkpoint(settings: Settings, identifier: str) -> dict[str, str]:
    path = _checkpoint(settings, identifier)
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("identifier") != identifier or not isinstance(payload.get("items"), dict):
        raise ValueError("批次恢复记录格式或标识不一致，禁止自动覆盖")
    return {str(k): str(v) for k, v in payload["items"].items()}


def _save_checkpoint(settings: Settings, identifier: str, items: dict[str, str]) -> None:
    atomic_write(
        _checkpoint(settings, identifier),
        json.dumps({"schema_version": 1, "identifier": identifier, "items": items}, ensure_ascii=False, indent=2) + "\n",
    )


def organize_batch(
    settings: Settings, plan_path: Path, *, confirmed_scope: str, apply: bool = False
) -> dict[str, Any]:
    """Preview by default; apply with per-file checkpoints and safe retry."""
    if confirmed_scope not in {"single", "latest", "all"}:
        raise ValueError("批次整理必须明确指定 single、latest 或 all")
    entries, identifier = _load_plan(settings, plan_path)
    if confirmed_scope == "single" and len(entries) != 1:
        raise ValueError("single 只允许包含一篇笔记")
    if confirmed_scope == "latest":
        latest = list_inbox(settings, "latest")["notes"]
        if len(entries) != 1:
            raise ValueError("latest 计划必须且只能指定一篇笔记")
        is_latest = bool(latest and latest[0]["source"] == entries[0]["source"])
        started = _read_checkpoint(settings, identifier).get(entries[0]["source"]) in {"started", "done"}
        if not is_latest and not started:
            raise ValueError("latest 计划已失效：该笔记不是当前最近一篇，且没有可恢复检查点")
    if confirmed_scope == "all":
        inbox = settings.taxonomy["fallback"]["path"][0]
        if any(not x["source"].startswith(inbox + "/") or len(x["source"].split("/")) != 2 for x in entries):
            raise ValueError("all 仅允许整理 00-待整理 内的直接子文件")
        planned = {x["source"] for x in entries}
        current = {x["source"] for x in list_inbox(settings, "all")["notes"]}
        missing = current - planned
        # A batch already in progress may safely finish its original snapshot
        # even when newer notes arrive. A new 'all' plan must cover all notes.
        if missing and not _read_checkpoint(settings, identifier):
            raise ValueError(f"all 计划不完整，待整理目录另有 {len(missing)} 篇未列入计划")
    lock = settings.runtime_root / "locks" / "organize-batch.lock"
    with waiting_file_lock(lock, timeout_seconds=30.0):
        states = _read_checkpoint(settings, identifier)
        results: list[dict[str, str]] = []
        for item in entries:
            key = item["source"]
            was_started = states.get(key) in {"started", "done"}
            result = _inspect(settings, item, was_started)
            if not apply or result["status"] == "blocked":
                results.append(result)
                continue
            source, target = _location(settings, item)
            if result["status"] == "ready":
                # Record intent BEFORE touching the note, for crash recovery.
                states[key] = "started"
                _save_checkpoint(settings, identifier, states)
                try:
                    organize_note(
                        settings, source, destination=item["destination"],
                        confirmed_scope=confirmed_scope, expected_sha256=item["sha256"],
                        refresh_navigation=False,
                    )
                    result["status"] = "organized"
                except (OSError, ValueError) as error:
                    result["status"] = "blocked"
                    result["reason"] = str(error)
            elif result["status"] == "repairable_link":
                try:
                    with waiting_file_lock(settings.runtime_root / "locks" / "organizer.lock", timeout_seconds=30.0):
                        if not (source.exists() and target.exists() and os.path.samefile(source, target)
                                and note_sha256(source) == item["sha256"] and note_sha256(target) == item["sha256"]):
                            raise ValueError("恢复前文件状态发生变化")
                        source.unlink()  # Remove only the original name of the verified hardlink.
                    result["status"] = "recovered"
                except (OSError, ValueError) as error:
                    result["status"] = "blocked"
                    result["reason"] = str(error)
            elif result["status"] == "already_organized":
                result["status"] = "already_organized"
            if result["status"] != "blocked":
                states[key] = "done"
                _save_checkpoint(settings, identifier, states)
            results.append(result)

        navigation = "not_requested"
        if apply:
            try:
                build_navigation(settings)
                navigation = "refreshed"
            except (OSError, ValueError, TimeoutError) as error:
                navigation = f"needs_refresh: {error}"

        blocked = sum(x["status"] == "blocked" for x in results)
        status = "preview" if not apply else (
            "organized_batch" if blocked == 0 and navigation == "refreshed" else "partial"
        )
        return {
            "schema_version": 1,
            "status": status,
            "plan_id": identifier,
            "applied": apply,
            "scope": confirmed_scope,
            "count": len(results),
            "blocked": blocked,
            "navigation": navigation,
            "results": results,
        }
