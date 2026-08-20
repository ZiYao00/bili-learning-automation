#!/usr/bin/env python3
"""Prepare subtitle-first Bilibili learning materials for the Hermes skill."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BILI_NOTE = PROJECT_ROOT / "bili-note" / "scripts"
WEB_ACCESS = PROJECT_ROOT / "web-access"
NOTES_DIR = PROJECT_ROOT / "notes" / "bilibili"
MATERIALS_DIR = PROJECT_ROOT / "materials"
PROXY_BASE = "http://127.0.0.1:3456"
MEDIA_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4", ".webm", ".flv", ".m4s", ".part"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def emit(payload: dict[str, Any], code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def canonicalize(value: str) -> tuple[str, str]:
    match = re.search(r"\b(BV[0-9A-Za-z]{10})\b", value, re.IGNORECASE)
    if not match:
        raise ValueError("未识别到 Bilibili BVID；请发送包含 BV 号的原始链接或分享卡片。")
    bvid = match.group(1)
    return bvid, f"https://www.bilibili.com/video/{bvid}/"


def find_existing_note(canonical_url: str) -> Path | None:
    if not NOTES_DIR.is_dir():
        return None
    for note in NOTES_DIR.glob("*.md"):
        try:
            if canonical_url in note.read_text(encoding="utf-8"):
                return note
        except OSError:
            continue
    return None


def run(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"命令失败（退出码 {completed.returncode}）")
    return completed.stdout


def proxy_request(path: str, body: str | None = None) -> dict[str, Any]:
    data = body.encode("utf-8") if body is not None else None
    request = urllib.request.Request(f"{PROXY_BASE}{path}", data=data, method="POST" if data else "GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def read_source(source_path: Path) -> dict[str, str]:
    text = source_path.read_text(encoding="utf-8")
    title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    author = re.search(r"^- UP:\s+(.+)$", text, re.MULTILINE)
    published = re.search(r"^- Published:\s+(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
    duration = re.search(r"^- Duration:\s+(.+)$", text, re.MULTILINE)
    description = re.search(r"^## Description\s*\n\n(.*?)(?=\n## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not all((title, author, published, duration, description)):
        raise RuntimeError("元数据不完整，未生成笔记。")
    filename = re.sub(r'[<>:"/\\|?*]', "", title.group(1)).strip().rstrip(".") or "Bilibili 学习笔记"
    return {
        "title": title.group(1),
        "author": author.group(1),
        "published": published.group(1),
        "duration": duration.group(1),
        "description": description.group(1).strip(),
        "suggested_filename": f"{filename}.md",
    }


def media_count(root: Path) -> int:
    return sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Bilibili URL or text containing a BV id")
    parser.add_argument("--dry-run", action="store_true", help="Only normalize and check for duplicates")
    args = parser.parse_args()

    try:
        bvid, canonical_url = canonicalize(args.url)
        existing = find_existing_note(canonical_url)
        if existing:
            emit({"status": "already_exists", "bvid": bvid, "canonical_url": canonical_url, "note_path": str(existing)})
        if args.dry_run:
            emit({"status": "ready_to_process", "bvid": bvid, "canonical_url": canonical_url})

        extract_dir = MATERIALS_DIR / bvid / "extract"
        archive_dir = MATERIALS_DIR / bvid / "source"
        run([sys.executable, str(BILI_NOTE / "extract_bilibili.py"), bvid, "--out", str(extract_dir), "--parts", "all", "--download-subtitles"], PROJECT_ROOT)

        subtitle_files = list((extract_dir / "subtitles").rglob("*.txt")) if (extract_dir / "subtitles").exists() else []
        target_id: str | None = None
        try:
            if not subtitle_files:
                run(["node", ".\\scripts\\check-deps.mjs", "--browser", "chrome"], WEB_ACCESS)
                target = proxy_request("/new", canonical_url)
                target_id = target.get("targetId")
                if not target_id:
                    raise RuntimeError("无法创建隔离的 Chrome 页面。")
                run(
                    [
                        sys.executable,
                        str(BILI_NOTE / "fetch_browser_ai_subtitles.py"),
                        "--target",
                        target_id,
                        "--out",
                        str(extract_dir),
                        "--cdp-base",
                        PROXY_BASE,
                        "--limit",
                        "1",
                    ],
                    PROJECT_ROOT,
                )
        finally:
            if target_id:
                try:
                    proxy_request(f"/close?target={target_id}")
                except Exception:
                    pass

        run([sys.executable, str(BILI_NOTE / "archive_bili_materials.py"), "--extract-dir", str(extract_dir), "--archive-dir", str(archive_dir)], PROJECT_ROOT)
        budget_path = archive_dir / "metadata" / "note_budget.json"
        budget = json.loads(budget_path.read_text(encoding="utf-8"))
        if not budget.get("subtitle_chars", 0):
            emit(
                {
                    "status": "subtitle_unavailable",
                    "bvid": bvid,
                    "canonical_url": canonical_url,
                    "message": "未取得可用字幕；默认流程未下载音频或视频。",
                    "archive_dir": str(archive_dir),
                },
                2,
            )
        visual = budget.get("visual_dependency", {})
        if visual.get("needs_visual_review"):
            emit(
                {
                    "status": "visual_review_required",
                    "bvid": bvid,
                    "canonical_url": canonical_url,
                    "message": "字幕密度不足，不能据此生成完整学习笔记。",
                    "archive_dir": str(archive_dir),
                },
                2,
            )
        source = read_source(archive_dir / "metadata" / "source.md")
        emit(
            {
                "status": "materials_ready",
                "bvid": bvid,
                "canonical_url": canonical_url,
                "archive_dir": str(archive_dir),
                "subtitle_path": str(next((archive_dir / "subtitles" / "txt").glob("*.txt"))),
                "evidence_path": str(archive_dir / "indexes" / "字幕证据索引.md"),
                "note_path": str(NOTES_DIR / source["suggested_filename"]),
                "media_files": media_count(archive_dir),
                **source,
            }
        )
    except Exception as error:
        emit({"status": "failed", "message": str(error)}, 1)


if __name__ == "__main__":
    main()
