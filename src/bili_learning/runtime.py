from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

LOCK_STALE_SECONDS = 2 * 60 * 60
RESERVATION_SUFFIX = ".reservation.json"
RETIRED_DIR_NAME = "retired"


class ReservationBusyError(RuntimeError):
    def __init__(
        self,
        bvid: str,
        age_seconds: int | None = None,
        job_dir: str | None = None,
        *,
        recoverable: bool = False,
    ) -> None:
        self.bvid = bvid
        self.age_seconds = age_seconds
        self.job_dir = job_dir
        self.recoverable = recoverable
        super().__init__(f"该视频已有活动任务：{bvid}")


class LockBusyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Reservation:
    bvid: str
    path: Path


def _reservation_path(runtime_root: Path, bvid: str) -> Path:
    return runtime_root / "locks" / f"{bvid}{RESERVATION_SUFFIX}"


def _reservation_lock_path(runtime_root: Path, bvid: str) -> Path:
    return runtime_root / "locks" / f"{bvid}.reservation.lock"


def _read_reservation(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


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


def _reservation_is_complete_job(payload: dict[str, object]) -> bool:
    job_dir = payload.get("job_dir")
    if not isinstance(job_dir, str) or not job_dir:
        return False
    candidate = Path(job_dir)
    try:
        return candidate.is_dir() and (candidate / "job.json").is_file()
    except OSError:
        return False


def _release_payload(path: Path, payload: dict[str, object]) -> None:
    released = dict(payload)
    released["state"] = "released"
    released["pid"] = None
    released["updated_at"] = time.time()
    _write_json_atomic(path, released)


def _normalize_existing_reservation(path: Path, stale_seconds: int) -> dict[str, object]:
    payload = _read_reservation(path)
    if not payload:
        return {}
    if payload.get("state") == "released":
        return payload

    age = _reservation_age_seconds(path, payload)
    owner_alive = _process_is_alive(payload.get("pid"))
    complete_job = _reservation_is_complete_job(payload)

    # A dead owner with a complete job is intentionally preserved so prepare can
    # recover the already-collected materials instead of downloading them again.
    if owner_alive is False and complete_job:
        return payload

    job_dir = payload.get("job_dir")
    if isinstance(job_dir, str) and job_dir:
        candidate = Path(job_dir)
        try:
            if not candidate.exists():
                _release_payload(path, payload)
                return _read_reservation(path)
            if owner_alive is False and candidate.is_dir() and not (candidate / "job.json").is_file():
                remove_job(path.parent.parent, candidate)
                _release_payload(path, payload)
                return _read_reservation(path)
        except OSError:
            pass

    # Dead/incomplete reservations are reusable immediately. Legacy reservations
    # without a usable owner are also reusable after the stale window.
    if owner_alive is False or age > stale_seconds:
        _release_payload(path, payload)
        return _read_reservation(path)
    return payload


def claim_reservation(runtime_root: Path, bvid: str, stale_seconds: int = LOCK_STALE_SECONDS) -> Reservation:
    path = _reservation_path(runtime_root, bvid)
    path.parent.mkdir(parents=True, exist_ok=True)
    with waiting_file_lock(_reservation_lock_path(runtime_root, bvid)):
        current = _normalize_existing_reservation(path, stale_seconds) if path.exists() else {}
        if current and current.get("state") != "released":
            owner = current.get("job_dir")
            job_dir = owner if isinstance(owner, str) and owner else None
            owner_alive = _process_is_alive(current.get("pid"))
            raise ReservationBusyError(
                bvid,
                _reservation_age_seconds(path, current),
                job_dir,
                recoverable=owner_alive is False and _reservation_is_complete_job(current),
            )

        payload: dict[str, object] = {
            "bvid": bvid,
            "state": "active",
            "pid": os.getpid(),
            "created_at": time.time(),
            "updated_at": time.time(),
            "job_dir": None,
        }
        _write_json_atomic(path, payload)
    return Reservation(bvid=bvid, path=path)


def bind_reservation(reservation: Reservation, job_dir: Path) -> None:
    runtime_root = reservation.path.parent.parent
    with waiting_file_lock(_reservation_lock_path(runtime_root, reservation.bvid)):
        payload = _read_reservation(reservation.path)
        if payload.get("bvid") != reservation.bvid or payload.get("state") == "released":
            raise RuntimeError("任务预约已失效，拒绝继续处理。")
        payload["job_dir"] = str(job_dir)
        payload["updated_at"] = time.time()
        _write_json_atomic(reservation.path, payload)


def release_reservation(runtime_root: Path, bvid: str, job_dir: Path | None = None) -> None:
    path = _reservation_path(runtime_root, bvid)
    with waiting_file_lock(_reservation_lock_path(runtime_root, bvid)):
        payload = _read_reservation(path)
        if not payload:
            return
        owner = payload.get("job_dir")
        if job_dir is not None and isinstance(owner, str) and owner and Path(owner) != job_dir:
            return
        _release_payload(path, payload)


def safe_job_path(runtime_root: Path, path: Path) -> Path:
    root = runtime_root.resolve()
    candidate = path.resolve()
    if candidate == root or root not in candidate.parents:
        raise ValueError("拒绝清理运行目录之外的路径。")
    return candidate


def _next_retired_path(runtime_root: Path, candidate: Path) -> Path:
    retired_root = runtime_root / RETIRED_DIR_NAME
    retired_root.mkdir(parents=True, exist_ok=True)
    destination = retired_root / candidate.name
    sequence = 2
    while destination.exists():
        destination = retired_root / f"{candidate.name}-{sequence}"
        sequence += 1
    return destination


def remove_job(runtime_root: Path, path: Path) -> Path | None:
    """Retire an active job without requiring delete permission.

    The historical public name is kept for caller compatibility. Normal task
    success no longer depends on physical deletion; retired jobs can be purged by
    a separate maintenance process outside the business-critical lifecycle.
    """
    candidate = safe_job_path(runtime_root, path)
    if not candidate.exists() or candidate.is_symlink():
        return None
    if candidate.parent.name == RETIRED_DIR_NAME:
        return candidate
    destination = _next_retired_path(runtime_root, candidate)
    candidate.replace(destination)
    return destination


def cleanup_job(runtime_root: Path, path: Path) -> Path | None:
    candidate = safe_job_path(runtime_root, path)
    bvid: str | None = None
    try:
        payload = json.loads((candidate / "job.json").read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("bvid"), str):
            bvid = payload["bvid"]
    except (OSError, json.JSONDecodeError):
        pass

    retired = remove_job(runtime_root, candidate)
    if bvid:
        release_reservation(runtime_root, bvid, candidate)
        return retired

    # Incomplete jobs may be killed before job.json is written. Release the
    # reservation bound to this job path without deleting the reservation file.
    locks_dir = runtime_root / "locks"
    if not locks_dir.is_dir():
        return retired
    for reservation_path in locks_dir.glob(f"*{RESERVATION_SUFFIX}"):
        payload = _read_reservation(reservation_path)
        owner = payload.get("job_dir")
        if isinstance(owner, str) and owner and Path(owner).resolve() == candidate:
            _release_payload(reservation_path, payload)
            break
    return retired


def _try_os_lock(file_obj: object) -> bool:
    if os.name == "nt":
        import msvcrt

        file_obj.seek(0)  # type: ignore[attr-defined]
        try:
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
        except OSError:
            return False
        return True

    import fcntl

    try:
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
    except (BlockingIOError, OSError):
        return False
    return True


def _unlock_os_file(file_obj: object) -> None:
    if os.name == "nt":
        import msvcrt

        file_obj.seek(0)  # type: ignore[attr-defined]
        msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        return

    import fcntl

    fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]


@contextmanager
def file_lock(lock_path: Path, stale_seconds: int = LOCK_STALE_SECONDS) -> Iterator[None]:
    del stale_seconds  # Kept in the signature for backward compatibility.
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    file_obj = lock_path.open("a+b")
    try:
        file_obj.seek(0, os.SEEK_END)
        if file_obj.tell() == 0:
            file_obj.write(b"0")
            file_obj.flush()
        if not _try_os_lock(file_obj):
            raise LockBusyError(f"已有任务正在处理：{lock_path.stem}")
        try:
            yield
        finally:
            _unlock_os_file(file_obj)
    finally:
        file_obj.close()


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
