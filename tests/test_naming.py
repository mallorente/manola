from datetime import datetime
from pathlib import Path

from nanola.models import MeetingType
from nanola.naming import meeting_folder_name, proposed_archive_parent, slugify


def test_slugify_keeps_stable_ascii_folder_names() -> None:
    assert slugify("Ana Garcia / Backend Role", "fallback") == "ana-garcia-backend-role"
    assert slugify("Grabación (38)", "fallback") == "grabacion-38"
    assert slugify("", "fallback") == "fallback"


def test_meeting_folder_name_uses_date_type_subject_and_topic() -> None:
    name = meeting_folder_name(
        created_at=datetime(2026, 5, 7, 12, 0),
        meeting_type=MeetingType.job_interview,
        title="Backend Role",
        attendees=["Ana Garcia"],
    )

    assert name == "2026-05-07__job-interview__ana-garcia__backend-role"


def test_meeting_folder_name_omits_duplicate_subject_topic() -> None:
    name = meeting_folder_name(
        created_at=datetime(2026, 5, 7, 12, 0),
        meeting_type=MeetingType.general,
        title="Recording 22:10",
        attendees=[],
    )

    assert name == "2026-05-07__general__recording-22-10"


def test_proposed_archive_parent_uses_project_when_present() -> None:
    parent = proposed_archive_parent(Path("Meetings"), "nanola", MeetingType.job_interview)

    assert parent == Path("Meetings") / "Projects" / "nanola"


def test_proposed_archive_parent_without_project_is_workspace_root() -> None:
    assert proposed_archive_parent(Path("Meetings"), None, MeetingType.general) == Path("Meetings")
