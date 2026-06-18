import json
from pathlib import Path

import pytest

from manola.config import AppConfig
from manola.errors import ManolaError
from manola.models import MetadataSuggestions, MeetingType, ProcessOptions, TranscriptionBackend
from manola.pipeline import apply_metadata_suggestions, apply_suggested_title, create_recorded_meeting, enrich_meeting, import_recording, process_recording, repair_meeting, resolve_meeting, summarize_meeting, transcribe_meeting


def _write_meeting(workspace: Path, *, title: str = "Old Title", attendees=None) -> Path:
    meeting_dir = workspace / "2026-06-18__general__old-title"
    (meeting_dir / "audio").mkdir(parents=True)
    metadata = {
        "id": meeting_dir.name,
        "title": title,
        "created_at": "2026-06-18T10:00:00",
        "meeting_type": "general",
        "project": None,
        "language": "en",
        "attendees": attendees or ["Ada"],
        "share_policy": "private",
        "transcription_backend": "local",
        "transcription_model": "large-v3",
        "transcription_device": "cuda",
        "transcription_compute_type": "float16",
        "llm_profile": "deepseek_fast",
        "audio_original": "audio/original.m4a",
        "audio_normalized": "audio/normalized.wav",
        "transcript": "transcript.md",
        "report": "report.md",
    }
    (meeting_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (meeting_dir / "transcript.md").write_text("# Transcript\n[0.00-1.00] hi\n", encoding="utf-8")
    (meeting_dir / "report.md").write_text("# Report\n", encoding="utf-8")
    (meeting_dir / "audio" / "original.m4a").write_text("ORIGINAL", encoding="utf-8")
    (meeting_dir / "audio" / "normalized.wav").write_text("truncated", encoding="utf-8")
    return meeting_dir


def test_repair_meeting_renormalizes_and_preserves_original(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    workspace.mkdir()
    meeting_dir = _write_meeting(workspace)

    def fake_normalize(source: Path, target: Path) -> Path:
        assert source.name == "original.m4a"
        target.write_text("renormalized", encoding="utf-8")
        return target

    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    monkeypatch.setattr("manola.pipeline.transcribe_audio", lambda *a, **k: "repaired transcript")

    repair_meeting(meeting_dir, AppConfig(workspace_dir=workspace))

    assert (meeting_dir / "audio" / "original.m4a").read_text(encoding="utf-8") == "ORIGINAL"
    assert (meeting_dir / "audio" / "normalized.wav").read_text(encoding="utf-8") == "renormalized"
    assert "repaired transcript" in (meeting_dir / "transcript.md").read_text(encoding="utf-8")


def test_repair_meeting_requires_source_audio(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    workspace.mkdir()
    meeting_dir = _write_meeting(workspace)
    (meeting_dir / "audio" / "original.m4a").unlink()

    with pytest.raises(ManolaError):
        repair_meeting(meeting_dir, AppConfig(workspace_dir=workspace))


def test_apply_metadata_suggestions_retitles_and_renames_folder(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    workspace.mkdir()
    meeting_dir = _write_meeting(workspace, title="Old Title")

    new_dir = apply_metadata_suggestions(meeting_dir, AppConfig(workspace_dir=workspace), {"title": "Quarterly Planning"})

    assert not meeting_dir.exists()
    assert new_dir.exists()
    metadata = json.loads((new_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["title"] == "Quarterly Planning"
    assert metadata["id"] == new_dir.name
    # Relative artifact paths stay valid after the rename.
    assert (new_dir / "transcript.md").exists()
    assert metadata["transcript"] == "transcript.md"


def test_apply_metadata_suggestions_applies_attendees_without_rename_when_name_unchanged(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    workspace.mkdir()
    meeting_dir = _write_meeting(workspace, title="Old Title")

    new_dir = apply_metadata_suggestions(meeting_dir, AppConfig(workspace_dir=workspace), {"project": "Atlas"})

    metadata = json.loads((new_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["project"] == "Atlas"


def test_apply_metadata_suggestions_rejects_empty_title(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    workspace.mkdir()
    meeting_dir = _write_meeting(workspace)

    with pytest.raises(ManolaError):
        apply_metadata_suggestions(meeting_dir, AppConfig(workspace_dir=workspace), {"title": "   "})


def test_apply_metadata_suggestions_ignores_unknown_fields(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    workspace.mkdir()
    meeting_dir = _write_meeting(workspace, title="Old Title")

    new_dir = apply_metadata_suggestions(meeting_dir, AppConfig(workspace_dir=workspace), {"llm_profile": "evil", "report": "../escape.md"})

    metadata = json.loads((new_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["llm_profile"] == "deepseek_fast"
    assert metadata["report"] == "report.md"


def fake_normalize(source_path: Path, target: Path) -> Path:
    target.write_text("wav", encoding="utf-8")
    return target


def test_process_recording_creates_expected_artifacts(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")

    def fake_normalize(source_path: Path, target: Path) -> Path:
        target.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        return target

    def fake_transcribe(*args, **kwargs) -> str:
        return "Speaker 1: Hello"

    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    monkeypatch.setattr("manola.pipeline.transcribe_audio", fake_transcribe)

    meeting_dir = process_recording(
        ProcessOptions(
            audio_path=source,
            meeting_type=MeetingType.job_interview,
            title="Backend Role",
            attendees=["Ana Garcia"],
            transcription_backend=TranscriptionBackend.remote,
        ),
        AppConfig(workspace_dir=tmp_path / "meetings"),
        generate_llm_report=False,
    )

    assert (meeting_dir / "metadata.json").exists()
    assert (meeting_dir / "report.md").exists()
    transcript = (meeting_dir / "transcript.md").read_text(encoding="utf-8")
    assert "Whisper model:" in transcript
    assert "Speaker 1: Hello" in transcript
    assert (meeting_dir / "audio" / "original.m4a").exists()
    assert (meeting_dir / "audio" / "normalized.wav").exists()


def test_summarize_meeting_rewrites_report(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")

    def fake_normalize(source_path: Path, target: Path) -> Path:
        target.write_text("wav", encoding="utf-8")
        return target

    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    monkeypatch.setattr("manola.pipeline.transcribe_audio", lambda *args, **kwargs: "transcript")
    meeting_dir = process_recording(
        ProcessOptions(audio_path=source, title="Meeting"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
        generate_llm_report=False,
    )
    monkeypatch.setattr(
        "manola.pipeline.generate_report",
        lambda **kwargs: "# Meeting\n\n## Summary\n\nLLM report",
    )

    report_path = summarize_meeting(meeting_dir, AppConfig())

    assert report_path == meeting_dir / "report.md"
    assert "LLM report" in report_path.read_text(encoding="utf-8")


def test_import_recording_creates_placeholders_without_transcribing(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "Grabación (38).m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)

    meeting_dir = import_recording(
        ProcessOptions(audio_path=source),
        AppConfig(workspace_dir=tmp_path / "meetings"),
    )

    assert "grabacion-38" in meeting_dir.name
    assert (meeting_dir / "transcript.md").read_text(encoding="utf-8") == ""
    assert (meeting_dir / "report.md").exists()


def test_transcribe_meeting_writes_transcript(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    monkeypatch.setattr("manola.pipeline.transcribe_audio", lambda *args, **kwargs: "new transcript")
    meeting_dir = import_recording(
        ProcessOptions(audio_path=source),
        AppConfig(workspace_dir=tmp_path / "meetings"),
    )

    transcript_path = transcribe_meeting(meeting_dir, AppConfig())

    transcript = transcript_path.read_text(encoding="utf-8")
    assert "Whisper model:" in transcript
    assert "new transcript" in transcript


def test_transcribe_meeting_skips_existing_transcript(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    meeting_dir = import_recording(
        ProcessOptions(audio_path=source),
        AppConfig(workspace_dir=tmp_path / "meetings"),
    )
    transcript_path = meeting_dir / "transcript.md"
    transcript_path.write_text("existing transcript", encoding="utf-8")

    def fail_transcribe(*args, **kwargs) -> str:
        raise AssertionError("transcription should be skipped")

    monkeypatch.setattr("manola.pipeline.transcribe_audio", fail_transcribe)

    result_path = transcribe_meeting(meeting_dir, AppConfig())

    assert result_path == transcript_path
    assert transcript_path.read_text(encoding="utf-8") == "existing transcript"


def test_transcribe_meeting_force_rewrites_existing_transcript(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    monkeypatch.setattr("manola.pipeline.transcribe_audio", lambda *args, **kwargs: "forced transcript")
    meeting_dir = import_recording(
        ProcessOptions(audio_path=source),
        AppConfig(workspace_dir=tmp_path / "meetings"),
    )
    transcript_path = meeting_dir / "transcript.md"
    transcript_path.write_text("existing transcript", encoding="utf-8")

    transcribe_meeting(meeting_dir, AppConfig(), force=True)

    assert "forced transcript" in transcript_path.read_text(encoding="utf-8")


def test_summarize_meeting_skips_existing_generated_report(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    monkeypatch.setattr("manola.pipeline.transcribe_audio", lambda *args, **kwargs: "transcript")
    meeting_dir = process_recording(
        ProcessOptions(audio_path=source, title="Meeting"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
        generate_llm_report=False,
    )
    report_path = meeting_dir / "report.md"
    report_path.write_text("# Meeting\n\nLLM model: deepseek-v4-flash\n\nGenerated report\n", encoding="utf-8")

    def fail_generate_report(**kwargs) -> str:
        raise AssertionError("report generation should be skipped")

    monkeypatch.setattr("manola.pipeline.generate_report", fail_generate_report)

    result_path = summarize_meeting(meeting_dir, AppConfig())

    assert result_path == report_path
    assert "Generated report" in report_path.read_text(encoding="utf-8")


def test_enrich_meeting_writes_metadata_suggestions(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    monkeypatch.setattr("manola.pipeline.transcribe_audio", lambda *args, **kwargs: "transcript")
    meeting_dir = process_recording(
        ProcessOptions(audio_path=source, title="Meeting"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
        generate_llm_report=False,
    )
    monkeypatch.setattr(
        "manola.pipeline.generate_metadata_suggestions",
        lambda **kwargs: MetadataSuggestions(
            suggested_title="Better title",
            suggested_attendees=["Ana"],
            summary="Discussed planning.",
        ),
    )

    suggestions_path = enrich_meeting(meeting_dir, AppConfig())

    assert suggestions_path == meeting_dir / "metadata.suggestions.json"
    suggestions = suggestions_path.read_text(encoding="utf-8")
    assert "Better title" in suggestions
    assert "Ana" in suggestions


def test_enrich_meeting_skips_existing_suggestions(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    monkeypatch.setattr("manola.pipeline.transcribe_audio", lambda *args, **kwargs: "transcript")
    meeting_dir = process_recording(
        ProcessOptions(audio_path=source, title="Meeting"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
        generate_llm_report=False,
    )
    suggestions_path = meeting_dir / "metadata.suggestions.json"
    suggestions_path.write_text('{"suggested_title":"Existing"}\n', encoding="utf-8")

    def fail_enrichment(**kwargs) -> MetadataSuggestions:
        raise AssertionError("enrichment should be skipped")

    monkeypatch.setattr("manola.pipeline.generate_metadata_suggestions", fail_enrichment)

    result_path = enrich_meeting(meeting_dir, AppConfig())

    assert result_path == suggestions_path
    assert "Existing" in suggestions_path.read_text(encoding="utf-8")


def test_apply_suggested_title_renames_generic_meeting(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    config = AppConfig(workspace_dir=tmp_path / "meetings")
    meeting_dir = import_recording(ProcessOptions(audio_path=source, title="Recording 10:30"), config)

    new_dir = apply_suggested_title(
        meeting_dir,
        config,
        MetadataSuggestions(suggested_title="Quarterly Budget Review"),
    )

    assert new_dir != meeting_dir
    assert not meeting_dir.exists()
    assert "quarterly-budget-review" in new_dir.name
    metadata = json.loads((new_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["title"] == "Quarterly Budget Review"
    assert metadata["id"] == new_dir.name


def test_apply_suggested_title_keeps_explicit_title(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    config = AppConfig(workspace_dir=tmp_path / "meetings")
    meeting_dir = import_recording(ProcessOptions(audio_path=source, title="Investor Sync"), config)

    new_dir = apply_suggested_title(
        meeting_dir,
        config,
        MetadataSuggestions(suggested_title="Something Else"),
    )

    assert new_dir == meeting_dir
    metadata = json.loads((meeting_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["title"] == "Investor Sync"


def test_apply_suggested_title_noop_without_suggestion(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    config = AppConfig(workspace_dir=tmp_path / "meetings")
    meeting_dir = import_recording(ProcessOptions(audio_path=source, title="Recording 10:30"), config)

    new_dir = apply_suggested_title(meeting_dir, config, MetadataSuggestions())

    assert new_dir == meeting_dir
    metadata = json.loads((meeting_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["title"] == "Recording 10:30"


def test_resolve_meeting_accepts_id(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("fake audio", encoding="utf-8")
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)
    config = AppConfig(workspace_dir=tmp_path / "meetings")
    meeting_dir = import_recording(ProcessOptions(audio_path=source, title="Meeting"), config)

    assert resolve_meeting(meeting_dir.name, config) == meeting_dir


def test_create_recorded_meeting_writes_recording_inside_meeting(monkeypatch, tmp_path: Path) -> None:
    class FakeRecording:
        path = tmp_path / "meetings" / "audio" / "recorded.wav"
        duration_seconds = 1.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    def fake_record_wav(*, source, duration_seconds, target, **kwargs):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("wav", encoding="utf-8")
        return FakeRecording()

    monkeypatch.setattr("manola.pipeline.record_wav", fake_record_wav)
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)

    meeting_dir, result = create_recorded_meeting(
        ProcessOptions(audio_path=Path("placeholder.wav"), title="Recorded Call"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
        source="meeting",
        duration_seconds=1,
    )

    assert (meeting_dir / "audio" / "recorded.wav").exists()
    assert (meeting_dir / "audio" / "normalized.wav").exists()
    assert result.rms == 0.1
    assert "recorded.wav" in (meeting_dir / "metadata.json").read_text(encoding="utf-8")


def test_create_recorded_meeting_enables_live_transcript_for_timed_meeting(monkeypatch, tmp_path: Path) -> None:
    class FakeRecording:
        path = tmp_path / "meetings" / "audio" / "recorded.wav"
        duration_seconds = 2.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    captured = {}

    def fake_record_meeting_until_stopped(*, target, on_audio_chunk, duration_seconds, **kwargs):
        captured["duration_seconds"] = duration_seconds
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("wav", encoding="utf-8")
        on_audio_chunk.__self__.target.write_text("live preview\n", encoding="utf-8")
        return FakeRecording()

    monkeypatch.setattr("manola.pipeline.record_meeting_until_stopped", fake_record_meeting_until_stopped)
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)

    meeting_dir, result = create_recorded_meeting(
        ProcessOptions(audio_path=Path("placeholder.wav"), title="Live Call"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
        source="meeting",
        duration_seconds=2,
        live_transcript=True,
    )

    assert captured["duration_seconds"] == 2
    assert result.rms == 0.1
    assert (meeting_dir / "live_transcript.md").read_text(encoding="utf-8") == "live preview\n"


def test_create_recorded_meeting_forwards_audio_level_callback(monkeypatch, tmp_path: Path) -> None:
    class FakeRecording:
        path = tmp_path / "meetings" / "audio" / "recorded.wav"
        duration_seconds = 2.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    captured = {}

    def fake_record_meeting_until_stopped(*, target, on_audio_level, **kwargs):
        captured["on_audio_level"] = on_audio_level
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("wav", encoding="utf-8")
        on_audio_level({"mic": 0.1, "system": 0.2})
        return FakeRecording()

    levels = []
    audio_level = levels.append
    monkeypatch.setattr("manola.pipeline.record_meeting_until_stopped", fake_record_meeting_until_stopped)
    monkeypatch.setattr("manola.pipeline.normalize_audio", fake_normalize)

    create_recorded_meeting(
        ProcessOptions(audio_path=Path("placeholder.wav"), title="Measured Call"),
        AppConfig(workspace_dir=tmp_path / "meetings"),
        source="meeting",
        duration_seconds=None,
        audio_level=audio_level,
    )

    assert captured["on_audio_level"] is audio_level
    assert levels == [{"mic": 0.1, "system": 0.2}]
