from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILL = REPO_ROOT / "skill" / "bili-learning-automation"
CANONICAL_SKILL_MD = CANONICAL_SKILL / "SKILL.md"
CHATGPT_SKILL_NAME = "bili-learning-automation-chatgpt"
ARCHIVE_NAME = f"{CHATGPT_SKILL_NAME}.zip"
GENERATED_MARKER = "<!-- GENERATED from skill/bili-learning-automation/SKILL.md; DO NOT EDIT DIRECTLY. -->"

REFERENCE_SOURCES = {
    "references/AGENT-INTEGRATION.md": REPO_ROOT / "docs" / "AGENT-INTEGRATION.md",
    "references/BILIBILI-COOKIE.md": REPO_ROOT / "docs" / "BILIBILI-COOKIE.md",
    "references/CONFIGURATION.md": REPO_ROOT / "docs" / "CONFIGURATION.md",
    "references/MAINTENANCE-HANDOFF.md": REPO_ROOT / "docs" / "MAINTENANCE-HANDOFF.md",
    "references/NOTE-ORGANIZATION.md": REPO_ROOT / "docs" / "NOTE-ORGANIZATION.md",
    "references/OBSIDIAN-STYLING.md": REPO_ROOT / "docs" / "OBSIDIAN-STYLING.md",
    "references/TROUBLESHOOTING.md": REPO_ROOT / "docs" / "TROUBLESHOOTING.md",
    "references/LIGHT-WORKFLOW.md": REPO_ROOT / "docs" / "standards" / "LIGHT-WORKFLOW.md",
    "references/CODEX-VIDEO-NOTE-GUIDE.md": REPO_ROOT / "docs" / "standards" / "CODEX-VIDEO-NOTE-GUIDE.md",
    "references/KNOWLEDGE-DENSE-WORKFLOW.md": REPO_ROOT / "docs" / "standards" / "KNOWLEDGE-DENSE-WORKFLOW.md",
    "references/STANDARD-VIDEO-NOTE-EXAMPLE.md": REPO_ROOT / "docs" / "standards" / "STANDARD-VIDEO-NOTE-EXAMPLE.md",
}

FORBIDDEN_NAMES = {
    ".env",
    "cookie.txt",
    "cookies.txt",
    "bilibili_cookies.txt",
    "local.json",
    "pinned-comment-whitelist.local.json",
}


def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"\A---\r?\n(?P<frontmatter>.*?)\r?\n---\r?\n(?P<body>.*)\Z", text, flags=re.DOTALL)
    if not match:
        raise ValueError("canonical SKILL.md 缺少有效 YAML frontmatter")
    return match.group("frontmatter"), match.group("body")


def frontmatter_value(frontmatter: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", frontmatter)
    if not match:
        raise ValueError(f"canonical SKILL.md 缺少 {key}")
    return match.group(1)


def render_skill() -> str:
    canonical = CANONICAL_SKILL_MD.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(canonical)
    if frontmatter_value(frontmatter, "name") != "bili-learning-automation":
        raise ValueError("canonical Skill name 必须是 bili-learning-automation")
    description = frontmatter_value(frontmatter, "description")
    host_guard = (
        "## ChatGPT Web 宿主边界\n\n"
        "必须通过已授权的本地工作区桥接访问项目；只有远程沙箱而无法访问本机项目时停止。"
        "不要上传 Cookie、runtime、私人笔记或本机配置。包内 references 是构建时文档快照；"
        "连接本地项目后仍以项目根 AGENTS.md、当前 Job agent_handoff.md 与本地项目文档为运行事实源。\n\n"
    )
    return (
        f"---\nname: {CHATGPT_SKILL_NAME}\ndescription: {description}\n---\n\n"
        f"{GENERATED_MARKER}\n\n{host_guard}{body.lstrip()}"
    )


def render_openai_yaml() -> str:
    return (
        "interface:\n"
        '  display_name: "B站视频转笔记 · ChatGPT"\n'
        '  short_description: "通过本地工作区桥接生成 Obsidian B站学习笔记。"\n'
        '  default_prompt: "Use $bili-learning-automation-chatgpt to check the local workspace bridge and turn this Bilibili link into an Obsidian learning note."\n'
        "policy:\n"
        "  allow_implicit_invocation: true\n"
    )


def package_files() -> dict[Path, bytes]:
    files: dict[Path, bytes] = {
        Path("SKILL.md"): render_skill().encode("utf-8"),
        Path("agents/openai.yaml"): render_openai_yaml().encode("utf-8"),
    }
    for relative, source in REFERENCE_SOURCES.items():
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"reference 真源无效：{source.relative_to(REPO_ROOT)}")
        files[Path(relative)] = source.read_bytes()
    return files


def validate(files: dict[Path, bytes]) -> None:
    if set(path.as_posix() for path in files if path.name == "SKILL.md") != {"SKILL.md"}:
        raise ValueError("ChatGPT Skill 必须且只能包含一个根目录 SKILL.md")
    if GENERATED_MARKER not in files[Path("SKILL.md")].decode("utf-8"):
        raise ValueError("ChatGPT SKILL.md 缺少 generated marker")
    if f"name: {CHATGPT_SKILL_NAME}" not in files[Path("SKILL.md")].decode("utf-8"):
        raise ValueError("ChatGPT SKILL.md name 不正确")
    if f"${CHATGPT_SKILL_NAME}" not in files[Path("agents/openai.yaml")].decode("utf-8"):
        raise ValueError("ChatGPT openai.yaml 没有引用正确 Skill 名称")

    for relative in files:
        lowered = {part.lower() for part in relative.parts}
        if relative.name.lower() in FORBIDDEN_NAMES:
            raise ValueError(f"包内包含禁止文件：{relative}")
        if "__pycache__" in lowered or relative.suffix.lower() in {".pyc", ".pyo"}:
            raise ValueError(f"包内包含缓存：{relative}")
        if any(part in {"key", "notes", ".runtime"} for part in lowered):
            raise ValueError(f"包内包含本机数据目录：{relative}")


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def build(output_dir: Path) -> dict[str, object]:
    files = package_files()
    validate(files)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / ARCHIVE_NAME
    with zipfile.ZipFile(archive_path, "w") as archive:
        for relative in sorted(files):
            archive.writestr(zip_info(f"{CHATGPT_SKILL_NAME}/{relative.as_posix()}"), files[relative])
    return {
        "status": "chatgpt_skill_built",
        "archive": str(archive_path),
        "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "files": len(files),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="从 canonical Skill 直接生成 ChatGPT Web 安装 ZIP")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "dist")
    parser.add_argument("--check", action="store_true", help="只验证 canonical Skill 与 ChatGPT package render，不写 ZIP")
    args = parser.parse_args()

    if not CANONICAL_SKILL_MD.is_file():
        raise SystemExit(f"canonical Skill 不存在：{CANONICAL_SKILL_MD}")

    files = package_files()
    validate(files)
    if args.check:
        print(
            json.dumps(
                {
                    "status": "chatgpt_skill_ready",
                    "canonical": str(CANONICAL_SKILL),
                    "skill": CHATGPT_SKILL_NAME,
                    "files": len(files),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    output_dir = args.output_dir if args.output_dir.is_absolute() else (REPO_ROOT / args.output_dir).resolve()
    print(json.dumps(build(output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
