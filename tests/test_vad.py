import sys

import numpy as np

from manola.config import AppConfig
from manola.vad import SpeechDetector, build_speech_detector


class FakeVad:
    """Stand-in for webrtcvad.Vad that returns scripted per-frame verdicts."""

    def __init__(self, voiced_flags):
        self._flags = list(voiced_flags)
        self.calls = 0

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        flag = self._flags[self.calls] if self.calls < len(self._flags) else False
        self.calls += 1
        return flag


def _audio(frames: int, sample_rate: int = 48000) -> np.ndarray:
    # 30 ms frame at 48 kHz == 1440 samples.
    frame_len = int(sample_rate * 30 / 1000)
    return np.zeros(frames * frame_len, dtype=np.float32)


def test_has_speech_true_when_voiced_ratio_met() -> None:
    detector = SpeechDetector(FakeVad([True, False, False, False, False]), min_voiced_ratio=0.2)
    assert detector.has_speech(_audio(5), 48000) is True


def test_has_speech_false_when_below_ratio() -> None:
    detector = SpeechDetector(FakeVad([True, False, False, False, False]), min_voiced_ratio=0.3)
    assert detector.has_speech(_audio(5), 48000) is False


def test_has_speech_false_for_unsupported_sample_rate() -> None:
    detector = SpeechDetector(FakeVad([True] * 10), min_voiced_ratio=0.1)
    assert detector.has_speech(_audio(5, 44100), 44100) is False


def test_has_speech_false_when_audio_shorter_than_one_frame() -> None:
    detector = SpeechDetector(FakeVad([True] * 10), min_voiced_ratio=0.1)
    assert detector.has_speech(np.zeros(100, dtype=np.float32), 48000) is False


def test_has_speech_false_when_vad_raises() -> None:
    class Boom:
        def is_speech(self, frame, sample_rate):
            raise RuntimeError("bad frame")

    detector = SpeechDetector(Boom(), min_voiced_ratio=0.1)
    assert detector.has_speech(_audio(3), 48000) is False


def test_build_speech_detector_returns_detector_when_lib_present() -> None:
    # webrtcvad-wheels is a project dependency, so this resolves to a real detector.
    detector = build_speech_detector(2)
    assert detector is not None
    assert detector.has_speech(_audio(10), 48000) is False  # pure silence is not speech


def test_build_speech_detector_falls_back_when_lib_missing(monkeypatch) -> None:
    # A None entry in sys.modules makes `import webrtcvad` raise ImportError.
    monkeypatch.setitem(sys.modules, "webrtcvad", None)
    messages: list[str] = []
    detector = build_speech_detector(2, status=messages.append)
    assert detector is None
    assert any("webrtcvad" in message for message in messages)


def test_vad_config_defaults() -> None:
    config = AppConfig()
    assert config.vad_pause_resume is True
    assert config.vad_aggressiveness == 2
