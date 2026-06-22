"""Voice-activity detection for meeting capture pause/resume.

RMS thresholds cannot tell quiet speech from ambient noise: a soft speaker can
dip below the silence floor and trigger a false pause. This module wraps
``webrtcvad`` to answer "does this chunk contain speech?" so the recording loop
can treat quiet-but-present speech as activity.

webrtcvad only accepts 16-bit PCM at 8/16/32/48 kHz in 10/20/30 ms frames, so we
split each recording chunk into 30 ms frames and report speech when at least
``min_voiced_ratio`` of frames are voiced. It is an optional dependency: when it
is missing, :func:`build_speech_detector` returns ``None`` and callers fall back
to RMS-based activity.
"""

from __future__ import annotations

import numpy as np

from .status import StatusCallback, noop_status


# Sample rates and frame length webrtcvad accepts.
VAD_SAMPLE_RATES = (8000, 16000, 32000, 48000)
_FRAME_MS = 30


class SpeechDetector:
    """Detect speech in float mono audio chunks via webrtcvad."""

    def __init__(self, vad, *, min_voiced_ratio: float = 0.2) -> None:
        self._vad = vad
        self._min_voiced_ratio = min_voiced_ratio

    def has_speech(self, audio_mono: np.ndarray, sample_rate: int) -> bool:
        if sample_rate not in VAD_SAMPLE_RATES:
            return False
        pcm = _float_to_pcm16(audio_mono)
        frame_len = int(sample_rate * _FRAME_MS / 1000)
        if frame_len <= 0 or pcm.size < frame_len:
            return False
        total = 0
        voiced = 0
        for start in range(0, pcm.size - frame_len + 1, frame_len):
            frame = pcm[start : start + frame_len].tobytes()
            total += 1
            try:
                if self._vad.is_speech(frame, sample_rate):
                    voiced += 1
            except Exception:
                return False
        if total == 0:
            return False
        return (voiced / total) >= self._min_voiced_ratio


def build_speech_detector(
    aggressiveness: int = 2,
    *,
    min_voiced_ratio: float = 0.2,
    status: StatusCallback = noop_status,
) -> SpeechDetector | None:
    """Return a :class:`SpeechDetector`, or ``None`` when webrtcvad is unavailable.

    A missing ``webrtcvad`` is not fatal: the recording loop falls back to
    RMS-based pause/resume.
    """
    try:
        import webrtcvad
    except ImportError:
        status(
            "Voice-activity detection unavailable (webrtcvad not installed); "
            "using RMS-based pause/resume."
        )
        return None
    bounded = max(0, min(3, int(aggressiveness)))
    return SpeechDetector(webrtcvad.Vad(bounded), min_voiced_ratio=min_voiced_ratio)


def _float_to_pcm16(audio_mono: np.ndarray) -> np.ndarray:
    array = np.asarray(audio_mono, dtype=np.float32)
    if array.ndim != 1:
        array = array.reshape(-1)
    clipped = np.clip(array, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2")
