"""Manual ASR fallback for Bilibili videos that truly have no usable subtitles.

This script is intentionally outside the normal Skill workflow. Run it only after
confirming that the source video has no extractable subtitle track.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib import error, request

DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "FunAudioLLM/SenseVoiceSmall"
MAX_BYTES = 50 * 1024 * 1024
MAX_DURATION = 3600.0


def load_api_key(path: Path | None, project_root: Path) -> str:
    env_key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if env_key:
        return env_key

    if path is not None:
        if not path.is_file():
            raise RuntimeError(f"API Key 文件不存在：{path}")
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                line = line.split("=", 1)[1].strip().strip('"\'')
            if line:
                return line
        raise RuntimeError(f"API Key 文件没有可用内容：{path}")

    config = load_project_config(project_root)
    siliconflow = config.get("siliconflow") if isinstance(config, dict) else None
    configured = str(siliconflow.get("api_key") or "").strip() if isinstance(siliconflow, dict) else ""
    if configured:
        return configured

    raise RuntimeError(
        "缺少 SiliconFlow API Key：在 config/local.json 的 siliconflow.api_key 中配置，"
        "或设置 SILICONFLOW_API_KEY / 传入 --api-key-file。"
    )


def load_project_config(project_root: Path) -> dict:
    path = project_root / "config" / "local.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_ytdlp(explicit: str | None, project_root: Path) -> str:
    if explicit:
        return explicit
    config = load_project_config(project_root)
    configured = str(config.get("ytdlp") or "").strip()
    if configured and Path(configured).is_file():
        return configured
    found = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
    if found:
        return found
    raise RuntimeError("未找到 yt-dlp。可使用 --ytdlp 指定路径，或在 config/local.json 配置 ytdlp。")


def resolve_cookie(project_root: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    for name in ("cookies_netscape.txt", "bilibili_cookies.txt", "Cookie.txt"):
        candidate = project_root / "key" / name
        if candidate.is_file():
            return candidate
    return None


def download_audio(ytdlp: str, url: str, temp_dir: Path, cookie: Path | None) -> tuple[Path, float]:
    output = temp_dir / "%(id)s.%(ext)s"
    command = [
        ytdlp,
        "--ignore-config",
        "--no-cache-dir",
        "--no-playlist",
        "--format",
        "worstaudio/bestaudio",
        "--write-info-json",
        "--paths",
        str(temp_dir),
        "--output",
        str(output),
    ]
    if cookie is not None and cookie.is_file():
        command += ["--cookies", str(cookie)]
    command.append(url)
    completed = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip().splitlines()[-1:] or ["未知错误"]
        raise RuntimeError(f"yt-dlp 音频下载失败：{detail[0]}")

    media = [p for p in temp_dir.iterdir() if p.is_file() and p.suffix.lower() not in {".json", ".part", ".ytdl"}]
    if not media:
        raise RuntimeError("yt-dlp 已执行，但未找到下载后的音频文件。")
    audio = max(media, key=lambda p: p.stat().st_mtime)

    duration = 0.0
    info_files = list(temp_dir.glob("*.info.json"))
    if info_files:
        try:
            info = json.loads(info_files[0].read_text(encoding="utf-8"))
            duration = float(info.get("duration") or 0)
        except (OSError, ValueError, json.JSONDecodeError):
            duration = 0.0
    return audio, duration


def multipart_body(audio: Path, model: str) -> tuple[bytes, str]:
    boundary = f"----bili-asr-{secrets.token_hex(12)}"
    mime = mimetypes.guess_type(audio.name)[0] or "application/octet-stream"
    chunks: list[bytes] = []

    def field(name: str, value: str) -> None:
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            value.encode("utf-8"),
            b"\r\n",
        ])

    field("model", model)
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{audio.name}"\r\n'.encode(),
        f"Content-Type: {mime}\r\n\r\n".encode(),
        audio.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), boundary


def transcribe(audio: Path, api_key: str, base_url: str, model: str, timeout: int) -> dict:
    body, boundary = multipart_body(audio, model)
    endpoint = base_url.rstrip("/") + "/audio/transcriptions"
    req = request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"SiliconFlow STT 返回 HTTP {exc.code}：{detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"无法连接 SiliconFlow STT：{exc.reason}") from exc
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SiliconFlow STT 返回了非 JSON 响应。") from exc
    text = str(data.get("text") or "").strip() if isinstance(data, dict) else ""
    if not text:
        raise RuntimeError("SiliconFlow STT 响应中没有可用 text。")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="B站无字幕视频应急转录：yt-dlp 只取音频，再调用 SiliconFlow STT。")
    parser.add_argument("url", help="Bilibili 视频 URL / BV URL")
    parser.add_argument(
        "--api-key-file",
        type=Path,
        help="可选 API Key 文本文件；默认读取 config/local.json 的 siliconflow.api_key，也可使用 SILICONFLOW_API_KEY",
    )
    parser.add_argument("--output", type=Path, default=Path("transcript.txt"), help="转录文本输出路径")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--ytdlp", help="yt-dlp 可执行文件路径；默认读取 config/local.json，再查 PATH")
    parser.add_argument("--cookies", type=Path, help="可选 Netscape Cookie 文件；默认尝试项目 key/ 下已有 Cookie")
    parser.add_argument("--timeout", type=int, default=180, help="STT HTTP 超时秒数")
    parser.add_argument("--keep-audio", action="store_true", help="保留下载音频到输出文件旁边，默认自动清理")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    try:
        api_key = load_api_key(args.api_key_file, project_root)
        ytdlp = resolve_ytdlp(args.ytdlp, project_root)
        cookie = resolve_cookie(project_root, args.cookies)
        output = args.output.resolve()
        if output.exists():
            raise RuntimeError(f"输出文件已存在，不覆盖：{output}")
        output.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="bili-asr-") as tmp:
            temp_dir = Path(tmp)
            print("[1/3] 下载最低码率音轨…")
            audio, duration = download_audio(ytdlp, args.url, temp_dir, cookie)
            size = audio.stat().st_size
            if size > MAX_BYTES:
                raise RuntimeError(f"音频约 {size / 1024 / 1024:.1f}MB，超过 SiliconFlow 50MB 单文件上限。")
            if duration > MAX_DURATION:
                raise RuntimeError(f"视频约 {duration / 60:.1f} 分钟，超过当前 1 小时单次转录上限。")

            print(f"[2/3] 调用 SiliconFlow STT（{args.model}）…")
            result = transcribe(audio, api_key, args.base_url, args.model, args.timeout)
            output.write_text(str(result["text"]).strip() + "\n", encoding="utf-8")

            if args.keep_audio:
                kept = output.with_suffix(audio.suffix)
                if kept.exists():
                    raise RuntimeError(f"音频目标已存在，不覆盖：{kept}")
                shutil.copy2(audio, kept)
                print(f"音频已保留：{kept}")

        print(f"[3/3] 完成：{output}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
