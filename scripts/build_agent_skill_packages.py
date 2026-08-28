from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
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
class PackageSpec:
    source: Path
    skill_name: str
    archive_name: str
    requires_openai_metadata: bool = False


PACKAGE_SPECS = (
    PackageSpec(
        source=REPO_ROOT / "chatgpt-skills" / "bili-learning-automation-chatgpt",
        skill_name="bili-learning-automation-chatgpt",
        archive_name="bili-learning-automation-chatgpt.zip",
        requires_openai_metadata=True,
    ),
    PackageSpec(
        source=REPO_ROOT / ".agents" / "skills" / "bili-learning-automation-codex",
        skill_name="bili-learning-automation-codex",
        archive_name="bili-learning-automation-codex.zip",
        requires_openai_metadata=True,
    ),
    PackageSpec(
        source=REPO_ROOT / "hermes-skills" / "bili-learning-automation-hermes",
        skill_name="bili-learning-automation-hermes",
        archive_name="bili-learning-automation-hermes.zip",
    ),
    PackageSpec(
        source=REPO_ROOT / "workbuddy-skills" / "bili-learning-automation-workbuddy",
        skill_name="bili-learning-automation-workbuddy",
        archive_name="bili-learning-automation-workbuddy.zip",
    ),
)


def _frontmatter_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    match = re.search(r"(?m)^name:\s*([a-z0-9-]+)\s*$", text)
    if not match:
        raise ValueError(f"{skill_md} 缺少有效的 name")
    return match.group(1)


def validate_source(spec: PackageSpec) -> list[Path]:
    if not spec.source.is_dir():
        raise ValueError(f"Skill 源目录不存在：{spec.source}")

    files: list[Path] = []
    for path in sorted(spec.source.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Skill 包禁止包含符号链接：{path}")
        if not path.is_file():
            continue

        relative = path.relative_to(spec.source)
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

    skill_files = [path for path in files if path.relative_to(spec.source).as_posix() == "SKILL.md"]
    nested_skill_files = [path for path in files if path.name == "SKILL.md" and path not in skill_files]
    if len(skill_files) != 1 or nested_skill_files:
        raise ValueError(f"{spec.skill_name} 必须且只能包含一个根目录 SKILL.md")
    if _frontmatter_name(skill_files[0]) != spec.skill_name:
        raise ValueError(f"{spec.skill_name} 的目录名与 frontmatter name 不一致")

    if spec.requires_openai_metadata:
        openai_yaml = spec.source / "agents" / "openai.yaml"
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


def build_package(spec: PackageSpec, output_dir: Path) -> dict[str, object]:
    files = validate_source(spec)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / spec.archive_name

    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in files:
            relative = path.relative_to(spec.source).as_posix()
            archive_name = f"{spec.skill_name}/{relative}"
            archive.writestr(_zip_info(archive_name), path.read_bytes())

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    return {
        "skill": spec.skill_name,
        "archive": str(archive_path),
        "sha256": digest,
        "files": len(files),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 ChatGPT、Codex、Hermes 与 WorkBuddy 独立 Skill 安装包")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "dist",
        help="ZIP 输出目录；默认 <repo-root>/dist",
    )
    args = parser.parse_args()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = (REPO_ROOT / output_dir).resolve()

    results = [build_package(spec, output_dir) for spec in PACKAGE_SPECS]
    print(json.dumps({"status": "packages_ready", "packages": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
