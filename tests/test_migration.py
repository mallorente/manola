import json
from pathlib import Path

from manola.config import AppConfig
from manola.migration import detect_legacy_meetings, migrate_legacy_meetings


def _write_meeting(
    parent: Path,
    *,
    name: str = "2026-06-18__general__old-title",
    meeting_type: str = "general",
    project: str | None = None,
) -> Path:
    meeting_dir = parent / name
    (meeting_dir / "audio").mkdir(parents=True)
    metadata = {
        "id": name,
        "title": "Old Title",
        "created_at": "2026-06-18T10:00:00",
        "meeting_type": meeting_type,
        "project": project,
        "language": "en",
        "attendees": ["Ada"],
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
    (meeting_dir / "transcript.md").write_text("# Transcript\n", encoding="utf-8")
    (meeting_dir / "audio" / "original.m4a").write_text("ORIGINAL", encoding="utf-8")
    return meeting_dir


def test_detect_ignores_simplified_layout(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    workspace.mkdir()
    _write_meeting(workspace)

    assert detect_legacy_meetings(AppConfig(workspace_dir=workspace)) == []


def test_detect_flags_nested_legacy_meeting(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    nested = workspace / "General" / "General" / "Meetings"
    _write_meeting(nested)

    legacy = detect_legacy_meetings(AppConfig(workspace_dir=workspace))

    assert len(legacy) == 1
    assert legacy[0].target_dir == workspace / "2026-06-18__general__old-title"


def test_migrate_relocates_preserves_data_and_prunes(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    nested = workspace / "General" / "General" / "Meetings"
    _write_meeting(nested)
    config = AppConfig(workspace_dir=workspace)

    moves = migrate_legacy_meetings(config, apply=True)

    assert len(moves) == 1
    target = workspace / "2026-06-18__general__old-title"
    assert target.exists()
    assert (target / "audio" / "original.m4a").read_text(encoding="utf-8") == "ORIGINAL"
    # metadata.id is updated to the new folder name.
    metadata = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["id"] == target.name
    # Emptied legacy parents are pruned but the workspace survives.
    assert not (workspace / "General").exists()
    assert workspace.exists()
    # No legacy meetings remain.
    assert detect_legacy_meetings(config) == []


def test_dry_run_does_not_move_anything(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    nested = workspace / "General" / "General" / "Meetings"
    meeting_dir = _write_meeting(nested)
    config = AppConfig(workspace_dir=workspace)

    moves = migrate_legacy_meetings(config, apply=False)

    assert len(moves) == 1
    assert moves[0] == (meeting_dir, workspace / "2026-06-18__general__old-title")
    assert meeting_dir.exists()
    assert not (workspace / "2026-06-18__general__old-title").exists()


def test_migrate_resolves_name_collision(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    # An already-correct meeting occupies the canonical leaf name.
    _write_meeting(workspace)
    # A legacy meeting nested under type folders shares the same leaf name.
    nested = workspace / "General" / "General" / "Meetings"
    _write_meeting(nested)
    config = AppConfig(workspace_dir=workspace)

    moves = migrate_legacy_meetings(config, apply=True)

    assert len(moves) == 1
    _, new_dir = moves[0]
    assert new_dir == workspace / "2026-06-18__general__old-title-2"
    assert new_dir.exists()
    # The pre-existing meeting is untouched.
    assert (workspace / "2026-06-18__general__old-title").exists()


def test_migrate_project_meeting_targets_projects_folder(tmp_path: Path) -> None:
    workspace = tmp_path / "meetings"
    nested = workspace / "Projects" / "Legacy" / "old"
    _write_meeting(nested, project="Legaltech")
    config = AppConfig(workspace_dir=workspace)

    moves = migrate_legacy_meetings(config, apply=True)

    assert len(moves) == 1
    _, new_dir = moves[0]
    assert new_dir == workspace / "Projects" / "legaltech" / "2026-06-18__general__old-title"
    assert new_dir.exists()
