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
    load_settings,
)
from .doctor import doctor_report, onboarding_report, run_doctor
from .lifecycle import (
    FAILSAFE_SECONDS,
    finalize_note,
    prepare_description_note,
    prepare_local_asr_note,
    prepare_note,
    prepare_transcript_note,
)
from .local_asr import health_report as local_asr_health_report
from .navigation import build_navigation
from .organization_batch import list_inbox, organize_batch
from .organization_duplicates import duplicates_inventory, recycle_duplicates
from .organizer import OrganizerNavigationPending, find_duplicate_bvid_notes, organize_note, organize_resource_note


def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "config" / "bilibili-note-taxonomy.json").is_file():
            return candidate
    raise RuntimeError("未找到 bili-learning-automation 项目根目录")


def _add_existing_note_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--on-existing",
        choices=("ask", "update", "rerun"),
        default="ask",
        help="相同 BVID 已存在时：询问、更新指定旧笔记或明确重新生成一篇",
    )
    parser.add_argument("--update-target", type=Path, help="--on-existing update 时要更新的现有笔记路径")


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
    asr_health_parser = subparsers.add_parser("asr-health", help="检查外部 local-ASR-service 是否可用")
    asr_health_parser.add_argument("--timeout", type=int, default=3, help="健康检查超时秒数")

    configure_parser = subparsers.add_parser("configure-obsidian", help="把本机 Obsidian Vault 写入 config/local.json")
    configure_parser.add_argument("--vault", type=Path, required=True, help="包含 .obsidian 的 Vault 根目录")
    configure_parser.add_argument(
        "--notes-subdir",
        default=DEFAULT_NOTES_SUBDIR,
        help="Vault 内用于保存本项目笔记的相对子目录",
    )
    cookie_parser = subparsers.add_parser("configure-cookie", help="把 Bilibili Cookie 文件路径写入 config/local.json")
    cookie_parser.add_argument("--file", type=Path, required=True, help="Netscape 格式 Cookie 文件路径")

    subparsers.add_parser("build-nav", help="重建 Obsidian 导航")
    prepare_parser = subparsers.add_parser("prepare", help="采集资料并创建 runtime 草稿任务")
    prepare_parser.add_argument("message", nargs="?", help="Bilibili 复制链接、短链或 BV 号")
    prepare_parser.add_argument("--dry-run", action="store_true")
    prepare_parser.add_argument("--cleanup-job", type=Path)
    prepare_parser.add_argument("--after-seconds", type=int, default=FAILSAFE_SECONDS)
    prepare_parser.add_argument("--cleanup-runner", type=Path, help=argparse.SUPPRESS)
    _add_existing_note_arguments(prepare_parser)
    asr_parser = subparsers.add_parser("prepare-asr", help="用户明确授权后，通过 local-ASR-service 转录并创建标准 Job")
    asr_parser.add_argument("message", help="Bilibili 复制链接、短链或 BV 号")
    asr_parser.add_argument("--cleanup-runner", type=Path, help=argparse.SUPPRESS)
    _add_existing_note_arguments(asr_parser)
    transcript_parser = subparsers.add_parser("prepare-transcript", help="把已授权取得的纯文本 transcript 接入标准 Job")
    transcript_parser.add_argument("message", help="Bilibili 复制链接、短链或 BV 号")
    transcript_parser.add_argument("--transcript", type=Path, required=True, help="已有的无时间戳纯文本 transcript")
    transcript_parser.add_argument("--cleanup-runner", type=Path, help=argparse.SUPPRESS)
    _add_existing_note_arguments(transcript_parser)
    description_parser = subparsers.add_parser("prepare-description", help="只采集元数据和 UP 主简介，创建纯资源分享 Job")
    description_parser.add_argument("message", help="Bilibili 复制链接、短链或 BV 号")
    description_parser.add_argument("--cleanup-runner", type=Path, help=argparse.SUPPRESS)
    _add_existing_note_arguments(description_parser)
    finalize_parser = subparsers.add_parser("finalize", help="校验 runtime 草稿并发布笔记")
    finalize_parser.add_argument("--job", type=Path, required=True)
    finalize_parser.add_argument("--note", type=Path, required=True)
    organize_parser = subparsers.add_parser("organize", help="学习后整理已有笔记；默认归档不改正文，纯资源可压缩进资源集合页")
    organize_parser.add_argument("--note", type=Path, required=True, help="待整理笔记路径")
    organize_parser.add_argument(
        "--mode",
        choices=("archive", "resource"),
        default="archive",
        help="archive=默认仅移动且保留文件名和全部内容；resource=单独授权后压缩资源笔记",
    )
    organize_parser.add_argument("--filename", help="可选的旧版显式重命名参数；默认保持来源文件名不变")
    organize_parser.add_argument("--destination", help="archive 模式下 notes_root 的目标相对目录，推荐“领域/对象”")
    organize_parser.add_argument("--collection", help="resource 模式的资源集合页名称，例如“Skills”或“网站与灵感”")
    organize_parser.add_argument(
        "--card-file",
        type=Path,
        help="resource 模式的资源卡 Markdown 草稿；必须位于 runtime/resource-cards，Agent 完整读完原笔记后生成",
    )
    organize_parser.add_argument(
        "--confirmed-scope",
        choices=("single", "latest", "all"),
        required=True,
        help="用户已明确选择指定单篇（single）、最近一篇（latest）或全部待整理笔记（all）",
    )
    list_parser = subparsers.add_parser("organize-list", help="只读枚举待整理笔记及哈希，由 Agent 阅读后制定分类计划")
    list_parser.add_argument("--scope", choices=("single", "latest", "all"), required=True)
    list_parser.add_argument("--note", type=Path, help="single 时必须指定现有笔记路径")
    batch_parser = subparsers.add_parser("organize-batch", help="按 Agent 已审阅的 JSON 计划安全批量归档，默认仅预览")
    batch_parser.add_argument("--plan", type=Path, required=True)
    batch_parser.add_argument("--confirmed-scope", choices=("single", "latest", "all"), required=True)
    batch_parser.add_argument("--apply", action="store_true", help="执行明确授权范围内的归档，记录可恢复检查点")
    duplicate_parser = subparsers.add_parser("organize-duplicates", help="查询重复版本或按精确文件清单移入 Windows 回收站")
    duplicate_group = duplicate_parser.add_mutually_exclusive_group(required=True)
    duplicate_group.add_argument("--bvid", help="只读查询该 BVID 的重复文件")
    duplicate_group.add_argument("--plan", type=Path, help="用户确认保留/回收文件及哈希的 JSON 计划")
    duplicate_parser.add_argument("--apply", action="store_true", help="只按计划列出的文件执行回收站清理")
    args = parser.parse_args()

    project_root = args.project_root.resolve() if args.project_root else find_project_root()

    if args.command in {"configure-obsidian", "configure-cookie"}:
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
            else:
                config_path = configure_cookie_file(project_root, args.file)
                payload = {
                    "schema_version": 1,
                    "status": "configured",
                    "config_path": str(config_path),
                    "cookie_file": str(args.file.expanduser().resolve()),
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
    if args.command == "asr-health":
        report, code = local_asr_health_report(settings, timeout=args.timeout)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(code)
    if args.command == "build-nav":
        build_navigation(settings)
        print(f"导航已刷新：{settings.notes_root / settings.navigation_dir}")
        return
    if args.command in {"organize-list", "organize-batch", "organize-duplicates"}:
        try:
            if args.command == "organize-list":
                result = list_inbox(settings, args.scope, note=args.note)
            elif args.command == "organize-batch":
                result = organize_batch(settings, args.plan, confirmed_scope=args.confirmed_scope, apply=args.apply)
            elif args.bvid is not None:
                if args.apply:
                    raise ValueError("--bvid 是只读查询；执行删除必须提供显式 JSON --plan")
                result = duplicates_inventory(settings, args.bvid)
            else:
                result = recycle_duplicates(settings, args.plan, apply=args.apply)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            raise SystemExit(0 if result["status"] not in {"partial", "failed"} else 2)
        except (OSError, ValueError, TypeError, KeyError) as error:
            print(json.dumps({"schema_version": 1, "status": "failed", "message": str(error)}, ensure_ascii=False, indent=2))
            raise SystemExit(1)
    if args.command == "prepare":
        payload, code = prepare_note(
            project_root,
            args.message,
            dry_run=args.dry_run,
            cleanup_job_path=args.cleanup_job,
            after_seconds=args.after_seconds,
            cleanup_runner=args.cleanup_runner,
            on_existing=args.on_existing,
            update_target=args.update_target,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(code)
    if args.command == "prepare-asr":
        payload, code = prepare_local_asr_note(
            project_root,
            args.message,
            cleanup_runner=args.cleanup_runner,
            on_existing=args.on_existing,
            update_target=args.update_target,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(code)
    if args.command == "prepare-transcript":
        payload, code = prepare_transcript_note(
            project_root,
            args.message,
            args.transcript,
            cleanup_runner=args.cleanup_runner,
            on_existing=args.on_existing,
            update_target=args.update_target,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(code)
    if args.command == "prepare-description":
        payload, code = prepare_description_note(
            project_root,
            args.message,
            cleanup_runner=args.cleanup_runner,
            on_existing=args.on_existing,
            update_target=args.update_target,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(code)
    if args.command == "finalize":
        payload, code = finalize_note(project_root, args.job, args.note)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(code)
    if args.command == "organize":
        try:
            if args.mode == "resource":
                if args.collection is None or args.card_file is None:
                    raise ValueError("resource 模式必须同时提供 --collection 与 --card-file")
                result = organize_resource_note(
                    settings,
                    args.note,
                    args.collection,
                    card_path=args.card_file,
                    confirmed_scope=args.confirmed_scope,
                )
                collection_path = Path(result["collection_path"])
                resolved_root = settings.notes_root.resolve()
                relative_note = collection_path.resolve().relative_to(resolved_root)
                logical_note = settings.notes_root / relative_note
                payload = {
                    "schema_version": 1,
                    "status": "resource_compacted",
                    "scope": args.confirmed_scope,
                    "bvid": result["bvid"],
                    "collection_path": str(logical_note),
                    "resolved_collection_path": str(collection_path.resolve()),
                    "updated_existing_card": result["updated_existing_card"],
                    "backup_path": str(result["backup_path"]),
                    "card_cleanup_warning": result["card_cleanup_warning"],
                }
            else:
                if args.destination is None:
                    raise ValueError("archive 模式必须指定 --destination；默认保留原文件名")
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
        except OrganizerNavigationPending as error:
            print(json.dumps({
                "schema_version": 1,
                "status": "organized_navigation_pending",
                "note_path": str(error.target),
                "message": str(error),
            }, ensure_ascii=False, indent=2))
            raise SystemExit(2)
        except Exception as error:
            print(json.dumps({"schema_version": 1, "status": "failed", "message": str(error)}, ensure_ascii=False, indent=2))
            raise SystemExit(1)


if __name__ == "__main__":
    main()
