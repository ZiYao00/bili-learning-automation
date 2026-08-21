#!/usr/bin/env python3
"""Hermes compatibility launcher for the agent-neutral finalize command."""
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
    sys.argv = ["bili-learning", "--project-root", str(PROJECT_ROOT), "finalize", *sys.argv[1:]]
    main()
