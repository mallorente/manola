import sys
import types
from collections import namedtuple
from pathlib import Path

from manola.config import AppConfig
from manola.diarization import SpeakerTurn, assign_speakers, diarize_audio, _relabel_turns


_Segment = namedtuple("_Segment", ["start", "end"])


def test_assign_speakers_labels_by_dominant_overlap() -> None:
    transcript = "[0.00-2.00] hello there\n[2.00-4.00] goodbye"
    turns = [
        SpeakerTurn(0.0, 1.5, "Speaker 1"),
        SpeakerTurn(1.5, 4.0, "Speaker 2"),
    ]
    result = assign_speakers(transcript, turns)
    assert result == "[0.00-2.00] Speaker 1: hello there\n[2.00-4.00] Speaker 2: goodbye"


def test_assign_speakers_returns_unchanged_without_turns() -> None:
    transcript = "[0.00-1.00] hi"
    assert assign_speakers(transcript, []) == transcript


def test_assign_speakers_passes_through_non_segment_lines() -> None:
    transcript = "# Heading\n[0.00-1.00] hi\nplain line"
    turns = [SpeakerTurn(0.0, 1.0, "Speaker 1")]
    result = assign_speakers(transcript, turns).splitlines()
    assert result[0] == "# Heading"
    assert result[1] == "[0.00-1.00] Speaker 1: hi"
    assert result[2] == "plain line"


def test_assign_speakers_leaves_non_overlapping_segment_unlabeled() -> None:
    transcript = "[10.00-11.00] later"
    turns = [SpeakerTurn(0.0, 1.0, "Speaker 1")]
    assert assign_speakers(transcript, turns) == transcript


def test_relabel_turns_assigns_stable_speaker_numbers() -> None:
    class FakeDiarization:
        def itertracks(self, yield_label=False):
            yield _Segment(0.0, 1.0), "_", "spk_b"
            yield _Segment(1.0, 2.0), "_", "spk_a"
            yield _Segment(2.0, 3.0), "_", "spk_b"

    turns = _relabel_turns(FakeDiarization())
    assert [t.speaker for t in turns] == ["Speaker 1", "Speaker 2", "Speaker 1"]


def test_diarize_audio_returns_none_when_pyannote_missing(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "pyannote.audio", None)
    messages: list[str] = []
    result = diarize_audio(Path("x.wav"), AppConfig(), status=messages.append)
    assert result is None
    assert any("pyannote" in message for message in messages)


def _install_fake_pyannote(monkeypatch, diarization) -> None:
    class FakePipeline:
        @classmethod
        def from_pretrained(cls, model, use_auth_token=None):
            return cls()

        def __call__(self, path):
            return diarization

    fake_module = types.ModuleType("pyannote.audio")
    fake_module.Pipeline = FakePipeline
    monkeypatch.setitem(sys.modules, "pyannote", types.ModuleType("pyannote"))
    monkeypatch.setitem(sys.modules, "pyannote.audio", fake_module)


def test_diarize_audio_returns_none_without_token(monkeypatch) -> None:
    _install_fake_pyannote(monkeypatch, diarization=None)
    monkeypatch.setattr("manola.diarization.has_secret", lambda name: False)
    messages: list[str] = []
    result = diarize_audio(Path("x.wav"), AppConfig(), status=messages.append)
    assert result is None
    assert any("token" in message.lower() for message in messages)


def test_diarize_audio_happy_path_returns_turns(monkeypatch) -> None:
    class FakeDiarization:
        def itertracks(self, yield_label=False):
            yield _Segment(0.0, 1.0), "_", "A"
            yield _Segment(1.0, 2.0), "_", "B"

    _install_fake_pyannote(monkeypatch, diarization=FakeDiarization())
    monkeypatch.setattr("manola.diarization.has_secret", lambda name: True)
    monkeypatch.setattr("manola.diarization.resolve_secret", lambda name: "hf_token")

    turns = diarize_audio(Path("x.wav"), AppConfig())
    assert turns is not None
    assert [t.speaker for t in turns] == ["Speaker 1", "Speaker 2"]


def test_diarize_audio_returns_none_on_pipeline_error(monkeypatch) -> None:
    class Boom:
        def itertracks(self, yield_label=False):
            raise RuntimeError("model exploded")

    # Pipeline call returns an object whose itertracks raises; relabel happens after
    # the call, but the call itself is what we guard. Simulate the call raising.
    class FakePipeline:
        @classmethod
        def from_pretrained(cls, model, use_auth_token=None):
            return cls()

        def __call__(self, path):
            raise RuntimeError("inference failed")

    fake_module = types.ModuleType("pyannote.audio")
    fake_module.Pipeline = FakePipeline
    monkeypatch.setitem(sys.modules, "pyannote", types.ModuleType("pyannote"))
    monkeypatch.setitem(sys.modules, "pyannote.audio", fake_module)
    monkeypatch.setattr("manola.diarization.has_secret", lambda name: True)
    monkeypatch.setattr("manola.diarization.resolve_secret", lambda name: "hf_token")

    messages: list[str] = []
    result = diarize_audio(Path("x.wav"), AppConfig(), status=messages.append)
    assert result is None
    assert any("failed" in message.lower() for message in messages)


def test_diarization_config_defaults() -> None:
    config = AppConfig()
    assert config.diarization_enabled is False
    assert config.diarization_model == "pyannote/speaker-diarization-3.1"
    assert config.huggingface_token_env == "HF_TOKEN"


def _import_meeting(monkeypatch, tmp_path: Path) -> Path:
    from manola.models import ProcessOptions
    from manola.pipeline import import_recording

    source = tmp_path / "rec.m4a"
    source.write_text("audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", lambda s, t: (t.write_text("WAV", encoding="utf-8"), t)[1])
    monkeypatch.setattr("manola.pipeline.transcribe_audio", lambda *a, **k: "[0.00-2.00] hello\n[2.00-4.00] bye")
    return import_recording(ProcessOptions(audio_path=source), AppConfig(workspace_dir=tmp_path / "meetings"))


def test_transcribe_meeting_applies_speaker_labels_when_diarize(monkeypatch, tmp_path: Path) -> None:
    import json

    from manola.pipeline import transcribe_meeting

    meeting_dir = _import_meeting(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "manola.pipeline.diarize_audio",
        lambda *a, **k: [SpeakerTurn(0.0, 2.0, "Speaker 1"), SpeakerTurn(2.0, 4.0, "Speaker 2")],
    )

    transcript_path = transcribe_meeting(meeting_dir, AppConfig(), diarize=True)

    transcript = transcript_path.read_text(encoding="utf-8")
    assert "Speaker 1: hello" in transcript
    assert "Speaker 2: bye" in transcript
    metadata = json.loads((meeting_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["diarized"] is True


def test_transcribe_meeting_skips_labels_when_diarization_unavailable(monkeypatch, tmp_path: Path) -> None:
    import json

    from manola.pipeline import transcribe_meeting

    meeting_dir = _import_meeting(monkeypatch, tmp_path)
    monkeypatch.setattr("manola.pipeline.diarize_audio", lambda *a, **k: None)

    transcript_path = transcribe_meeting(meeting_dir, AppConfig(), diarize=True)

    transcript = transcript_path.read_text(encoding="utf-8")
    assert "Speaker" not in transcript
    assert "hello" in transcript
    metadata = json.loads((meeting_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["diarized"] is False
