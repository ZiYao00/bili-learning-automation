#!/usr/bin/env python3
"""Run local preflight checks for B站视频转笔记 without reading credential contents."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bili_learning.config import load_settings  # noqa: E402
from bili_learning.doctor import run_doctor  # noqa: E402


def main() -> None:
    code, lines = run_doctor(load_settings(PROJECT_ROOT))
    print("\n".join(lines))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
