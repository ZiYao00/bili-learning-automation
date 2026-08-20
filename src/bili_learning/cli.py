from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_settings
from .doctor import run_doctor
from .navigation import build_navigation


def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "config" / "bilibili-note-taxonomy.json").is_file():
            return candidate
    raise RuntimeError("未找到 bili-learning-automation 项目根目录")


def main() -> None:
    parser = argparse.ArgumentParser(prog="bili-learning", description="B站视频转笔记维护工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="检查本机依赖和配置")
    subparsers.add_parser("build-nav", help="重建 Obsidian 导航")
    args = parser.parse_args()

    settings = load_settings(find_project_root())
    if args.command == "doctor":
        code, lines = run_doctor(settings)
        print("\n".join(lines))
        raise SystemExit(code)
    if args.command == "build-nav":
        build_navigation(settings)
        print(f"导航已刷新：{settings.notes_root / settings.navigation_dir}")
