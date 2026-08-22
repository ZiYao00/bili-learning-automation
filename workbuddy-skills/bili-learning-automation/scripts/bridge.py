#!/usr/bin/env python3
"""WorkBuddy thin launcher that resolves the repository from the installed junction."""
# ruff: noqa: E402, I001

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bili_learning.cli import main  # noqa: E402


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0].startswith("--cleanup-job"):
        args = ["prepare", "--cleanup-runner", str(Path(__file__).resolve()), *args]
    elif args and args[0] == "prepare":
        args = ["prepare", "--cleanup-runner", str(Path(__file__).resolve()), *args[1:]]
    sys.argv = ["bili-learning", "--project-root", str(PROJECT_ROOT), *args]
    main()
