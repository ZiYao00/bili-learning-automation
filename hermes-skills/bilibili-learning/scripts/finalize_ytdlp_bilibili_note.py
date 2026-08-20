#!/usr/bin/env python3
"""Validate a finished Bilibili note and always remove its temporary job data."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bili_learning.config import load_settings  # noqa: E402
from bili_learning.navigation import build_navigation  # noqa: E402
from bili_learning.runtime import remove_job, safe_job_path  # noqa: E402
from bili_learning.validator import validate_note  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def emit(payload: dict, code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def quarantine_invalid_note(note: Path, job: dict) -> Path | None:
    expected = Path(job["note_path"])
    if not note.is_file() or note.resolve() != expected.resolve():
        return None
    candidate = note.with_name(note.name + ".invalid")
    if candidate.exists():
        candidate = note.with_name(note.name + f".{int(time.time())}.invalid")
    note.replace(candidate)
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--note", type=Path, required=True)
    args = parser.parse_args()
    runtime_root = PROJECT_ROOT / ".runtime" / "bilibili-learning"
    job_dir = safe_job_path(runtime_root, args.job)
    payload: dict = {}
    code = 0
    try:
        settings = load_settings(PROJECT_ROOT)
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        errors = validate_note(args.note, job)
        if errors:
            invalid_note = quarantine_invalid_note(args.note, job)
            payload, code = {"status": "note_invalid", "message": "；".join(errors)}, 2
            if invalid_note:
                payload["invalid_note_path"] = str(invalid_note)
        else:
            build_navigation(settings)
            payload, code = {"status": "note_ready", "note_path": str(args.note)}, 0
    except Exception as error:
        payload, code = {"status": "failed", "message": str(error)}, 1

    try:
        remove_job(runtime_root, job_dir)
        payload["temporary_data_removed"] = True
    except Exception as error:
        payload["temporary_data_removed"] = False
        payload["cleanup_error"] = str(error)
        if code == 0:
            payload["status"] = "failed"
            payload["message"] = "笔记已写入但临时数据清理失败"
            code = 1
    emit(payload, code)


if __name__ == "__main__":
    main()
