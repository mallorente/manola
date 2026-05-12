from __future__ import annotations

import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import numpy as np

from .audio_recording import write_wav
from .config import AppConfig
from .errors import DependencyMissingError
from .models import Language
from .status import StatusCallback, noop_status
from .transcription import _segments_to_text


class LiveTranscriptSession:
    def __init__(
        self,
        *,
        target: Path,
        language: Language,
        config: AppConfig,
        status: StatusCallback = noop_status,
        preview: Callable[[str], None] | None = None,
    ) -> None:
        self.target = target
        self.language = language
        self.config = config
        self.status = status
        self.preview = preview
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._buffer: list[np.ndarray] = []
        self._buffer_frames = 0
        self._retained_overlap_frames = 0
        self._sample_rate: int | None = None
        self._offset_seconds = 0.0
        self._future: Future[str] | None = None
        self._model = None
        self._closed = False
        self._recent_lines: list[str] = []

    def __enter__(self) -> LiveTranscriptSession:
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(
            "\n".join(
                [
                    "# Live transcript preview",
                    "",
                    "Preview quality. The final transcript.md generated after recording is canonical.",
                    "",
                    "## Confirmed Preview Chunks",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self.status(f"Live transcript preview: {self.target}")
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            self.flush(wait=True)
        finally:
            self._closed = True
            self._executor.shutdown(wait=False, cancel_futures=True)

    def add_audio(self, audio: np.ndarray, sample_rate: int) -> None:
        with self._lock:
            if self._closed:
                return
            self._sample_rate = sample_rate
            mono = np.asarray(audio, dtype=np.float32)
            self._buffer.append(mono)
            self._buffer_frames += mono.shape[0]
            self._collect_finished_locked()
            if self._ready_to_submit_locked():
                self._submit_locked()

    def flush(self, *, wait: bool) -> None:
        while True:
            with self._lock:
                self._collect_finished_locked()
                if self._future is None and self._buffer_frames > self._retained_overlap_frames:
                    self._submit_locked()
                future = self._future
                if future is None:
                    return
            if not wait:
                return
            try:
                future.result()
            except Exception:
                pass

    def _ready_to_submit_locked(self) -> bool:
        sample_rate = self._sample_rate
        if sample_rate is None or self._future is not None:
            return False
        return self._buffer_frames >= sample_rate * self.config.live_transcript_window_seconds

    def _submit_locked(self) -> None:
        sample_rate = self._sample_rate
        if sample_rate is None or not self._buffer:
            return
        audio = np.concatenate(self._buffer)
        offset = self._offset_seconds
        overlap_frames = self._overlap_frames(sample_rate)
        retained_frames = min(overlap_frames, audio.shape[0])
        advance_frames = audio.shape[0] - retained_frames
        self._offset_seconds += advance_frames / float(sample_rate)
        if retained_frames:
            self._buffer = [audio[-retained_frames:].copy()]
            self._buffer_frames = retained_frames
            self._retained_overlap_frames = retained_frames
        else:
            self._buffer = []
            self._buffer_frames = 0
            self._retained_overlap_frames = 0
        self._future = self._executor.submit(
            self._transcribe_chunk,
            audio,
            sample_rate,
            offset,
        )

    def _collect_finished_locked(self) -> None:
        if self._future is None or not self._future.done():
            return
        future = self._future
        self._future = None
        try:
            text = future.result().strip()
        except Exception as exc:
            self.status(f"Live transcript preview failed for a chunk; recording continues: {exc}")
            return
        text = self._dedupe_text(text)
        if not text:
            return
        with self.target.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")
        if self.preview:
            self.preview(text)

    def _overlap_frames(self, sample_rate: int) -> int:
        overlap_seconds = max(0, self.config.live_transcript_overlap_seconds)
        window_seconds = max(1, self.config.live_transcript_window_seconds)
        overlap_seconds = min(overlap_seconds, max(0, window_seconds - 1))
        return int(sample_rate * overlap_seconds)

    def _dedupe_text(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            normalized = _normalize_transcript_line(line)
            if not normalized or normalized in self._recent_lines:
                continue
            lines.append(line)
            self._recent_lines.append(normalized)
        self._recent_lines = self._recent_lines[-20:]
        return "\n".join(lines).strip()

    def _transcribe_chunk(self, audio: np.ndarray, sample_rate: int, offset_seconds: float) -> str:
        if self._model is None:
            self.status(
                f"Loading live transcript model {self.config.live_transcript_model} "
                f"on {self.config.live_transcript_device}/{self.config.live_transcript_compute_type}..."
            )
            self._model = _load_live_model(self.config)
        language_arg = None if self.language == Language.auto else self.language.value
        with tempfile.TemporaryDirectory(prefix="manola-live-") as temp_dir:
            chunk_path = Path(temp_dir) / "chunk.wav"
            write_wav(chunk_path, audio, sample_rate)
            segments, _info = self._model.transcribe(str(chunk_path), language=language_arg)
            return _segments_to_text(segments, offset=offset_seconds)


def _load_live_model(config: AppConfig):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise DependencyMissingError(
            "Live transcription requires faster-whisper. Install with: uv sync --extra local-transcription"
        ) from exc
    return WhisperModel(
        config.live_transcript_model,
        device=config.live_transcript_device,
        compute_type=config.live_transcript_compute_type,
    )


def _normalize_transcript_line(line: str) -> str:
    text = line.strip()
    if text.startswith("[") and "]" in text:
        text = text.split("]", 1)[1]
    return " ".join(text.casefold().split())
