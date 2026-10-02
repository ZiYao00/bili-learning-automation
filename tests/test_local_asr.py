from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import bili_learning.lifecycle as lifecycle
import bili_learning.local_asr as local_asr
from bili_learning.input_resolver import ResolvedInput


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_local_asr_health_accepts_expected_service(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "status": "ok",
        "service": "local-ASR-service",
        "device": "cpu",
        "model": "SenseVoiceSmall",
        "ffmpeg": True,
        "vad": True,
        "punctuation": True,
    }
    monkeypatch.setattr(local_asr.request, "urlopen", lambda request, timeout: _Response(payload))

    result = local_asr.check_local_asr_health("http://127.0.0.1:8001")

    assert result["status"] == "ok"
    assert result["service"] == "local-ASR-service"


def test_local_asr_health_rejects_wrong_service(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "status": "ok",
        "service": "other-service",
        "ffmpeg": True,
        "vad": True,
        "punctuation": True,
    }
    monkeypatch.setattr(local_asr.request, "urlopen", lambda request, timeout: _Response(payload))

    with pytest.raises(local_asr.LocalAsrError) as exc:
        local_asr.check_local_asr_health("http://127.0.0.1:8001")

    assert exc.value.code == "local_asr_not_ready"


def test_transcribe_local_file_posts_verbose_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake-audio")
    captured: dict[str, object] = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["data"] = req.data
        captured["content_type"] = req.headers.get("Content-type")
        return _Response(
            {
                "status": "ok",
                "text": " 测试转录 ",
                "model": "SenseVoiceSmall",
                "segments": [],
            }
        )

    monkeypatch.setattr(local_asr.request, "urlopen", fake_urlopen)

    result = local_asr.transcribe_local_file("http://127.0.0.1:8001", audio)

    assert result["text"] == "测试转录"
    assert captured["url"] == "http://127.0.0.1:8001/v1/audio/transcriptions"
    body = captured["data"]
    assert isinstance(body, bytes)
    assert b'name="model"' in body and b"custom" in body
    assert b'name="language"' in body and b"zh" in body
    assert b'name="response_format"' in body and b"verbose_json" in body
    assert b"fake-audio" in body
    assert str(captured["content_type"]).startswith("multipart/form-data; boundary=")


def test_prepare_local_asr_note_routes_plain_text_into_standard_job(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = SimpleNamespace(local_asr_base_url="http://127.0.0.1:8001")
    captured: dict[str, str] = {}

    monkeypatch.setattr(lifecycle, "load_settings", lambda project_root: settings)
    monkeypatch.setattr(
        lifecycle,
        "onboarding_report",
        lambda current_settings: {"status": "ready", "actions": [], "warnings": []},
    )
    monkeypatch.setattr(
        lifecycle,
        "transcribe_bilibili",
        lambda current_settings, message: (
            ResolvedInput("BV1mxYF6cEQE", "https://www.bilibili.com/video/BV1mxYF6cEQE/"),
            {"status": "ok", "text": "真实 ASR 纯文本。", "model": "SenseVoiceSmall"},
        ),
    )

    def fake_prepare_transcript_note(project_root, message, transcript_path, **kwargs):
        captured["text"] = transcript_path.read_text(encoding="utf-8")
        return {"status": "materials_ready", "source_mode": "asr_text"}, 0

    monkeypatch.setattr(lifecycle, "prepare_transcript_note", fake_prepare_transcript_note)

    payload, code = lifecycle.prepare_local_asr_note(tmp_path, "BV1mxYF6cEQE")

    assert code == 0
    assert captured["text"] == "真实 ASR 纯文本。\n"
    assert payload["source_mode"] == "asr_text"
    assert payload["asr_provider"] == "local-ASR-service"
    assert payload["asr_model"] == "SenseVoiceSmall"
