import json
from pathlib import Path

from manola.config import AppConfig
from manola.exporting import export_meeting
from manola.models import SharePolicy


def test_export_meeting_copies_report_and_transcript(tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meeting"
    meeting_dir.mkdir()
    (meeting_dir / "report.md").write_text("report", encoding="utf-8")
    (meeting_dir / "transcript.md").write_text("transcript", encoding="utf-8")
    (meeting_dir / "metadata.json").write_text(
        json.dumps({"share_policy": "report_transcript"}),
        encoding="utf-8",
    )

    shared_dir = tmp_path / "shared"
    target = export_meeting(meeting_dir, AppConfig(shared_dir=shared_dir))

    assert target == shared_dir / "meeting"
    assert (target / "report.md").read_text(encoding="utf-8") == "report"
    assert (target / "transcript.md").read_text(encoding="utf-8") == "transcript"


def test_export_policy_override_can_export_report_only(tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meeting"
    meeting_dir.mkdir()
    (meeting_dir / "report.md").write_text("report", encoding="utf-8")
    (meeting_dir / "transcript.md").write_text("transcript", encoding="utf-8")
    (meeting_dir / "metadata.json").write_text(
        json.dumps({"share_policy": "private"}),
        encoding="utf-8",
    )

    target = export_meeting(
        meeting_dir,
        AppConfig(shared_dir=tmp_path / "shared"),
        SharePolicy.report,
    )

    assert (target / "report.md").exists()
    assert not (target / "transcript.md").exists()


def test_export_all_uses_metadata_audio_paths(tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meeting"
    audio_dir = meeting_dir / "audio"
    audio_dir.mkdir(parents=True)
    (meeting_dir / "report.md").write_text("report", encoding="utf-8")
    (meeting_dir / "transcript.md").write_text("transcript", encoding="utf-8")
    (audio_dir / "original.mp3").write_text("original", encoding="utf-8")
    (audio_dir / "normalized.wav").write_text("normalized", encoding="utf-8")
    (meeting_dir / "metadata.json").write_text(
        json.dumps(
            {
                "share_policy": "all",
                "audio_original": "audio/original.mp3",
                "audio_normalized": "audio/normalized.wav",
            }
        ),
        encoding="utf-8",
    )

    target = export_meeting(meeting_dir, AppConfig(shared_dir=tmp_path / "shared"))

    assert (target / "audio" / "original.mp3").exists()
    assert (target / "audio" / "normalized.wav").exists()
    assert (target / "metadata.json").exists()
