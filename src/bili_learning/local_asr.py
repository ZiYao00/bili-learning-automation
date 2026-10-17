from __future__ import annotations

import json
import mimetypes
import secrets
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib import error, request

from .config import (
    YTDLP_RELATIVE_PATH,
    DependencyError,
    Settings,
)
from .input_resolver import ResolvedInput, resolve_input

LOCAL_ASR_SERVICE_NAME = "local-ASR-service"
HEALTH_TIMEOUT_SECONDS = 3
TRANSCRIBE_TIMEOUT_SECONDS = 3 * 60 * 60 + 60
DOWNLOAD_TIMEOUT_SECONDS = 900


class LocalAsrError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _endpoint(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def check_local_asr_health(
    base_url: str,
    *,
    timeout: int = HEALTH_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    req = request.Request(
        _endpoint(base_url, "/health"),
        method="GET",
        headers={"Accept": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except (error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise LocalAsrError(
            "local_asr_unavailable",
            f"{LOCAL_ASR_SERVICE_NAME} 不可用：{reason}",
        ) from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise LocalAsrError("local_asr_invalid_response", "local-ASR-service /health 返回了非 JSON 响应。") from exc

    if not isinstance(data, dict):
        raise LocalAsrError("local_asr_invalid_response", "local-ASR-service /health 响应结构无效。")
    if data.get("status") != "ok" or data.get("service") != LOCAL_ASR_SERVICE_NAME:
        raise LocalAsrError("local_asr_not_ready", "local-ASR-service 尚未进入 ready 状态。")
    for field in ("ffmpeg", "vad", "punctuation"):
        if data.get(field) is not True:
            raise LocalAsrError("local_asr_not_ready", f"local-ASR-service 健康检查未满足：{field}=true")
    return data


def health_report(settings: Settings, *, timeout: int = HEALTH_TIMEOUT_SECONDS) -> tuple[dict[str, Any], int]:
    try:
        health = check_local_asr_health(settings.local_asr_base_url, timeout=timeout)
    except LocalAsrError as exc:
        return (
            {
                "schema_version": 1,
                "status": "unavailable",
                "code": exc.code,
                "provider": LOCAL_ASR_SERVICE_NAME,
                "base_url": settings.local_asr_base_url,
                "message": str(exc),
            },
            2,
        )

    return (
        {
            "schema_version": 1,
            "status": "ready",
            "provider": LOCAL_ASR_SERVICE_NAME,
            "base_url": settings.local_asr_base_url,
            "device": health.get("device"),
            "model": health.get("model"),
            "ffmpeg": health.get("ffmpeg"),
            "vad": health.get("vad"),
            "punctuation": health.get("punctuation"),
            "queue": health.get("queue"),
        },
        0,
    )


def _download_audio(settings: Settings, canonical_url: str, temp_dir: Path) -> Path:
    ytdlp = settings.ytdlp.path
    if ytdlp is None:
        raise DependencyError(
            "ytdlp_not_configured",
            f"项目缺少 {YTDLP_RELATIVE_PATH.as_posix()}；ASR 同样只使用项目内 EXE。",
        )
    if not ytdlp.is_file():
        raise DependencyError("ytdlp_path_invalid", f"yt-dlp 路径不存在或不是文件（来源：{settings.ytdlp.source}）。")
    if not settings.cookie_file.is_file():
        raise DependencyError("cookie_file_missing", "Bilibili Cookie 文件不存在或未配置。")

    output = temp_dir / "source.%(ext)s"
    command = [
        str(ytdlp),
        "--ignore-config",
        "--no-cache-dir",
        "--cookies",
        str(settings.cookie_file),
        "--no-playlist",
        "--format",
        "bestaudio",
        "--paths",
        str(temp_dir),
        "--output",
        str(output),
        canonical_url,
    ]
    try:
        completed = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise LocalAsrError("asr_audio_download_timeout", "ASR 临时音轨下载超时。") from exc
    if completed.returncode:
        raise LocalAsrError(
            "asr_audio_download_failed",
            "ASR 临时音轨下载失败；请检查 Cookie、视频可访问性或音频流。",
        )

    candidates = [
        path
        for path in temp_dir.iterdir()
        if path.is_file() and path.suffix.lower() not in {".json", ".part", ".ytdl"}
    ]
    if len(candidates) != 1:
        raise LocalAsrError("asr_audio_missing", "yt-dlp 已执行，但未取得唯一的临时音轨。")
    return candidates[0]


def _multipart_body(audio: Path) -> tuple[Iterable[bytes], str, int]:
    """Stream a known-length multipart upload without materializing the media in RAM."""
    boundary = f"----bili-local-asr-{secrets.token_hex(12)}"
    mime = mimetypes.guess_type(audio.name)[0] or "application/octet-stream"
    filename = audio.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
    fields = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'
        for key, value in (("model", "custom"), ("language", "zh"), ("response_format", "verbose_json"))
    ]
    prefix = ("".join(fields) + (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    )).encode("utf-8")
    suffix = f"\r\n--{boundary}--\r\n".encode()
    total_bytes = len(prefix) + audio.stat().st_size + len(suffix)

    def chunks() -> Iterable[bytes]:
        yield prefix
        with audio.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                yield block
        yield suffix

    return chunks(), boundary, total_bytes


def transcribe_local_file(
    base_url: str,
    audio: Path,
    *,
    timeout: int = TRANSCRIBE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    body, boundary, content_length = _multipart_body(audio)
    req = request.Request(
        _endpoint(base_url, "/v1/audio/transcriptions"),
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(content_length),
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise LocalAsrError("local_asr_http_error", f"local-ASR-service 返回 HTTP {exc.code}：{detail}") from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise LocalAsrError(
            "local_asr_outcome_unknown",
            f"ASR 请求连接中断或超时，无法确认服务端是否已完成转录：{reason}。"
            "请先检查 /health.queue 和服务状态，不得直接重复提交。",
        ) from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise LocalAsrError("local_asr_invalid_response", "local-ASR-service 转写返回了非 JSON 响应。") from exc
    if not isinstance(data, dict):
        raise LocalAsrError("local_asr_invalid_response", "local-ASR-service 转写响应结构无效。")
    text = str(data.get("text") or "").strip()
    if data.get("status") != "ok" or not text:
        raise LocalAsrError("local_asr_empty_transcript", "local-ASR-service 没有返回可用纯文本。")
    data["text"] = text
    return data


def transcribe_bilibili(
    settings: Settings,
    message: str,
    *,
    health_timeout: int = HEALTH_TIMEOUT_SECONDS,
    transcribe_timeout: int = TRANSCRIBE_TIMEOUT_SECONDS,
) -> tuple[ResolvedInput, dict[str, Any]]:
    resolved = resolve_input(message)
    check_local_asr_health(settings.local_asr_base_url, timeout=health_timeout)
    with tempfile.TemporaryDirectory(prefix="bili-learning-asr-") as temp:
        audio = _download_audio(settings, resolved.canonical_url, Path(temp))
        result = transcribe_local_file(settings.local_asr_base_url, audio, timeout=transcribe_timeout)
    return resolved, result
