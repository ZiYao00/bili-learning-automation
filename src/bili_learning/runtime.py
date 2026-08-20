from __future__ import annotations

import os
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

LOCK_STALE_SECONDS = 60 * 60


def safe_job_path(runtime_root: Path, path: Path) -> Path:
    root = runtime_root.resolve()
    candidate = path.resolve()
    if candidate == root or root not in candidate.parents:
        raise ValueError("拒绝清理运行目录之外的路径。")
    return candidate


def remove_job(runtime_root: Path, path: Path) -> None:
    candidate = safe_job_path(runtime_root, path)
    if candidate.exists() and not candidate.is_symlink():
        shutil.rmtree(candidate)


def _remove_stale_lock(lock_path: Path, stale_seconds: int) -> None:
    try:
        age = time.time() - lock_path.stat().st_mtime
    except FileNotFoundError:
        return
    if age <= stale_seconds:
        return
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


@contextmanager
def file_lock(lock_path: Path, stale_seconds: int = LOCK_STALE_SECONDS) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    _remove_stale_lock(lock_path, stale_seconds)
    fd: int | None = None
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("ascii"))
        yield
    except FileExistsError as exc:
        raise RuntimeError(f"已有任务正在处理：{lock_path.stem}") from exc
    finally:
        if fd is not None:
            os.close(fd)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
