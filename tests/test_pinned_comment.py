from __future__ import annotations

import json
from pathlib import Path

from bili_learning.note_template import render_video_materials
from bili_learning.pinned_comment import (
    bvid_to_aid,
    fetch_uploader_pinned_comment,
    is_pinned_comment_whitelisted,
    should_lookup_pinned_comment,
)
from bili_learning.source import SOURCE_MODE_DESCRIPTION, SourceMaterial


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _size: int = -1) -> bytes:
        return self._payload


def test_bvid_to_aid_matches_current_ytdlp_sample() -> None:
    assert bvid_to_aid("BV1TXua68EYi") == 117072302512876


def test_comment_lookup_only_triggers_for_explicit_comment_resource_reference() -> None:
    source = SourceMaterial(SOURCE_MODE_DESCRIPTION)
    assert should_lookup_pinned_comment("工作流在评论区，使用需遵守规范", source)
    assert not should_lookup_pinned_comment("本期介绍一个新的工作流", source)


def test_t8star_aix_is_in_pinned_comment_whitelist() -> None:
    project_root = Path(__file__).resolve().parents[1]
    assert is_pinned_comment_whitelisted(project_root, {"uploader": "T8star-Aix"})
    assert is_pinned_comment_whitelisted(project_root, {"uploader_id": "385085361"})
    assert not is_pinned_comment_whitelisted(project_root, {"uploader": "another-uploader", "uploader_id": "1"})


def test_fetch_supports_current_direct_top_field() -> None:
    def open_url(_request, timeout):
        return _FakeResponse(
            {
                "code": 0,
                "data": {
                    "upper": {"mid": 123},
                    "top": {
                        "rpid": 789,
                        "mid": 123,
                        "content": {"message": "置顶资源：https://github.com/example/current-top"},
                    },
                },
            }
        )

    result = fetch_uploader_pinned_comment("BV1TXua68EYi", open_url=open_url)
    assert result["status"] == "present"
    assert result["rpid"] == "789"
    assert result["text"] == "置顶资源：https://github.com/example/current-top"


def test_fetch_reads_only_upper_pinned_comment_without_cookie_header() -> None:
    captured = {}

    def open_url(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _FakeResponse(
            {
                "code": 0,
                "data": {
                    "upper": {
                        "mid": 123,
                        "top": {
                            "rpid": 456,
                            "mid": 123,
                            "content": {"message": "工作流：https://github.com/example/demo"},
                        },
                    }
                },
            }
        )

    result = fetch_uploader_pinned_comment("BV1TXua68EYi", open_url=open_url)
    assert result["status"] == "present"
    assert result["text"] == "工作流：https://github.com/example/demo"
    headers = {key.lower(): value for key, value in captured["request"].header_items()}
    assert "cookie" not in headers


def test_fetch_failure_is_non_blocking_status() -> None:
    def open_url(_request, timeout=None):
        raise OSError("offline")

    result = fetch_uploader_pinned_comment("BV1TXua68EYi", open_url=open_url)
    assert result["status"] == "unavailable"
    assert result["reason"] == "request_failed"


def test_render_merges_description_and_pinned_comment_resources_and_uses_github_repo_name() -> None:
    job = {
        "bvid": "BV1TXua68EYi",
        "description_status": "present",
        "description": "https://github.com/example/demo\nhttps://github.com/example/second",
        "resource_access_notices": [],
        "uploader_pinned_comment": {
            "status": "present",
            "text": "提示词项目：https://github.com/example/demo\n节点：https://github.com/example/node-project\n镜像：https://example.com/file，备用说明",
        },
    }
    rendered = render_video_materials(job)
    assert rendered.count("https://github.com/example/demo") == 3  # resource link + raw pinned source + raw description
    assert "second（GitHub）" in rendered
    assert "提示词项目（GitHub）" in rendered
    assert "node-project（GitHub）" in rendered
    assert "](<https://example.com/file>)" in rendered
    assert "https://example.com/file，备用说明" in rendered
