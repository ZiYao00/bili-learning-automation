from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

import bili_learning.lifecycle as lifecycle
import bili_learning.local_asr as local_asr
from bili_learning.runtime import ReservationBusyError, claim_reservation

BVID = "BV1mxYF6cEQE"


def _prepare_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, notes: list | None = None):
    settings = SimpleNamespace(
        local_asr_base_url="http://127.0.0.1:8191",
        runtime_root=tmp_path / "runtime",
        notes_root=tmp_path / "notes",
    )
    monkeypatch.setattr(lifecycle, "load_settings", lambda _root: settings)
    monkeypatch.setattr(
        lifecycle, "onboarding_report", lambda _settings: {"status": "ready", "actions": [], "warnings": []}
    )
    monkeypatch.setattr(lifecycle, "find_notes_by_bvid", lambda _settings, _bvid: notes or [])
    return settings


def test_existing_note_skips_asr_before_download(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    note = tmp_path / "notes" / "existing.md"
    note.parent.mkdir()
    note.write_text("existing", encoding="utf-8")
    _prepare_env(monkeypatch, tmp_path, [
        SimpleNamespace(path=note, as_dict=lambda: {"path": str(note)})
    ])

    def must_not_transcribe(*_args):
        raise AssertionError("duplicate note must be detected before downloading or ASR")

    monkeypatch.setattr(lifecycle, "transcribe_bilibili", must_not_transcribe)
    payload, code = lifecycle.prepare_local_asr_note(tmp_path, BVID)

    assert code == 2
    assert payload["status"] == "existing_note_found"
    assert not (tmp_path / "runtime" / "locks").exists()


def test_update_missing_note_skips_asr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _prepare_env(monkeypatch, tmp_path)
    monkeypatch.setattr(
        lifecycle, "transcribe_bilibili",
        lambda *_args: pytest.fail("update without target must not transcribe"),
    )
    payload, code = lifecycle.prepare_local_asr_note(tmp_path, BVID, on_existing="update")
    assert code == 2
    assert payload["status"] == "existing_note_not_found"


def test_busy_bvid_never_triggers_second_asr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = _prepare_env(monkeypatch, tmp_path)
    claim_reservation(settings.runtime_root, BVID, purpose="asr")
    monkeypatch.setattr(
        lifecycle, "transcribe_bilibili",
        lambda *_args: pytest.fail("busy BVID must not transcribe"),
    )
    payload, code = lifecycle.prepare_local_asr_note(tmp_path, BVID, on_existing="rerun")
    assert code == 2
    assert payload["status"] == "in_progress"


def test_failed_asr_releases_preclaimed_reservation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = _prepare_env(monkeypatch, tmp_path)

    def fail_transcription(*_args):
        raise local_asr.LocalAsrError(
            "local_asr_outcome_unknown", "transcription may still be running"
        )

    monkeypatch.setattr(lifecycle, "transcribe_bilibili", fail_transcription)
    payload, code = lifecycle.prepare_local_asr_note(tmp_path, BVID)

    assert code == 2
    assert payload["status"] == "asr_outcome_unknown"
    reservation = settings.runtime_root / "locks" / f"{BVID}.reservation.json"
    assert json.loads(reservation.read_text(encoding="utf-8"))["state"] == "released"


def test_asr_active_owner_not_reclaimed_by_two_hour_stale_window(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    reservation = claim_reservation(runtime, BVID, purpose="asr")
    payload = json.loads(reservation.path.read_text(encoding="utf-8"))
    payload["updated_at"] = time.time() - 7300
    reservation.path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ReservationBusyError):
        claim_reservation(runtime, BVID)


def test_multipart_upload_is_streamed_with_known_length(tmp_path: Path) -> None:
    media = tmp_path / "long.m4a"
    media.write_bytes(b"x" * (2 * 1024 * 1024 + 17))
    parts, _boundary, total = local_asr._multipart_body(media)
    blocks = list(parts)
    body = b"".join(blocks)

    assert len(blocks) >= 5
    assert max(map(len, blocks)) <= 1024 * 1024
    assert total == len(body)
    assert body.count(b"x" * 100) > 1


def test_streamed_multipart_reaches_real_local_http_server(tmp_path: Path) -> None:
    audio = tmp_path / "voice.m4a"
    audio.write_bytes(b"synthetic-audio")
    captured: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            size = int(self.headers["Content-Length"])
            body = self.rfile.read(size)
            captured.update(path=self.path, size=size, body=body)
            response = json.dumps({"status": "ok", "text": "转录测试", "model": "SenseVoiceSmall"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = local_asr.transcribe_local_file(
            f"http://127.0.0.1:{server.server_port}", audio, timeout=5
        )
        assert result["text"] == "转录测试"
        assert captured["path"] == "/v1/audio/transcriptions"
        assert captured["size"] == len(captured["body"])
        assert b"synthetic-audio" in captured["body"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
