from pathlib import Path

import numpy as np

from manola.config import AppConfig
from manola.live_transcription import LiveTranscriptSession
from manola.models import Language


class Segment:
    start = 0.0
    end = 0.5
    text = "hello live"


class FakeModel:
    def transcribe(self, path: str, language: str | None = None):
        assert Path(path).exists()
        assert language == "en"
        return [Segment()], None


class DuplicateModel:
    def transcribe(self, path: str, language: str | None = None):
        assert Path(path).exists()
        return [Segment()], None


def test_live_transcript_session_writes_preview_chunks(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("manola.live_transcription._load_live_model", lambda config: FakeModel())
    previews: list[str] = []

    with LiveTranscriptSession(
        target=tmp_path / "live_transcript.md",
        language=Language.en,
        config=AppConfig(live_transcript_window_seconds=1),
        preview=previews.append,
    ) as live:
        live.add_audio(np.ones(8000, dtype=np.float32) * 0.1, 16000)
        live.add_audio(np.ones(8000, dtype=np.float32) * 0.1, 16000)

    text = (tmp_path / "live_transcript.md").read_text(encoding="utf-8")
    assert "Preview quality" in text
    assert "[0.00-0.50] hello live" in text
    assert previews == ["[0.00-0.50] hello live"]


def test_live_transcript_session_dedupes_overlap_lines(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("manola.live_transcription._load_live_model", lambda config: DuplicateModel())
    previews: list[str] = []

    with LiveTranscriptSession(
        target=tmp_path / "live_transcript.md",
        language=Language.auto,
        config=AppConfig(live_transcript_window_seconds=1, live_transcript_overlap_seconds=0),
        preview=previews.append,
    ) as live:
        live.add_audio(np.ones(16000, dtype=np.float32) * 0.1, 16000)
        live.flush(wait=True)
        live.add_audio(np.ones(16000, dtype=np.float32) * 0.1, 16000)

    text = (tmp_path / "live_transcript.md").read_text(encoding="utf-8")
    assert text.count("hello live") == 1
    assert previews == ["[0.00-0.50] hello live"]
