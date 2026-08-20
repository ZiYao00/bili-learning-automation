from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

BVID_RE = re.compile(r"\b(BV[0-9A-Za-z]{10})\b", re.IGNORECASE)
ALLOWED_HOSTS = {
    "bilibili.com",
    "www.bilibili.com",
    "m.bilibili.com",
    "b23.tv",
    "www.b23.tv",
}
MAX_REDIRECTS = 5
DEFAULT_TIMEOUT = 10


@dataclass(frozen=True)
class ResolvedInput:
    bvid: str
    canonical_url: str


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, max_redirects: int = MAX_REDIRECTS) -> None:
        self._redirect_count = 0
        self._max_redirects = max_redirects
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        self._redirect_count += 1
        if self._redirect_count > self._max_redirects:
            raise ValueError("Bilibili 短链重定向次数过多")
        _assert_allowed_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _hostname(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return (parsed.hostname or "").lower()


def _assert_allowed_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or _hostname(url) not in ALLOWED_HOSTS:
        raise ValueError("只允许解析 Bilibili 官方链接")


def _extract_bvid(value: str) -> str | None:
    match = BVID_RE.search(value)
    return match.group(1) if match else None


def resolve_input(value: str, timeout: int = DEFAULT_TIMEOUT) -> ResolvedInput:
    direct = _extract_bvid(value)
    if direct:
        return ResolvedInput(direct, f"https://www.bilibili.com/video/{direct}/")

    urls = re.findall(r"https?://[^\s<>'\"]+", value)
    if not urls:
        raise ValueError("未识别到 Bilibili BVID 或官方链接；请发送复制后的 B站链接或 BV 号。")

    candidate = urls[0].rstrip("。)，)]}")
    _assert_allowed_url(candidate)
    if _hostname(candidate) not in {"b23.tv", "www.b23.tv"}:
        raise ValueError("链接中未识别到 BVID；请重新复制 Bilibili 视频链接。")

    opener = urllib.request.build_opener(_SafeRedirectHandler())
    request = urllib.request.Request(candidate, method="HEAD", headers={"User-Agent": "bili-learning/0.1"})
    try:
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
    except urllib.error.HTTPError as exc:
        # Some short-link endpoints reject HEAD; retry with a small GET request.
        if exc.code not in {403, 405}:
            raise ValueError("Bilibili 短链解析失败") from exc
        request = urllib.request.Request(candidate, method="GET", headers={"User-Agent": "bili-learning/0.1"})
        try:
            with opener.open(request, timeout=timeout) as response:
                final_url = response.geturl()
        except (OSError, urllib.error.URLError, ValueError) as inner:
            raise ValueError("Bilibili 短链解析失败") from inner
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise ValueError("Bilibili 短链解析失败") from exc

    _assert_allowed_url(final_url)
    bvid = _extract_bvid(final_url)
    if not bvid:
        raise ValueError("Bilibili 短链未解析出 BVID")
    return ResolvedInput(bvid, f"https://www.bilibili.com/video/{bvid}/")
