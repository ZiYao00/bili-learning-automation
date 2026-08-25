from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

LOCK_STALE_SECONDS = 2 * 60 * 60
RESERVATION_SUFFIX = ".reservation.json"


class ReservationBusyError(RuntimeError):
    def __init__(self, bvid: str, age_seconds: int | None = None, job_dir: str | None = None) -> None:
        self.bvid = bvid
        self.age_seconds = age_seconds
        self.job_dir = job_dir
        super().__init__(f"该视频已有活动任务：{bvid}")


class LockBusyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Reservation:
    bvid: str
    path: Path


def _reservation_path(runtime_root: Path, bvid: str) -> Path:
    return runtime_root / "locks" / f"{bvid}{RESERVATION_SUFFIX}"


def _read_reservation(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _reservation_age_seconds(path: Path, payload: dict[str, object]) -> int:
    updated = payload.get("updated_at")
    if isinstance(updated, (int, float)):
        return max(0, int(time.time() - updated))
    try:
        return max(0, int(time.time() - path.stat().st_mtime))
    except FileNotFoundError:
        return 0


def _process_is_alive(pid: object) -> bool | None:
    """Return True/False when process liveness can be determined, else None."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            process_query_limited_information = 0x1000
            still_active = 259
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
            if not handle:
                return False if ctypes.get_last_error() == 87 else None
            exit_code = wintypes.DWORD()
            try:
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return None
                return exit_code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
        except (AttributeError, OSError):
            return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


def _remove_stale_reservation(path: Path, stale_seconds: int) -> None:
    payload = _read_reservation(path)
    age = _reservation_age_seconds(path, payload)
    owner_alive = _process_is_alive(payload.get("pid"))
    job_dir = payload.get("job_dir")
    if isinstance(job_dir, str) and job_dir:
        candidate = Path(job_dir)
        try:
            if candidate.is_dir():
                if (candidate / "job.json").is_file() and age <= stale_seconds:
                    return
                if not (candidate / "job.json").is_file():
                    if owner_alive is True:
                        return
                    if owner_alive is None and age <= stale_seconds:
                        return
                    if owner_alive is False:
                        try:
                            remove_job(path.parent.parent, candidate)
                        except (OSError, ValueError):
                            pass
        except OSError:
            if owner_alive is not False and age <= stale_seconds:
                return
    elif age <= stale_seconds and owner_alive is not False:
        # Between claim and bind, job_dir is intentionally empty. Keep it while
        # the owner lives. Older payloads without a PID keep the stale timeout.
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def claim_reservation(runtime_root: Path, bvid: str, stale_seconds: int = LOCK_STALE_SECONDS) -> Reservation:
    path = _reservation_path(runtime_root, bvid)
    path.parent.mkdir(parents=True, exist_ok=True)
    _remove_stale_reservation(path, stale_seconds)
    payload = {
        "bvid": bvid,
        "pid": os.getpid(),
        "created_at": time.time(),
        "updated_at": time.time(),
        "job_dir": None,
    }
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        current = _read_reservation(path)
        owner = current.get("job_dir")
        job_dir = owner if isinstance(owner, str) and owner else None
        raise ReservationBusyError(bvid, _reservation_age_seconds(path, current), job_dir) from exc
    try:
        os.write(fd, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    finally:
        os.close(fd)
    return Reservation(bvid=bvid, path=path)


def bind_reservation(reservation: Reservation, job_dir: Path) -> None:
    payload = _read_reservation(reservation.path)
    if payload.get("bvid") != reservation.bvid:
        raise RuntimeError("任务预约已失效，拒绝继续处理。")
    payload["job_dir"] = str(job_dir)
    payload["updated_at"] = time.time()
    temporary = reservation.path.with_name(reservation.path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(reservation.path)


def release_reservation(runtime_root: Path, bvid: str, job_dir: Path | None = None) -> None:
    path = _reservation_path(runtime_root, bvid)
    payload = _read_reservation(path)
    owner = payload.get("job_dir")
    if job_dir is not None and isinstance(owner, str) and owner and Path(owner) != job_dir:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


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


def cleanup_job(runtime_root: Path, path: Path) -> None:
    candidate = safe_job_path(runtime_root, path)
    bvid: str | None = None
    try:
        payload = json.loads((candidate / "job.json").read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("bvid"), str):
            bvid = payload["bvid"]
    except (OSError, json.JSONDecodeError):
        pass
    remove_job(runtime_root, candidate)
    if bvid:
        release_reservation(runtime_root, bvid, candidate)
        return

    # Incomplete jobs may be killed before job.json is written. Release the
    # reservation already bound to this job path instead of leaving a dead job.
    locks_dir = runtime_root / "locks"
    if not locks_dir.is_dir():
        return
    for reservation_path in locks_dir.glob(f"*{RESERVATION_SUFFIX}"):
        payload = _read_reservation(reservation_path)
        owner = payload.get("job_dir")
        if isinstance(owner, str) and owner and Path(owner).resolve() == candidate:
            try:
                reservation_path.unlink()
            except FileNotFoundError:
                pass
            break


def _remove_stale_lock(lock_path: Path, stale_seconds: int) -> None:
    try:
        age = time.time() - lock_path.stat().st_mtime
        raw_pid = lock_path.read_text(encoding="ascii", errors="ignore").strip()
    except FileNotFoundError:
        return
    try:
        pid: object = int(raw_pid)
    except ValueError:
        pid = None
    owner_alive = _process_is_alive(pid)
    if owner_alive is True:
        return
    if owner_alive is None and age <= stale_seconds:
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
        raise LockBusyError(f"已有任务正在处理：{lock_path.stem}") from exc
    finally:
        if fd is not None:
            os.close(fd)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


@contextmanager
def waiting_file_lock(lock_path: Path, timeout_seconds: float = 30.0) -> Iterator[None]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            with file_lock(lock_path):
                yield
                return
        except LockBusyError:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"等待锁超时：{lock_path.stem}") from None
            time.sleep(0.05)
