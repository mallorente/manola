from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
import wave
from http.server import ThreadingHTTPServer

from manola.config import AppConfig
from manola.jobs import JobRegistry
from manola.ui_server import (
    ManolaUiHandler,
    audio_info,
    build_state,
    meeting_health,
    read_meeting,
    safe_devices,
    transcript_end_seconds,
)


def _write_wav(path, *, seconds: int, rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * rate * seconds)


def test_audio_info_reads_wav_duration(tmp_path):
    wav = tmp_path / "sample.wav"
    _write_wav(wav, seconds=3)

    info = audio_info(wav)

    assert info is not None
    assert info["duration_seconds"] == 3
    assert info["duration_label"] == "0m 03s"
    assert info["sample_rate"] == 16000


def test_meeting_health_detects_truncated_normalized_audio():
    original = {"duration_seconds": 5266}
    normalized = {"duration_seconds": 2159.957}

    health = meeting_health(original, normalized, transcript_end=2159.92)

    assert health["level"] == "warn"
    assert health["normalized_mismatch"] is True
    assert "Normalized audio is shorter" in health["label"]


def test_meeting_health_detects_truncated_transcript():
    original = {"duration_seconds": 5266}
    normalized = {"duration_seconds": 5266}

    health = meeting_health(original, normalized, transcript_end=2159.92)

    assert health["level"] == "warn"
    assert health["transcript_mismatch"] is True
    assert "Transcript appears shorter" in health["label"]


def test_transcript_end_seconds_uses_last_timestamp():
    transcript = "\n".join(
        [
            "# Transcript",
            "[0.00-1.25] hello",
            "[12.50-18.75] goodbye",
        ]
    )

    assert transcript_end_seconds(transcript) == 18.75


def test_safe_devices_returns_error_when_device_probe_fails(monkeypatch):
    def fail_probe():
        raise RuntimeError("device probe failed")

    monkeypatch.setattr("manola.ui_server.inspect_audio_devices", fail_probe)

    assert safe_devices() == {"error": "device probe failed"}


def test_build_state_returns_doctor_warning_when_doctor_probe_fails(tmp_path, monkeypatch):
    def fail_doctor(config):
        raise RuntimeError("doctor failed")

    monkeypatch.setattr("manola.ui_server.collect_doctor_checks", fail_doctor)
    monkeypatch.setattr("manola.ui_server.safe_devices", lambda: {"error": "skipped"})

    state = build_state(AppConfig(workspace_dir=tmp_path))

    assert state["doctor"] == [{"name": "doctor", "status": "warn", "detail": "doctor failed"}]
    assert state["devices"] == {"error": "skipped"}


def test_read_meeting_includes_metadata_suggestions(tmp_path):
    meeting_dir = tmp_path / "2026-06-18__general__metadata-test"
    meeting_dir.mkdir()
    metadata = {
        "id": meeting_dir.name,
        "title": "Metadata test",
        "created_at": "2026-06-18T10:00:00",
        "meeting_type": "general",
        "project": None,
        "language": "en",
        "attendees": ["Ada"],
        "share_policy": "private",
        "transcription_backend": "local",
        "transcription_model": "large-v3",
        "transcription_device": "cuda",
        "transcription_compute_type": "float16",
        "llm_profile": "deepseek_fast",
        "audio_original": "audio/recorded.wav",
        "audio_normalized": "audio/normalized.wav",
        "transcript": "transcript.md",
        "report": "report.md",
    }
    suggestions = {
        "suggested_title": "Suggested title",
        "suggested_attendees": ["Ada", "Grace"],
        "notable_terms": ["local-first"],
    }
    (meeting_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (meeting_dir / "metadata.suggestions.json").write_text(json.dumps(suggestions), encoding="utf-8")

    meeting = read_meeting(meeting_dir, AppConfig(workspace_dir=tmp_path))

    assert meeting["metadata_suggestions"] == suggestions
    assert meeting["duration_label"] == "unknown"


def _post(base, action, payload):
    request = urllib.request.Request(
        f"{base}/api/jobs/{action}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _serving_handler(registry):
    class Handler(ManolaUiHandler):
        app_config = AppConfig(workspace_dir="/tmp")
        job_registry = registry

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    return server, base


def test_job_endpoints_start_poll_and_complete():
    registry = JobRegistry({"echo": lambda params, report: {"echo": params.get("v")}})
    server, base = _serving_handler(registry)
    try:
        status, job = _post(base, "echo", {"v": 7})
        assert status == 202
        assert job["status"] in {"queued", "running", "done"}

        record = None
        for _ in range(50):
            with urllib.request.urlopen(f"{base}/api/jobs/{job['id']}") as response:
                record = json.loads(response.read().decode("utf-8"))
            if record["status"] in {"done", "failed"}:
                break
            time.sleep(0.05)
        assert record["status"] == "done"
        assert record["result"] == {"echo": 7}
    finally:
        server.shutdown()
        registry.close()


def test_remote_llm_job_endpoint_refuses_without_confirmation():
    registry = JobRegistry(
        {"summarize": lambda params, report: "ok"},
        remote_llm_actions=frozenset({"summarize"}),
    )
    server, base = _serving_handler(registry)
    try:
        try:
            _post(base, "summarize", {})
            raise AssertionError("expected HTTP 412")
        except urllib.error.HTTPError as exc:
            assert exc.code == 412

        status, _job = _post(base, "summarize", {"confirm_remote_llm": True})
        assert status == 202
    finally:
        server.shutdown()
        registry.close()


def test_unknown_job_action_returns_404():
    registry = JobRegistry({})
    server, base = _serving_handler(registry)
    try:
        try:
            _post(base, "bogus", {})
            raise AssertionError("expected HTTP 404")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
    finally:
        server.shutdown()
        registry.close()
