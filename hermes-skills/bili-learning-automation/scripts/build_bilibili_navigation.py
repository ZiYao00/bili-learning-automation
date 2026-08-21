#!/usr/bin/env python3
"""Generate Obsidian navigation pages from the project taxonomy."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bili_learning.config import load_settings  # noqa: E402
from bili_learning.navigation import build_navigation  # noqa: E402


def main() -> None:
    build_navigation(load_settings(PROJECT_ROOT))


if __name__ == "__main__":
    main()
