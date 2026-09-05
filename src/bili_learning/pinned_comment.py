from __future__ import annotations

import html
import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .resource_access import detect_resource_access_notices
from .source import SourceMaterial

COMMENT_ENDPOINT = "https://api.bilibili.com/x/v2/reply"
COMMENT_TIMEOUT_SECONDS = 6.0
MAX_COMMENT_RESPONSE_BYTES = 1024 * 1024
PINNED_COMMENT_WHITELIST = Path("config/pinned-comment-whitelist.local.json")

_BV_ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
_BV_XOR_CODE = 23442827791579
_BV_MASK = (1 << 51) - 1
_BVID_RE = re.compile(r"^BV[0-9A-Za-z]{10}$", re.IGNORECASE)
_RESOURCE_WORD = r"(?:工作流|资源|资料|模型|提示词|整合包|脚本|插件|项目文件|工程文件|文件|下载链接|链接)"
_COMMENT_WORD = r"(?:置顶评论|顶置评论|评论区(?:置顶|顶置)?|评论里|评论中|评论)"
_DIRECT_COMMENT_RESOURCE_PATTERNS = (
    re.compile(
        rf"{_RESOURCE_WORD}.{{0,12}}(?:在|见|放在|放到|位于|查看|前往|通过).{{0,10}}{_COMMENT_WORD}",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        rf"{_COMMENT_WORD}.{{0,10}}(?:有|放着|放了|提供|发布|查看|获取|领取|下载).{{0,12}}{_RESOURCE_WORD}",
        re.IGNORECASE | re.DOTALL,
    ),
)


def bvid_to_aid(bvid: str) -> int:
    """Convert a modern 12-character BVID to its numeric AID locally."""

    value = bvid.strip()
    if not _BVID_RE.fullmatch(value):
        raise ValueError("无效的 BVID")
    chars = list(value)
    chars[3], chars[9] = chars[9], chars[3]
    chars[4], chars[7] = chars[7], chars[4]
    encoded = chars[3:]

    lookup = {character: index for index, character in enumerate(_BV_ALPHABET)}
    total = 0
    for character in encoded:
        try:
            index = lookup[character]
        except KeyError as exc:
            raise ValueError("BVID 包含无效字符") from exc
        total = total * len(_BV_ALPHABET) + index
    return (total & _BV_MASK) ^ _BV_XOR_CODE


def _source_text(source: SourceMaterial) -> str:
    path = source.path
    if path is None or not Path(path).is_file():
        return ""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def should_lookup_pinned_comment(description: str, source: SourceMaterial) -> bool:
    """Return True only when the current source explicitly points resource retrieval to comments."""

    notices = detect_resource_access_notices(description, source)
    if any("评论/关键词" in str(notice.get("condition") or "") for notice in notices):
        return True

    combined = html.unescape("\n".join(part for part in (description, _source_text(source)) if part))
    combined = re.sub(r"\s+", " ", combined)
    return any(pattern.search(combined) for pattern in _DIRECT_COMMENT_RESOURCE_PATTERNS)


def is_pinned_comment_whitelisted(project_root: Path, info: dict[str, Any]) -> bool:
    """Match an uploader identity against the user's local comment-resource whitelist."""

    path = project_root / PINNED_COMMENT_WHITELIST
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    uploaders = payload.get("uploaders") if isinstance(payload, dict) else None
    if not isinstance(uploaders, list):
        return False

    uploader_name = str(info.get("uploader") or "").strip().casefold()
    uploader_id = str(info.get("uploader_id") or "").strip()
    for item in uploaders:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip().casefold()
        ids = item.get("uploader_ids")
        ids = {str(value).strip() for value in ids} if isinstance(ids, list) else set()
        if uploader_id and uploader_id in ids:
            return True
        if uploader_name and name and uploader_name == name:
            return True
    return False


def _read_limited(response: Any) -> bytes:
    payload = response.read(MAX_COMMENT_RESPONSE_BYTES + 1)
    if len(payload) > MAX_COMMENT_RESPONSE_BYTES:
        raise ValueError("comment_response_too_large")
    return payload


def _reply_mid(reply: dict[str, Any]) -> str:
    direct = reply.get("mid")
    if direct not in (None, ""):
        return str(direct)
    member = reply.get("member")
    if isinstance(member, dict) and member.get("mid") not in (None, ""):
        return str(member["mid"])
    return ""


def _looks_like_reply(value: dict[str, Any]) -> bool:
    return bool(
        value.get("rpid")
        or value.get("rpid_str")
        or isinstance(value.get("content"), dict)
        or isinstance(value.get("member"), dict)
    )


def _upper_top(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    upper = data.get("upper")
    upper_mid = ""
    if isinstance(upper, dict):
        if upper.get("mid") not in (None, ""):
            upper_mid = str(upper["mid"])
        top = upper.get("top")
        if isinstance(top, dict) and _looks_like_reply(top):
            return top, upper_mid

    top_group = data.get("top")
    if isinstance(top_group, dict):
        # Current replies can expose the pinned comment directly as data.top.
        if _looks_like_reply(top_group):
            return top_group, upper_mid
        # Retain compatibility with historical wrappers that nested it under top.upper.
        top = top_group.get("upper")
        if isinstance(top, dict) and _looks_like_reply(top):
            return top, upper_mid
    return None, upper_mid


def fetch_uploader_pinned_comment(
    bvid: str,
    *,
    timeout: float = COMMENT_TIMEOUT_SECONDS,
    cookie_file: Path | None = None,
    open_url: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Perform at most one read-only request for the uploader's top-level pinned comment.

    Normal lookups are anonymous. A caller may explicitly provide the project's Netscape Cookie file
    for a whitelisted uploader. The function never retries and never exposes Cookie contents.
    """

    aid = bvid_to_aid(bvid)
    query = urllib.parse.urlencode(
        {
            "type": 1,
            "oid": aid,
            "pn": 1,
            "ps": 1,
            "sort": 0,
        }
    )
    request = urllib.request.Request(
        f"{COMMENT_ENDPOINT}?{query}",
        method="GET",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://www.bilibili.com/video/{bvid}/",
            "User-Agent": "Mozilla/5.0 bili-learning-automation/1.0",
        },
    )
    if open_url is not None:
        opener = open_url
    elif cookie_file is not None:
        try:
            cookie_jar = http.cookiejar.MozillaCookieJar(str(cookie_file))
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except (OSError, http.cookiejar.LoadError):
            return {
                "status": "unavailable",
                "source": "uploader_pinned_comment",
                "aid": aid,
                "reason": "cookie_load_failed",
            }
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar)).open
    else:
        opener = urllib.request.urlopen

    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(_read_limited(response).decode("utf-8", errors="replace"))
    except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return {
            "status": "unavailable",
            "source": "uploader_pinned_comment",
            "aid": aid,
            "reason": "request_failed",
        }

    if not isinstance(payload, dict):
        return {
            "status": "unavailable",
            "source": "uploader_pinned_comment",
            "aid": aid,
            "reason": "invalid_response",
        }
    code = payload.get("code")
    if code != 0:
        return {
            "status": "unavailable",
            "source": "uploader_pinned_comment",
            "aid": aid,
            "reason": f"api_code_{code}",
        }
    data = payload.get("data")
    if not isinstance(data, dict):
        return {
            "status": "unavailable",
            "source": "uploader_pinned_comment",
            "aid": aid,
            "reason": "missing_data",
        }

    top, upper_mid = _upper_top(data)
    if top is None:
        return {
            "status": "not_found",
            "source": "uploader_pinned_comment",
            "aid": aid,
        }

    reply_mid = _reply_mid(top)
    if upper_mid and reply_mid and upper_mid != reply_mid:
        return {
            "status": "unavailable",
            "source": "uploader_pinned_comment",
            "aid": aid,
            "reason": "pinned_author_mismatch",
        }
    reply_oid = top.get("oid_str") or top.get("oid") or ""
    if reply_oid not in (None, "") and str(reply_oid) != str(aid):
        return {
            "status": "unavailable",
            "source": "uploader_pinned_comment",
            "aid": aid,
            "reason": "pinned_oid_mismatch",
        }

    content = top.get("content")
    message = str(content.get("message") or "") if isinstance(content, dict) else ""
    rpid = top.get("rpid_str") or top.get("rpid") or ""
    return {
        "status": "present",
        "source": "uploader_pinned_comment",
        "aid": aid,
        "author_mid": upper_mid or reply_mid,
        "rpid": str(rpid),
        "text": message.strip(),
    }
