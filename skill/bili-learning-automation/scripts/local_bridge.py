#!/usr/bin/env python3
"""Local Agent bridge for the canonical bili-learning-automation Skill."""

from __future__ import annotations

import sys
from pathlib import Path

PREPARE_COMMANDS = {"prepare", "prepare-transcript", "prepare-description"}


def find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "AGENTS.md").is_file()
            and (candidate / "scripts" / "run_bili_learning.py").is_file()
        ):
            return candidate
    raise SystemExit("Unable to locate bili-learning-automation project root from the installed Skill.")


def main() -> None:
    project_root = find_project_root()
    src_root = project_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

    from bili_learning.cli import main as cli_main

    args = sys.argv[1:]
    bridge_path = str(Path(__file__).resolve())
    if args and args[0].startswith("--cleanup-job"):
        args = ["prepare", "--cleanup-runner", bridge_path, *args]
    elif args and args[0] in PREPARE_COMMANDS:
        args = [args[0], "--cleanup-runner", bridge_path, *args[1:]]

    sys.argv = ["bili-learning", "--project-root", str(project_root), *args]
    cli_main()


if __name__ == "__main__":
    main()
