#!/usr/bin/env python3
"""Validate a finished Bilibili note and always remove its temporary job data."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = PROJECT_ROOT / ".runtime" / "bilibili-learning"
NAVIGATION_BUILDER = PROJECT_ROOT / "hermes-skills" / "bilibili-learning" / "scripts" / "build_bilibili_navigation.py"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def emit(payload: dict, code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def safe_job_path(path: Path) -> Path:
    root = RUNTIME_ROOT.resolve()
    candidate = path.resolve()
    if candidate == root or root not in candidate.parents:
        raise ValueError("拒绝清理运行目录之外的路径。")
    return candidate


def remove_job(path: Path) -> None:
    candidate = safe_job_path(path)
    if candidate.exists() and not candidate.is_symlink():
        shutil.rmtree(candidate)


def validate(note: Path, job: dict) -> list[str]:
    if not note.is_file():
        return ["笔记文件不存在"]
    text = note.read_text(encoding="utf-8")
    errors: list[str] = []
    if note.resolve() != Path(job["note_path"]).resolve():
        errors.append("笔记路径不符合分类规范")
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if not title_match or title_match.group(1).strip() != job["canonical_title"]:
        errors.append("H1 不符合标准短标题")
    if note.stem != job["canonical_title"]:
        errors.append("文件名不符合标准短标题")
    for field in ("author:", "published:", "duration:", "source:", "tags:"):
        if f"\n{field}" not in text and not text.startswith(field):
            errors.append(f"缺少 Frontmatter 字段：{field.rstrip(':')}")
    description_at = text.find("> **视频简介**")
    iframe_at = text.find("https://player.bilibili.com/player.html?bvid=" + job["bvid"])
    if description_at < 0:
        errors.append("缺少视频简介区块")
    if iframe_at < 0:
        errors.append("缺少正确的官方播放器 iframe")
    elif description_at > iframe_at:
        errors.append("视频简介没有放在播放器之前")
    for url in re.findall(r"https?://[^\s]+", job["description"]):
        if url.rstrip("。)，)") not in text:
            errors.append("原始简介中的 URL 未完整保留")
            break
    for heading in ("## 怎么做", "## 容易踩坑"):
        if heading not in text:
            errors.append(f"缺少章节：{heading}")
    frontmatter = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    tags = re.findall(r"(?m)^\s+-\s+(.+)$", frontmatter.group(1) if frontmatter else "")
    for tag in job.get("required_tags", []):
        if tag not in tags:
            errors.append(f"缺少规范标签：{tag}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--note", type=Path, required=True)
    args = parser.parse_args()
    job_dir = safe_job_path(args.job)
    payload: dict = {}
    code = 0
    try:
        job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        errors = validate(args.note, job)
        if errors:
            payload, code = {"status": "note_invalid", "message": "；".join(errors)}, 2
        else:
            completed = subprocess.run([sys.executable, str(NAVIGATION_BUILDER)], text=True, encoding="utf-8", errors="replace", capture_output=True)
            if completed.returncode:
                payload, code = {"status": "failed", "message": "笔记已通过但导航生成失败"}, 1
            else:
                payload, code = {"status": "note_ready", "note_path": str(args.note)}, 0
    except Exception as error:
        payload, code = {"status": "failed", "message": str(error)}, 1

    try:
        remove_job(job_dir)
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
