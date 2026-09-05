from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILL_DIR = REPO_ROOT / "skill" / "bili-learning-automation"
CANONICAL_SKILL_MD = CANONICAL_SKILL_DIR / "SKILL.md"
CANONICAL_OPENAI_YAML = CANONICAL_SKILL_DIR / "agents" / "openai.yaml"
GENERATED_MARKER = "<!-- GENERATED from skill/bili-learning-automation/SKILL.md; DO NOT EDIT DIRECTLY. -->"
ALLOWED_TOP_LEVEL_FILES = {"SKILL.md"}
ALLOWED_TOP_LEVEL_DIRS = {"agents", "assets", "references", "scripts"}
FORBIDDEN_FILE_NAMES = {
    ".env",
    "cookie.txt",
    "cookies.txt",
    "local.json",
    "bilibili_cookies.txt",
}


@dataclass(frozen=True)
class HostSpec:
    key: str
    skill_name: str
    install_dir: Path
    archive_name: str | None
    host_guard: str
    requires_openai_metadata: bool = False
    display_name: str = ""
    short_description: str = ""
    default_prompt: str = ""


PACKAGE_SPECS = (
    HostSpec(
        key="chatgpt",
        skill_name="bili-learning-automation-chatgpt",
        install_dir=REPO_ROOT / "chatgpt-skills" / "bili-learning-automation-chatgpt",
        archive_name="bili-learning-automation-chatgpt.zip",
        host_guard=(
            "ChatGPT 必须通过已授权的本地工作区桥接访问项目；只有远程沙箱而无法访问本机项目时停止，"
            "不要把项目、Cookie、runtime 或私人笔记复制到远程沙箱。"
        ),
        requires_openai_metadata=True,
        display_name="B站视频转笔记 · ChatGPT",
        short_description="通过本地工作区桥接生成 Obsidian B站学习笔记。",
        default_prompt=(
            "Use $bili-learning-automation-chatgpt to check the local workspace bridge and turn this Bilibili link "
            "into an Obsidian learning note."
        ),
    ),
    HostSpec(
        key="codex",
        skill_name="bili-learning-automation-codex",
        install_dir=REPO_ROOT / ".agents" / "skills" / "bili-learning-automation-codex",
        archive_name="bili-learning-automation-codex.zip",
        host_guard=(
            "Codex 优先使用当前本地工作区；当前目录不是项目时让用户打开或提供项目根目录。"
            "维护源码时保留与当前任务无关的工作区修改。"
        ),
        requires_openai_metadata=True,
        display_name="B站视频转笔记 · Codex",
        short_description="在本地项目中生成并维护 Obsidian B站学习笔记。",
        default_prompt=(
            "Use $bili-learning-automation-codex to check this local project and turn the supplied Bilibili link "
            "into an Obsidian learning note."
        ),
    ),
    HostSpec(
        key="hermes",
        skill_name="bili-learning-automation-hermes",
        install_dir=REPO_ROOT / "hermes-skills" / "bili-learning-automation-hermes",
        archive_name="bili-learning-automation-hermes.zip",
        host_guard=(
            "Hermes 只在 owner 私聊或等价受信任会话中执行本机项目操作；群聊或发送者范围不确定时停止并确认授权。"
        ),
    ),
    HostSpec(
        key="workbuddy",
        skill_name="bili-learning-automation-workbuddy",
        install_dir=REPO_ROOT / "workbuddy-skills" / "bili-learning-automation-workbuddy",
        archive_name="bili-learning-automation-workbuddy.zip",
        host_guard=(
            "WorkBuddy 只处理用户在当前会话明确提供或授权的 Bilibili 输入；项目位置不明确时让用户打开或提供根目录。"
        ),
    ),
)

# These repository-native install paths keep existing Junction-based setups working.
# Their SKILL.md files are generated from the same canonical source and are not separate sources of truth.
NATIVE_MIRROR_SPECS = (
    HostSpec(
        key="hermes-native",
        skill_name="bili-learning-automation",
        install_dir=REPO_ROOT / "hermes-skills" / "bili-learning-automation",
        archive_name=None,
        host_guard=(
            "Hermes 只在 owner 私聊或等价受信任会话中执行本机项目操作；如果安装目录自带 scripts bridge，"
            "可用它解决宿主路径/进程兼容，但所有业务规则仍来自共享核心。"
        ),
    ),
    HostSpec(
        key="workbuddy-native",
        skill_name="bili-learning-automation",
        install_dir=REPO_ROOT / "workbuddy-skills" / "bili-learning-automation",
        archive_name=None,
        host_guard=(
            "WorkBuddy 只处理用户在当前会话明确提供或授权的输入；如果安装目录自带 scripts bridge，"
            "可用它解决 Bash/PowerShell/PYTHONPATH 兼容，但所有业务规则仍来自共享核心。"
        ),
    ),
)

ALL_INSTALL_SPECS = PACKAGE_SPECS + NATIVE_MIRROR_SPECS


def _frontmatter_name_text(text: str) -> str:
    match = re.search(r"(?m)^name:\s*([a-z0-9-]+)\s*$", text)
    if not match:
        raise ValueError("SKILL.md 缺少有效的 name")
    return match.group(1)


def _split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"\A---\r?\n(?P<frontmatter>.*?)\r?\n---\r?\n(?P<body>.*)\Z", text, flags=re.DOTALL)
    if not match:
        raise ValueError("canonical SKILL.md 缺少有效 YAML frontmatter")
    return match.group("frontmatter"), match.group("body")


def _canonical_text() -> str:
    if not CANONICAL_SKILL_MD.is_file():
        raise ValueError(f"统一 Skill 真源不存在：{CANONICAL_SKILL_MD}")
    text = CANONICAL_SKILL_MD.read_text(encoding="utf-8")
    if _frontmatter_name_text(text) != "bili-learning-automation":
        raise ValueError("统一 Skill 真源的 name 必须是 bili-learning-automation")
    if GENERATED_MARKER in text:
        raise ValueError("统一 Skill 真源不能包含 generated marker")
    return text


def _canonical_description(frontmatter: str) -> str:
    match = re.search(r"(?m)^description:\s*(.+?)\s*$", frontmatter)
    if not match:
        raise ValueError("统一 Skill 真源缺少 description")
    return match.group(1)


def render_skill(spec: HostSpec) -> str:
    canonical = _canonical_text()
    frontmatter, body = _split_frontmatter(canonical)
    description = _canonical_description(frontmatter)
    rendered_frontmatter = f"---\nname: {spec.skill_name}\ndescription: {description}\n---"
    host_section = f"## 宿主边界\n\n{spec.host_guard}\n\n"
    return f"{rendered_frontmatter}\n\n{GENERATED_MARKER}\n\n{host_section}{body.lstrip()}"


def render_openai_yaml(spec: HostSpec) -> str:
    if not spec.requires_openai_metadata:
        raise ValueError(f"{spec.key} 不需要 OpenAI metadata")
    if not (spec.display_name and spec.short_description and spec.default_prompt):
        raise ValueError(f"{spec.key} 缺少 OpenAI metadata 配置")
    return (
        "interface:\n"
        f'  display_name: "{spec.display_name}"\n'
        f'  short_description: "{spec.short_description}"\n'
        f'  default_prompt: "{spec.default_prompt}"\n'
        "policy:\n"
        "  allow_implicit_invocation: true\n"
    )


def sync_install_exit(spec: HostSpec) -> list[str]:
    spec.install_dir.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []

    skill_path = spec.install_dir / "SKILL.md"
    expected_skill = render_skill(spec)
    current_skill = skill_path.read_text(encoding="utf-8") if skill_path.is_file() else None
    if current_skill != expected_skill:
        skill_path.write_text(expected_skill, encoding="utf-8", newline="\n")
        changed.append(str(skill_path.relative_to(REPO_ROOT)))

    openai_path = spec.install_dir / "agents" / "openai.yaml"
    if spec.requires_openai_metadata:
        openai_path.parent.mkdir(parents=True, exist_ok=True)
        expected_yaml = render_openai_yaml(spec)
        current_yaml = openai_path.read_text(encoding="utf-8") if openai_path.is_file() else None
        if current_yaml != expected_yaml:
            openai_path.write_text(expected_yaml, encoding="utf-8", newline="\n")
            changed.append(str(openai_path.relative_to(REPO_ROOT)))

    return changed


def check_install_exit(spec: HostSpec) -> list[str]:
    errors: list[str] = []
    skill_path = spec.install_dir / "SKILL.md"
    if not skill_path.is_file():
        errors.append(f"缺少生成文件：{skill_path.relative_to(REPO_ROOT)}")
    elif skill_path.read_text(encoding="utf-8") != render_skill(spec):
        errors.append(f"生成文件已漂移：{skill_path.relative_to(REPO_ROOT)}")

    if spec.requires_openai_metadata:
        openai_path = spec.install_dir / "agents" / "openai.yaml"
        if not openai_path.is_file():
            errors.append(f"缺少生成文件：{openai_path.relative_to(REPO_ROOT)}")
        elif openai_path.read_text(encoding="utf-8") != render_openai_yaml(spec):
            errors.append(f"生成文件已漂移：{openai_path.relative_to(REPO_ROOT)}")

    return errors


def validate_source(spec: HostSpec) -> list[Path]:
    if not spec.install_dir.is_dir():
        raise ValueError(f"Skill 安装出口不存在：{spec.install_dir}")

    files: list[Path] = []
    for path in sorted(spec.install_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Skill 包禁止包含符号链接：{path}")
        if not path.is_file():
            continue

        relative = path.relative_to(spec.install_dir)
        top = relative.parts[0]
        if len(relative.parts) == 1:
            if top not in ALLOWED_TOP_LEVEL_FILES:
                raise ValueError(f"Skill 根目录包含未允许文件：{relative}")
        elif top not in ALLOWED_TOP_LEVEL_DIRS:
            raise ValueError(f"Skill 包含未允许目录：{relative}")

        if path.name.lower() in FORBIDDEN_FILE_NAMES:
            raise ValueError(f"Skill 包疑似包含凭据或本机配置：{relative}")
        if "__pycache__" in relative.parts or path.suffix.lower() in {".pyc", ".pyo"}:
            raise ValueError(f"Skill 包包含 Python 缓存：{relative}")
        files.append(path)

    skill_files = [path for path in files if path.relative_to(spec.install_dir).as_posix() == "SKILL.md"]
    nested_skill_files = [path for path in files if path.name == "SKILL.md" and path not in skill_files]
    if len(skill_files) != 1 or nested_skill_files:
        raise ValueError(f"{spec.skill_name} 必须且只能包含一个根目录 SKILL.md")
    if _frontmatter_name_text(skill_files[0].read_text(encoding="utf-8")) != spec.skill_name:
        raise ValueError(f"{spec.skill_name} 的目录名/包名与 frontmatter name 不一致")
    if GENERATED_MARKER not in skill_files[0].read_text(encoding="utf-8"):
        raise ValueError(f"{spec.skill_name} 不是由统一 Skill 真源生成")

    if spec.requires_openai_metadata:
        openai_yaml = spec.install_dir / "agents" / "openai.yaml"
        if not openai_yaml.is_file():
            raise ValueError(f"{spec.skill_name} 缺少 agents/openai.yaml")
        yaml_text = openai_yaml.read_text(encoding="utf-8")
        expected_mention = "$" + spec.skill_name
        if expected_mention not in yaml_text:
            raise ValueError(f"{spec.skill_name} 的 default_prompt 必须引用正确的 Skill 名称")

    return files


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def build_package(spec: HostSpec, output_dir: Path) -> dict[str, object]:
    if spec.archive_name is None:
        raise ValueError(f"{spec.key} 不是可打包出口")
    files = validate_source(spec)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / spec.archive_name

    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in files:
            relative = path.relative_to(spec.install_dir).as_posix()
            archive_name = f"{spec.skill_name}/{relative}"
            archive.writestr(_zip_info(archive_name), path.read_bytes())

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    return {
        "host": spec.key,
        "skill": spec.skill_name,
        "archive": str(archive_path),
        "sha256": digest,
        "files": len(files),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从统一 Skill 真源同步 ChatGPT、Codex、Hermes、WorkBuddy 安装出口并生成独立 ZIP"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "dist",
        help="ZIP 输出目录；默认 <repo-root>/dist",
    )
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="只同步各宿主安装出口，不生成 ZIP",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检查各安装出口是否与统一 Skill 真源一致，不写文件或生成 ZIP",
    )
    args = parser.parse_args()

    if args.sync_only and args.check:
        raise SystemExit("--sync-only 与 --check 不能同时使用")

    _canonical_text()
    if not CANONICAL_OPENAI_YAML.is_file():
        raise SystemExit(f"统一 Skill 缺少 agents/openai.yaml：{CANONICAL_OPENAI_YAML}")

    if args.check:
        errors = [error for spec in ALL_INSTALL_SPECS for error in check_install_exit(spec)]
        if errors:
            print(json.dumps({"status": "skill_sources_out_of_sync", "errors": errors}, ensure_ascii=False, indent=2))
            raise SystemExit(1)
        print(json.dumps({"status": "skill_sources_in_sync", "canonical": str(CANONICAL_SKILL_DIR)}, ensure_ascii=False, indent=2))
        return

    changed = [item for spec in ALL_INSTALL_SPECS for item in sync_install_exit(spec)]
    if args.sync_only:
        print(
            json.dumps(
                {"status": "skill_sources_synced", "canonical": str(CANONICAL_SKILL_DIR), "changed": changed},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = (REPO_ROOT / output_dir).resolve()

    results = [build_package(spec, output_dir) for spec in PACKAGE_SPECS]
    print(
        json.dumps(
            {
                "status": "packages_ready",
                "canonical": str(CANONICAL_SKILL_DIR),
                "synced": changed,
                "packages": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
