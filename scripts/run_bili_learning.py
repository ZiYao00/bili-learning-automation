from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    src_dir = project_root / "src"
    if not (src_dir / "bili_learning" / "cli.py").is_file():
        raise SystemExit("未找到 bili-learning-automation 核心 CLI")

    os.chdir(project_root)
    sys.path.insert(0, str(src_dir))
    cli = importlib.import_module("bili_learning.cli")
    cli.main()


if __name__ == "__main__":
    main()
