from pathlib import Path
import warnings

import numpy as np
import pytest

from manola.audio_recording import (
    record_wav,
    rms_float,
    write_wav,
    _active_loopback,
    _device_by_index,
    _match_device,
    _mix_audio,
    _record_frames,
)
from manola.errors import ManolaError


def test_write_wav_creates_mono_file(tmp_path: Path) -> None:
    audio = np.array([[0.5, -0.5], [0.25, -0.25], [0.0, 0.0]], dtype=np.float32)
    path = tmp_path / "sample.wav"

    write_wav(path, audio, 16000)

    assert path.exists()
    assert path.stat().st_size > 44


def test_rms_float_reports_signal_strength() -> None:
    audio = np.array([0.0, 1.0, -1.0], dtype=np.float32)

    assert rms_float(audio) > 0.8


def test_mix_audio_averages_tracks() -> None:
    mixed = _mix_audio(
        [
            np.array([1.0, 1.0, 1.0], dtype=np.float32),
            np.array([-1.0, -1.0, -1.0], dtype=np.float32),
        ]
    )

    assert np.allclose(mixed, np.array([0.0, 0.0, 0.0], dtype=np.float32))


def test_record_wav_writes_target(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "manola.audio_recording._record_source_with_components",
        lambda source, duration_seconds, sample_rate, **kwargs: (
            np.ones(sample_rate, dtype=np.float32) * 0.1,
            {"mic": 0.1},
        ),
    )

    result = record_wav(source="mic", duration_seconds=1, target=tmp_path / "recorded.wav", sample_rate=16000)

    assert result.path.exists()
    assert result.rms > 0
    assert not result.silent


def test_record_wav_rejects_partial_meeting_capture(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "manola.audio_recording._record_source_with_components",
        lambda source, duration_seconds, sample_rate, **kwargs: (
            np.ones(sample_rate, dtype=np.float32) * 0.1,
            {"mic": 0.1, "system": 0.0},
        ),
    )

    target = tmp_path / "recorded.wav"
    with pytest.raises(ManolaError, match="Meeting capture appears partial"):
        record_wav(source="meeting", duration_seconds=1, target=target, sample_rate=16000)

    assert target.exists()


def test_record_wav_allows_partial_meeting_capture_when_requested(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "manola.audio_recording._record_source_with_components",
        lambda source, duration_seconds, sample_rate, **kwargs: (
            np.ones(sample_rate, dtype=np.float32) * 0.1,
            {"mic": 0.1, "system": 0.0},
        ),
    )

    result = record_wav(
        source="meeting",
        duration_seconds=1,
        target=tmp_path / "recorded.wav",
        sample_rate=16000,
        allow_partial=True,
    )

    assert result.component_rms == {"mic": 0.1, "system": 0.0}


def test_active_loopback_selects_loudest_signal(monkeypatch) -> None:
    class Device:
        def __init__(self, name: str) -> None:
            self.name = name
            self.isloopback = True

    quiet = Device("Quiet loopback")
    loud = Device("Loud loopback")

    class Soundcard:
        def all_microphones(self, *, include_loopback: bool):
            assert include_loopback is True
            return [quiet, loud]

    def fake_record_device(device, frames: int, sample_rate: int):
        value = 0.01 if device is quiet else 0.2
        return np.ones(frames, dtype=np.float32) * value

    monkeypatch.setattr("manola.audio_recording._record_device", fake_record_device)

    selected = _active_loopback(Soundcard(), sample_rate=16000, probe_seconds=0.1)

    assert selected is not None
    device, rms = selected
    assert device is loud
    assert rms == pytest.approx(0.2)


def test_record_frames_suppresses_soundcard_discontinuity_warning() -> None:
    class Recorder:
        def record(self, *, numframes: int):
            warnings.warn_explicit(
                "data discontinuity in recording",
                RuntimeWarning,
                filename="soundcard/mediafoundation.py",
                lineno=772,
                module="soundcard.mediafoundation",
            )
            return np.zeros(numframes, dtype=np.float32)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        audio = _record_frames(Recorder(), 3)

    assert np.allclose(audio, np.zeros(3, dtype=np.float32))
    assert caught == []


def test_match_device_accepts_case_insensitive_substring() -> None:
    class Device:
        def __init__(self, name: str) -> None:
            self.name = name

    selected = _match_device([Device("Microphone Array (Realtek)")], "realtek", "microphone")

    assert selected.name == "Microphone Array (Realtek)"


def test_device_by_index_is_one_based() -> None:
    class Device:
        def __init__(self, name: str) -> None:
            self.name = name

    selected = _device_by_index([Device("Mic A"), Device("Mic B")], 2, "microphone")

    assert selected.name == "Mic B"


def test_device_by_index_rejects_zero() -> None:
    with pytest.raises(ManolaError, match="1 or greater"):
        _device_by_index([], 0, "microphone")
