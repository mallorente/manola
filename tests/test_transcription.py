from pathlib import Path
from types import SimpleNamespace

import pytest

from nanola.config import AppConfig
from nanola.errors import NanolaError
from nanola.models import Language, TranscriptionBackend
from nanola.transcription import transcribe_audio
from nanola.transcription import _transcribe_local_in_worker


def test_local_transcription_uses_configured_cpu_defaults(monkeypatch, tmp_path: Path) -> None:
    calls = []

    class FakeWhisperModel:
        def __init__(self, model_name: str, *, device: str, compute_type: str) -> None:
            calls.append((model_name, device, compute_type))

        def transcribe(self, audio_path: str, *, language: str | None):
            return [SimpleNamespace(start=0.0, end=1.0, text=" Hello")], None

    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    result = transcribe_audio(
        tmp_path / "audio.wav",
        backend=TranscriptionBackend.local,
        language=Language.en,
        config=AppConfig(local_whisper_model="base", local_whisper_device="cpu", local_whisper_compute_type="int8"),
    )

    assert calls == [("base", "cpu", "int8")]
    assert result == "[0.00-1.00] Hello"


def test_local_transcription_falls_back_to_cpu_after_cuda_error(monkeypatch, tmp_path: Path) -> None:
    calls = []
    monkeypatch.setenv("NANOLA_TRANSCRIBE_WORKER", "1")

    class FakeWhisperModel:
        def __init__(self, model_name: str, *, device: str, compute_type: str) -> None:
            self.device = device
            calls.append((model_name, device, compute_type))

        def transcribe(self, audio_path: str, *, language: str | None):
            if self.device == "cuda":
                raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
            return [SimpleNamespace(start=1.0, end=2.0, text=" fallback")], None

    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    result = transcribe_audio(
        tmp_path / "audio.wav",
        backend=TranscriptionBackend.local,
        language=Language.en,
        config=AppConfig(
            local_whisper_device="cuda",
            local_whisper_compute_type="float16",
            local_whisper_cpu_fallback=True,
        ),
    )

    assert calls == [("base", "cuda", "float16"), ("base", "cpu", "int8")]
    assert result == "[1.00-2.00] fallback"


def test_local_transcription_cuda_error_does_not_fallback_unless_enabled(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("NANOLA_TRANSCRIBE_WORKER", "1")
    class FakeWhisperModel:
        def __init__(self, model_name: str, *, device: str, compute_type: str) -> None:
            pass

        def transcribe(self, audio_path: str, *, language: str | None):
            raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")

    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    with pytest.raises(NanolaError, match="CUDA transcription requires"):
        transcribe_audio(
            tmp_path / "audio.wav",
            backend=TranscriptionBackend.local,
            language=Language.en,
            config=AppConfig(local_whisper_device="cuda", local_whisper_compute_type="float16"),
        )


def test_local_transcription_wraps_cpu_runtime_errors(monkeypatch, tmp_path: Path) -> None:
    class FakeWhisperModel:
        def __init__(self, model_name: str, *, device: str, compute_type: str) -> None:
            pass

        def transcribe(self, audio_path: str, *, language: str | None):
            raise RuntimeError("bad audio")

    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )

    with pytest.raises(NanolaError, match="Local transcription failed"):
        transcribe_audio(
            tmp_path / "audio.wav",
            backend=TranscriptionBackend.local,
            language=Language.en,
            config=AppConfig(),
        )


def test_local_transcription_chunks_long_wav(monkeypatch, tmp_path: Path) -> None:
    calls = []

    class FakeWhisperModel:
        def __init__(self, model_name: str, *, device: str, compute_type: str) -> None:
            pass

        def transcribe(self, audio_path: str, *, language: str | None):
            calls.append(Path(audio_path).name)
            return [SimpleNamespace(start=0.0, end=1.0, text=f" {Path(audio_path).stem}")], None

    def fake_extract(source: Path, target: Path, *, start: int, duration: int) -> None:
        target.write_text("chunk", encoding="utf-8")

    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )
    monkeypatch.setattr("nanola.transcription._wav_duration", lambda audio_path: 601.0)
    monkeypatch.setattr("nanola.transcription._extract_audio_chunk", fake_extract)

    result = transcribe_audio(
        tmp_path / "long.wav",
        backend=TranscriptionBackend.local,
        language=Language.en,
        config=AppConfig(local_whisper_chunk_seconds=300),
    )

    assert calls == ["chunk-000000.wav", "chunk-000300.wav", "chunk-000600.wav"]
    assert "[0.00-1.00] chunk-000000" in result
    assert "[300.00-301.00] chunk-000300" in result
    assert "[600.00-601.00] chunk-000600" in result


def test_cuda_worker_wrapper_forwards_worker_status(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "transcript.txt"
    output.write_text("transcript\n", encoding="utf-8")

    class Completed:
        returncode = 0
        stderr = "Transcribing chunk 1/1\n"
        stdout = ""

    def fake_run(*args, **kwargs):
        config_arg_index = args[0].index("--config") + 1
        temp_dir = Path(args[0][config_arg_index]).parent
        (temp_dir / "transcript.txt").write_text("transcript\n", encoding="utf-8")
        return Completed()

    statuses = []
    monkeypatch.setattr("nanola.transcription.subprocess.run", fake_run)

    result = _transcribe_local_in_worker(
        tmp_path / "audio.wav",
        Language.en,
        AppConfig(local_whisper_device="cuda"),
        statuses.append,
    )

    assert result == "transcript"
    assert statuses == ["Transcribing chunk 1/1"]
