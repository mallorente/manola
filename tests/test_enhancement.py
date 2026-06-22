import json
from pathlib import Path

import pytest

from manola.audio import normalize_enhance_mode
from manola.config import AppConfig
from manola.errors import ManolaError
from manola.exporting import _files_for_policy
from manola.models import ProcessOptions, SharePolicy
from manola.pipeline import import_recording, transcribe_meeting


def _fake_normalize(source_path: Path, target: Path) -> Path:
    target.write_text("NORMALIZED", encoding="utf-8")
    return target


def _fake_enhance(source: Path, target: Path, *, mode: str) -> Path:
    target.write_text(f"ENHANCED-{mode}", encoding="utf-8")
    return target


@pytest.mark.parametrize("value", [None, "", "off", "OFF", "  off  "])
def test_normalize_enhance_mode_off_means_no_enhancement(value) -> None:
    assert normalize_enhance_mode(value) is None


@pytest.mark.parametrize("value,expected", [("light", "light"), ("Denoise", "denoise"), ("SPEECH", "speech")])
def test_normalize_enhance_mode_resolves_known_modes(value, expected) -> None:
    assert normalize_enhance_mode(value) == expected


def test_normalize_enhance_mode_rejects_unknown() -> None:
    with pytest.raises(ManolaError):
        normalize_enhance_mode("turbo")


def test_import_with_off_writes_no_enhanced_audio(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "rec.m4a"
    source.write_text("audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", _fake_normalize)
    monkeypatch.setattr("manola.pipeline.enhance_voice", _fake_enhance)

    meeting_dir = import_recording(
        ProcessOptions(audio_path=source, enhance_voice="off"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
    )

    assert not (meeting_dir / "audio" / "enhanced.wav").exists()
    metadata = json.loads((meeting_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["audio_enhanced"] is None
    assert metadata["enhancement_mode"] is None


def test_import_with_mode_writes_enhanced_and_preserves_others(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "rec.m4a"
    source.write_text("audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", _fake_normalize)
    monkeypatch.setattr("manola.pipeline.enhance_voice", _fake_enhance)

    meeting_dir = import_recording(
        ProcessOptions(audio_path=source, enhance_voice="speech"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
    )

    enhanced = meeting_dir / "audio" / "enhanced.wav"
    assert enhanced.read_text(encoding="utf-8") == "ENHANCED-speech"
    # Original and normalized audio are untouched.
    assert (meeting_dir / "audio").glob("original.*")
    assert (meeting_dir / "audio" / "normalized.wav").read_text(encoding="utf-8") == "NORMALIZED"
    metadata = json.loads((meeting_dir / "metadata.json").read_text(encoding="utf-8"))
    assert Path(metadata["audio_enhanced"]) == Path("audio/enhanced.wav")
    assert metadata["enhancement_mode"] == "speech"


def test_transcribe_prefers_enhanced_audio(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "rec.m4a"
    source.write_text("audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", _fake_normalize)
    monkeypatch.setattr("manola.pipeline.enhance_voice", _fake_enhance)

    meeting_dir = import_recording(
        ProcessOptions(audio_path=source, enhance_voice="denoise"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
    )

    seen: dict[str, Path] = {}

    def fake_transcribe(audio_path, **kwargs):
        seen["path"] = audio_path
        return "transcribed text"

    monkeypatch.setattr("manola.pipeline.transcribe_audio", fake_transcribe)
    transcribe_meeting(meeting_dir, AppConfig())

    assert seen["path"].name == "enhanced.wav"


def test_transcribe_falls_back_to_normalized_when_enhanced_missing(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "rec.m4a"
    source.write_text("audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", _fake_normalize)
    monkeypatch.setattr("manola.pipeline.enhance_voice", _fake_enhance)

    meeting_dir = import_recording(
        ProcessOptions(audio_path=source, enhance_voice="light"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
    )
    # Simulate the enhanced artifact going missing after import.
    (meeting_dir / "audio" / "enhanced.wav").unlink()

    seen: dict[str, Path] = {}

    def fake_transcribe(audio_path, **kwargs):
        seen["path"] = audio_path
        return "text"

    monkeypatch.setattr("manola.pipeline.transcribe_audio", fake_transcribe)
    transcribe_meeting(meeting_dir, AppConfig())

    assert seen["path"].name == "normalized.wav"


def test_export_all_includes_enhanced_when_present() -> None:
    metadata = {
        "audio_original": "audio/original.m4a",
        "audio_normalized": "audio/normalized.wav",
        "audio_enhanced": "audio/enhanced.wav",
    }
    files = _files_for_policy(SharePolicy.all, metadata)
    assert Path("audio/enhanced.wav") in files


def test_export_all_omits_enhanced_when_absent() -> None:
    metadata = {
        "audio_original": "audio/original.m4a",
        "audio_normalized": "audio/normalized.wav",
        "audio_enhanced": None,
    }
    files = _files_for_policy(SharePolicy.all, metadata)
    assert Path("audio/enhanced.wav") not in files


def test_default_enhance_voice_config_default() -> None:
    assert AppConfig().default_enhance_voice == "off"
