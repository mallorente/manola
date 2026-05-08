from __future__ import annotations

import subprocess
import sys
import tempfile
import wave
import math
from pathlib import Path

import httpx

from .audio import ffmpeg_path
from .config import AppConfig, resolve_secret
from .cuda import add_packaged_cuda_dll_directories
from .errors import ConfigurationError, DependencyMissingError, NanolaError
from .models import Language, TranscriptionBackend
from .status import StatusCallback, noop_status


def transcribe_audio(
    audio_path: Path,
    *,
    backend: TranscriptionBackend,
    language: Language,
    config: AppConfig,
    status: StatusCallback = noop_status,
) -> str:
    if backend == TranscriptionBackend.local:
        return _transcribe_local(audio_path, language, config, status)
    return _transcribe_remote(audio_path, language, config)


def _transcribe_local(
    audio_path: Path,
    language: Language,
    config: AppConfig,
    status: StatusCallback = noop_status,
) -> str:
    if config.local_whisper_device == "cuda" and not _running_in_worker():
        status("Starting CUDA transcription worker...")
        return _transcribe_local_in_worker(audio_path, language, config, status)

    if config.local_whisper_device == "cuda":
        status("Preparing CUDA libraries...")
        add_packaged_cuda_dll_directories()

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise DependencyMissingError(
            "Local transcription requires faster-whisper. Install with: uv sync --extra local-transcription"
        ) from exc

    status(
        f"Loading Whisper model {config.local_whisper_model} "
        f"on {config.local_whisper_device}/{config.local_whisper_compute_type}..."
    )
    model = WhisperModel(
        config.local_whisper_model,
        device=config.local_whisper_device,
        compute_type=config.local_whisper_compute_type,
    )
    language_arg = None if language == Language.auto else language.value
    try:
        return _transcribe_with_model(model, audio_path, language_arg, config, status)
    except RuntimeError as exc:
        if (
            not _is_cuda_runtime_error(exc)
            or config.local_whisper_device == "cpu"
            or not config.local_whisper_cpu_fallback
        ):
            raise NanolaError(_local_transcription_error(exc, config)) from exc

    cpu_model = WhisperModel(config.local_whisper_model, device="cpu", compute_type="int8")
    try:
        return _transcribe_with_model(cpu_model, audio_path, language_arg, config, status)
    except RuntimeError as exc:
        raise NanolaError(f"Local transcription failed on CPU fallback: {exc}") from exc


def _transcribe_with_model(
    model,
    audio_path: Path,
    language_arg: str | None,
    config: AppConfig,
    status: StatusCallback = noop_status,
) -> str:
    duration = _wav_duration(audio_path)
    chunk_seconds = config.local_whisper_chunk_seconds
    if chunk_seconds <= 0 or duration <= chunk_seconds:
        status("Transcribing audio...")
        segments, _info = model.transcribe(str(audio_path), language=language_arg)
        return _segments_to_text(segments)

    lines = []
    total_chunks = max(1, math.ceil(duration / chunk_seconds))
    with tempfile.TemporaryDirectory(prefix="nanola-whisper-") as temp_dir:
        for index, start in enumerate(range(0, int(duration), chunk_seconds), start=1):
            status(f"Transcribing chunk {index}/{total_chunks} ({start:0.0f}s-{min(start + chunk_seconds, duration):0.0f}s)...")
            chunk_path = Path(temp_dir) / f"chunk-{start:06d}.wav"
            _extract_audio_chunk(audio_path, chunk_path, start=start, duration=chunk_seconds)
            segments, _info = model.transcribe(str(chunk_path), language=language_arg)
            lines.extend(_segments_to_lines(segments, offset=float(start)))
    return "\n".join(lines).strip()


def _segments_to_text(segments, *, offset: float = 0.0) -> str:
    return "\n".join(_segments_to_lines(segments, offset=offset)).strip()


def _segments_to_lines(segments, *, offset: float = 0.0) -> list[str]:
    lines = []
    for segment in segments:
        lines.append(
            f"[{segment.start + offset:0.2f}-{segment.end + offset:0.2f}] {segment.text.strip()}"
        )
    return lines


def _wav_duration(audio_path: Path) -> float:
    try:
        with wave.open(str(audio_path), "rb") as handle:
            return handle.getnframes() / float(handle.getframerate())
    except (wave.Error, OSError):
        return 0.0


def _extract_audio_chunk(source: Path, target: Path, *, start: int, duration: int) -> None:
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        raise DependencyMissingError("FFmpeg is required to chunk long audio for transcription.")
    completed = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss",
            str(start),
            "-i",
            str(source),
            "-t",
            str(duration),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(target),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise NanolaError(f"FFmpeg failed to extract audio chunk: {details}")


def _transcribe_local_in_worker(
    audio_path: Path,
    language: Language,
    config: AppConfig,
    status: StatusCallback = noop_status,
) -> str:
    with tempfile.TemporaryDirectory(prefix="nanola-worker-") as temp_dir:
        config_path = Path(temp_dir) / "config.json"
        output_path = Path(temp_dir) / "transcript.txt"
        config_path.write_text(config.model_dump_json(), encoding="utf-8")
        env = dict(**__import__("os").environ)
        env["NANOLA_TRANSCRIBE_WORKER"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "nanola.transcribe_worker",
                str(audio_path),
                str(output_path),
                "--language",
                language.value,
                "--config",
                str(config_path),
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if completed.stderr.strip():
            for line in completed.stderr.strip().splitlines():
                status(line)
        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip()
            raise NanolaError(f"CUDA transcription worker failed: {details}")
        return output_path.read_text(encoding="utf-8").strip()


def _running_in_worker() -> bool:
    return __import__("os").environ.get("NANOLA_TRANSCRIBE_WORKER") == "1"


def _is_cuda_runtime_error(exc: RuntimeError) -> bool:
    message = str(exc).lower()
    cuda_markers = ("cuda", "cublas", "cudnn", "cufft", "cudart")
    return any(marker in message for marker in cuda_markers)


def _local_transcription_error(exc: RuntimeError, config: AppConfig) -> str:
    message = f"Local transcription failed: {exc}"
    if config.local_whisper_device != "cuda" or not _is_cuda_runtime_error(exc):
        return message
    return (
        f"{message}\n"
        "CUDA transcription requires NVIDIA CUDA 12 cuBLAS and cuDNN 9 DLLs available on PATH. "
        "Run `nanola doctor` to check CUDA dependencies, or set "
        'local_whisper_cpu_fallback = true if CPU fallback is acceptable.'
    )


def _transcribe_remote(audio_path: Path, language: Language, config: AppConfig) -> str:
    if not config.remote_transcription_url:
        raise ConfigurationError(
            "Remote transcription requires remote_transcription_url in ~/.nanola/config.toml."
        )

    api_key = resolve_secret(config.remote_transcription_api_key_env)
    data = {}
    if language != Language.auto:
        data["language"] = language.value

    with audio_path.open("rb") as audio_file:
        response = httpx.post(
            config.remote_transcription_url,
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files={"file": (audio_path.name, audio_file, "audio/wav")},
            timeout=600,
        )

    if response.status_code >= 400:
        raise NanolaError(f"Remote transcription failed: {response.status_code} {response.text}")

    payload = response.json()
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise NanolaError("Remote transcription response did not contain a non-empty 'text' field.")
    return text.strip()
