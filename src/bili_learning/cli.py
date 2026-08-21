from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_settings
from .doctor import doctor_report, run_doctor
from .lifecycle import FAILSAFE_SECONDS, finalize_note, prepare_note
from .navigation import build_navigation
from .organizer import organize_note


def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "config" / "bilibili-note-taxonomy.json").is_file():
            return candidate
    raise RuntimeError("未找到 bili-learning-automation 项目根目录")


def main() -> None:
    parser = argparse.ArgumentParser(prog="bili-learning", description="B站视频转笔记维护工具")
    parser.add_argument("--project-root", type=Path, help="项目根目录；省略时从当前目录向上查找")
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor_parser = subparsers.add_parser("doctor", help="检查本机依赖和配置")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json", help="输出机器可读诊断 JSON")
    subparsers.add_parser("build-nav", help="重建 Obsidian 导航")
    prepare_parser = subparsers.add_parser("prepare", help="采集资料并创建 runtime 草稿任务")
    prepare_parser.add_argument("message", nargs="?", help="Bilibili 复制链接、短链或 BV 号")
    prepare_parser.add_argument("--dry-run", action="store_true")
    prepare_parser.add_argument(
        "--allow-existing-for-test",
        action="store_true",
        help="仅限本地测试：允许已存在 source/BVID 再次完整转换；普通智能体不得使用",
    )
    prepare_parser.add_argument("--cleanup-job", type=Path)
    prepare_parser.add_argument("--after-seconds", type=int, default=FAILSAFE_SECONDS)
    prepare_parser.add_argument("--cleanup-runner", type=Path, help=argparse.SUPPRESS)
    finalize_parser = subparsers.add_parser("finalize", help="校验 runtime 草稿并发布笔记")
    finalize_parser.add_argument("--job", type=Path, required=True)
    finalize_parser.add_argument("--note", type=Path, required=True)
    organize_parser = subparsers.add_parser("organize", help="学习后整理已有笔记")
    organize_parser.add_argument("--note", type=Path, required=True, help="待整理笔记路径")
    organize_parser.add_argument("--title", required=True, help="学习后确定的短标题")
    organize_parser.add_argument("--intro", required=True, help="保留在视频简介区的一句摘要")
    organize_parser.add_argument("--category", help="可选的目标相对目录；默认按 tags 推断 taxonomy 建议目录")
    args = parser.parse_args()

    project_root = args.project_root.resolve() if args.project_root else find_project_root()
    settings = load_settings(project_root)
    if args.command == "doctor":
        if args.as_json:
            report = doctor_report(settings)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            raise SystemExit(0 if report["status"] == "ok" else 1)
        code, lines = run_doctor(settings)
        print("\n".join(lines))
        raise SystemExit(code)
    if args.command == "build-nav":
        build_navigation(settings)
        print(f"导航已刷新：{settings.notes_root / settings.navigation_dir}")
        return
    if args.command == "prepare":
        payload, code = prepare_note(
            project_root,
            args.message,
            dry_run=args.dry_run,
            allow_existing_for_test=args.allow_existing_for_test,
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
            note_path = organize_note(settings, args.note, args.title, args.intro, args.category)
            print(json.dumps({"schema_version": 1, "status": "organized", "note_path": str(note_path)}, ensure_ascii=False, indent=2))
        except Exception as error:
            print(json.dumps({"schema_version": 1, "status": "failed", "message": str(error)}, ensure_ascii=False, indent=2))
            raise SystemExit(1)


if __name__ == "__main__":
    main()
