from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
import mimetypes
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .audio_recording import inspect_audio_devices
from .config import CONFIG_PATH, SECRETS_PATH, AppConfig, load_config
from .doctor import collect_doctor_checks
from .models import MeetingMetadata
from .pipeline import iter_meetings


STATIC_DIR = Path(__file__).with_name("ui_static")
TRANSCRIPT_TIMESTAMP_RE = re.compile(r"^\[(?P<start>\d+(?:\.\d+)?)-(?P<end>\d+(?:\.\d+)?)\]")


def run_ui_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    config = load_config()

    class Handler(ManolaUiHandler):
        app_config = config

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Manola UI: http://{host}:{port}")
    server.serve_forever()


class ManolaUiHandler(BaseHTTPRequestHandler):
    app_config: AppConfig

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/" or parsed.path == "/index.html":
                self._send_file(STATIC_DIR / "index.html")
            elif parsed.path.startswith("/static/"):
                relative = parsed.path.removeprefix("/static/")
                self._send_file(STATIC_DIR / relative)
            elif parsed.path == "/api/state":
                self._send_json(build_state(self.app_config))
            elif parsed.path == "/api/meeting":
                query = parse_qs(parsed.query)
                path = query.get("path", [None])[0]
                if path is None:
                    self._send_error(400, "Missing path")
                    return
                self._send_json(read_meeting(Path(unquote(path)), self.app_config))
            else:
                self._send_error(404, "Not found")
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            self._send_error(500, str(exc))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_file(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            static_root = STATIC_DIR.resolve()
            if resolved != static_root and static_root not in resolved.parents:
                self._send_error(403, "Forbidden")
                return
            if not resolved.exists() or not resolved.is_file():
                self._send_error(404, "Not found")
                return
            content = resolved.read_bytes()
        except OSError as exc:
            self._send_error(500, str(exc))
            return
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, value: Any) -> None:
        content = json.dumps(value, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_error(self, status: int, message: str) -> None:
        content = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def build_state(config: AppConfig) -> dict[str, Any]:
    meetings = [read_meeting(metadata_path.parent, config) for metadata_path in iter_meetings(config.workspace_dir)]
    return {
        "config": public_config(config),
        "meetings": meetings,
        "doctor": safe_doctor_checks(config),
        "devices": safe_devices(),
        "backend_gaps": backend_gaps(),
    }


def public_config(config: AppConfig) -> dict[str, Any]:
    return {
        "workspace_dir": str(config.workspace_dir),
        "shared_dir": str(config.shared_dir) if config.shared_dir else None,
        "models_dir": str(config.models_dir),
        "prompts_dir": str(config.prompts_dir),
        "default_llm_profile": config.default_llm_profile,
        "default_generate_llm_report": config.default_generate_llm_report,
        "default_transcription_backend": config.default_transcription_backend,
        "default_language": config.default_language,
        "default_mic_index": config.default_mic_index,
        "default_speaker_index": config.default_speaker_index,
        "local_whisper_model": config.local_whisper_model,
        "local_whisper_device": config.local_whisper_device,
        "local_whisper_compute_type": config.local_whisper_compute_type,
        "local_whisper_chunk_seconds": config.local_whisper_chunk_seconds,
        "live_transcript_model": config.live_transcript_model,
        "live_transcript_device": config.live_transcript_device,
        "live_transcript_compute_type": config.live_transcript_compute_type,
        "llm_profiles": {
            name: {
                "base_url": profile.base_url,
                "model": profile.model,
                "api_key_env": profile.api_key_env,
                "thinking": profile.thinking,
                "temperature": profile.temperature,
                "enrichment_temperature": profile.enrichment_temperature,
            }
            for name, profile in config.llm_profiles.items()
        },
        "config_path": str(CONFIG_PATH),
        "secrets_path": str(SECRETS_PATH),
    }


def safe_doctor_checks(config: AppConfig) -> list[dict[str, str]]:
    try:
        return [asdict(check) for check in collect_doctor_checks(config)]
    except Exception as exc:  # pragma: no cover - protects the HTTP state boundary
        return [{"name": "doctor", "status": "warn", "detail": str(exc)}]


def safe_devices() -> dict[str, Any]:
    try:
        report = inspect_audio_devices()
        return {
            "default_microphone": report.default_microphone,
            "default_speaker": report.default_speaker,
            "microphones": report.microphones,
            "speakers": report.speakers,
            "loopbacks": report.loopbacks,
            "has_meeting_capture": report.has_meeting_capture,
        }
    except Exception as exc:
        return {"error": str(exc)}


def read_meeting(meeting_dir: Path, config: AppConfig) -> dict[str, Any]:
    metadata_path = meeting_dir / "metadata.json"
    metadata = MeetingMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8-sig"))
    transcript_path = meeting_dir / metadata.transcript
    report_path = meeting_dir / metadata.report
    suggestions_path = meeting_dir / "metadata.suggestions.json"
    transcript = _read_text(transcript_path)
    report = _read_text(report_path)
    original = audio_info(meeting_dir / metadata.audio_original)
    normalized = audio_info(meeting_dir / metadata.audio_normalized)
    transcript_end = transcript_end_seconds(transcript)
    health = meeting_health(original, normalized, transcript_end)
    report_stale = (
        report_path.exists()
        and transcript_path.exists()
        and transcript_path.stat().st_mtime > report_path.stat().st_mtime
    )
    duration = (normalized or {}).get("duration_seconds") or (original or {}).get("duration_seconds")
    return {
        **metadata.model_dump(mode="json"),
        "path": str(meeting_dir),
        "created_at": metadata.created_at.isoformat(),
        "duration_seconds": duration,
        "duration_label": format_duration(duration),
        "transcript_text": transcript,
        "transcript_excerpt": excerpt(transcript),
        "transcript_end_seconds": transcript_end,
        "transcript_end_label": format_duration(transcript_end) if transcript_end else None,
        "report_text": report,
        "report_excerpt": excerpt(report),
        "report_stale": report_stale,
        "metadata_suggestions": _read_json(suggestions_path),
        "audio": {
            "original": original,
            "normalized": normalized,
        },
        "health": health,
        "workspace_dir": str(config.workspace_dir),
    }


def audio_info(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    info: dict[str, Any] = {
        "name": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size,
    }
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as handle:
                frames = handle.getnframes()
                rate = handle.getframerate()
                duration = frames / float(rate)
                info.update(
                    {
                        "duration_seconds": duration,
                        "duration_label": format_duration(duration),
                        "sample_rate": rate,
                        "channels": handle.getnchannels(),
                        "sample_width": handle.getsampwidth(),
                    }
                )
        except wave.Error:
            info["duration_error"] = "Could not read WAV header"
    return info


def transcript_end_seconds(text: str) -> float | None:
    end: float | None = None
    for line in text.splitlines():
        match = TRANSCRIPT_TIMESTAMP_RE.match(line)
        if match:
            end = float(match.group("end"))
    return end


def meeting_health(original: dict[str, Any] | None, normalized: dict[str, Any] | None, transcript_end: float | None) -> dict[str, Any]:
    original_duration = _duration(original)
    normalized_duration = _duration(normalized)
    normalized_mismatch = bool(
        original_duration
        and normalized_duration
        and original_duration - normalized_duration > max(10.0, original_duration * 0.03)
    )
    transcript_mismatch = bool(
        normalized_duration
        and transcript_end
        and normalized_duration - transcript_end > max(20.0, normalized_duration * 0.05)
    )
    if normalized_mismatch:
        return {
            "level": "warn",
            "label": "Normalized audio is shorter than recorded audio",
            "detail": f"Recorded: {format_duration(original_duration)} · Normalized: {format_duration(normalized_duration)}",
            "normalized_mismatch": True,
            "transcript_mismatch": transcript_mismatch,
        }
    if transcript_mismatch:
        return {
            "level": "warn",
            "label": "Transcript appears shorter than source audio",
            "detail": f"Audio: {format_duration(normalized_duration)} · Transcript ends: {format_duration(transcript_end)}",
            "normalized_mismatch": False,
            "transcript_mismatch": True,
        }
    return {
        "level": "ok",
        "label": "Ready",
        "detail": "Meeting artifacts look consistent.",
        "normalized_mismatch": False,
        "transcript_mismatch": False,
    }


def _duration(info: dict[str, Any] | None) -> float | None:
    if not info:
        return None
    value = info.get("duration_seconds")
    return float(value) if isinstance(value, int | float) else None


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON: {exc}"}


def excerpt(text: str, length: int = 260) -> str:
    clean = " ".join(text.split())
    if len(clean) <= length:
        return clean
    return clean[: length - 1].rstrip() + "…"


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    total = max(0, int(round(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s"


def backend_gaps() -> list[dict[str, str]]:
    return [
        {
            "area": "recording",
            "gap": "The CLI recording flow is blocking and stop-key driven. The UI needs a job API for start/stop/progress/live levels before Record meeting can be wired.",
        },
        {
            "area": "import",
            "gap": "The CLI imports local paths. Browser upload or desktop file-picker handoff needs a backend endpoint before Import audio and Google Recorder import can process files.",
        },
        {
            "area": "long-running jobs",
            "gap": "Transcribe, summarize, enrich, export, and repair actions need async job tracking before the UI can safely run them.",
        },
        {
            "area": "settings persistence",
            "gap": "App language and highlight color are UI preferences stored in browser localStorage; they are not yet part of ~/.manola/config.toml.",
        },
    ]
