from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import (
    DEFAULT_NOTES_SUBDIR,
    ConfigurationError,
    configure_cookie_file,
    configure_obsidian,
    configure_ytdlp_path,
    load_settings,
)
from .doctor import doctor_report, onboarding_report, run_doctor
from .lifecycle import FAILSAFE_SECONDS, finalize_note, prepare_note
from .navigation import build_navigation
from .organizer import find_duplicate_bvid_notes, organize_note


def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "config" / "bilibili-note-taxonomy.json").is_file():
            return candidate
    raise RuntimeError("未找到 bili-learning-automation 项目根目录")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(prog="bili-learning", description="B站视频转笔记维护工具")
    parser.add_argument("--project-root", type=Path, help="项目根目录；省略时从当前目录向上查找")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="检查本机依赖和配置")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json", help="输出机器可读诊断 JSON")
    subparsers.add_parser("onboarding", help="输出首次使用所需的结构化环境检查")

    configure_parser = subparsers.add_parser("configure-obsidian", help="把本机 Obsidian Vault 写入 config/local.json")
    configure_parser.add_argument("--vault", type=Path, required=True, help="包含 .obsidian 的 Vault 根目录")
    configure_parser.add_argument(
        "--notes-subdir",
        default=DEFAULT_NOTES_SUBDIR,
        help="Vault 内用于保存本项目笔记的相对子目录",
    )
    cookie_parser = subparsers.add_parser("configure-cookie", help="把 Bilibili Cookie 文件路径写入 config/local.json")
    cookie_parser.add_argument("--file", type=Path, required=True, help="Netscape 格式 Cookie 文件路径")
    ytdlp_parser = subparsers.add_parser("configure-ytdlp", help="把自定义 yt-dlp 路径写入 config/local.json")
    ytdlp_parser.add_argument("--path", type=Path, required=True, help="yt-dlp 可执行文件路径")

    subparsers.add_parser("build-nav", help="重建 Obsidian 导航")
    prepare_parser = subparsers.add_parser("prepare", help="采集资料并创建 runtime 草稿任务")
    prepare_parser.add_argument("message", nargs="?", help="Bilibili 复制链接、短链或 BV 号")
    prepare_parser.add_argument("--dry-run", action="store_true")
    prepare_parser.add_argument("--cleanup-job", type=Path)
    prepare_parser.add_argument("--after-seconds", type=int, default=FAILSAFE_SECONDS)
    prepare_parser.add_argument("--cleanup-runner", type=Path, help=argparse.SUPPRESS)
    finalize_parser = subparsers.add_parser("finalize", help="校验 runtime 草稿并发布笔记")
    finalize_parser.add_argument("--job", type=Path, required=True)
    finalize_parser.add_argument("--note", type=Path, required=True)
    organize_parser = subparsers.add_parser("organize", help="学习后归档已有笔记；只改文件名和路径，不改正文")
    organize_parser.add_argument("--note", type=Path, required=True, help="待归档笔记路径")
    organize_parser.add_argument("--filename", required=True, help="新的简短文件名；可省略 .md")
    organize_parser.add_argument("--destination", required=True, help="notes_root 下的目标相对目录，推荐“领域/对象”")
    organize_parser.add_argument(
        "--confirmed-scope",
        choices=("single", "latest", "all"),
        required=True,
        help="用户已明确选择指定单篇（single）、最近一篇（latest）或全部待整理笔记（all）",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve() if args.project_root else find_project_root()

    if args.command in {"configure-obsidian", "configure-cookie", "configure-ytdlp"}:
        try:
            if args.command == "configure-obsidian":
                config_path = configure_obsidian(project_root, args.vault, args.notes_subdir)
                settings = load_settings(project_root)
                payload = {
                    "schema_version": 1,
                    "status": "configured",
                    "config_path": str(config_path),
                    "vault_root": str(settings.vault_root),
                    "notes_root": str(settings.notes_root),
                }
            elif args.command == "configure-cookie":
                config_path = configure_cookie_file(project_root, args.file)
                payload = {
                    "schema_version": 1,
                    "status": "configured",
                    "config_path": str(config_path),
                    "cookie_file": str(args.file.expanduser().resolve()),
                }
            else:
                config_path = configure_ytdlp_path(project_root, args.path)
                payload = {
                    "schema_version": 1,
                    "status": "configured",
                    "config_path": str(config_path),
                    "ytdlp": str(args.path.expanduser().resolve()),
                }
        except ConfigurationError as error:
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "failed",
                        "code": error.code,
                        "message": str(error),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            raise SystemExit(2)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    settings = load_settings(project_root)
    if args.command == "doctor":
        if args.as_json:
            report = doctor_report(settings)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            raise SystemExit(0 if report["status"] == "ok" else 1)
        code, lines = run_doctor(settings)
        print("\n".join(lines))
        raise SystemExit(code)
    if args.command == "onboarding":
        report = onboarding_report(settings)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report["status"] == "ready" else 2)
    if args.command == "build-nav":
        build_navigation(settings)
        print(f"导航已刷新：{settings.notes_root / settings.navigation_dir}")
        return
    if args.command == "prepare":
        payload, code = prepare_note(
            project_root,
            args.message,
            dry_run=args.dry_run,
            cleanup_job_path=args.cleanup_job,
            after_seconds=args.after_seconds,
            cleanup_runner=args.cleanup_runner,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(code)
    if args.command == "finalize":
        payload, code = finalize_note(project_root, args.job, args.note)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(code)
    if args.command == "organize":
        try:
            bvid, duplicates = find_duplicate_bvid_notes(settings, args.note)
            note_path = organize_note(
                settings,
                args.note,
                args.filename,
                destination=args.destination,
                confirmed_scope=args.confirmed_scope,
            )
            resolved_root = settings.notes_root.resolve()
            relative_note = note_path.resolve().relative_to(resolved_root)
            logical_note = settings.notes_root / relative_note
            logical_duplicates = [
                str(settings.notes_root / path.resolve().relative_to(resolved_root)) for path in duplicates
            ]
            payload = {
                "schema_version": 1,
                "status": "organized",
                "scope": args.confirmed_scope,
                "bvid": bvid,
                "note_path": str(logical_note),
                "resolved_note_path": str(note_path.resolve()),
                "duplicate_bvid_notes": logical_duplicates,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as error:
            print(json.dumps({"schema_version": 1, "status": "failed", "message": str(error)}, ensure_ascii=False, indent=2))
            raise SystemExit(1)


if __name__ == "__main__":
    main()
