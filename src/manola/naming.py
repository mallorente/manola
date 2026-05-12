from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path

from .models import MeetingType


TYPE_FOLDER_NAMES = {
    MeetingType.general: ("General", "Meetings"),
    MeetingType.sales_discovery: ("Sales", "Discovery"),
    MeetingType.sales_demo: ("Sales", "Demos"),
    MeetingType.customer_success: ("Customer Success", "Meetings"),
    MeetingType.client_update: ("Clients", "Updates"),
    MeetingType.internal_sync: ("Internal", "Syncs"),
    MeetingType.one_on_one: ("Internal", "One On Ones"),
    MeetingType.job_interview: ("Hiring", "Job Interviews"),
    MeetingType.case_interview: ("Hiring", "Case Interviews"),
    MeetingType.project_review: ("Projects", "Reviews"),
    MeetingType.incident_postmortem: ("Operations", "Incident Postmortems"),
    MeetingType.brainstorm: ("General", "Brainstorms"),
    MeetingType.strategy: ("Leadership", "Strategy"),
    MeetingType.workshop: ("General", "Workshops"),
    MeetingType.refinement: ("Product", "Refinement"),
    MeetingType.daily: ("Product", "Dailies"),
    MeetingType.retro: ("Product", "Retros"),
    MeetingType.planning: ("Product", "Planning"),
}


def slugify(value: str | None, fallback: str) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or fallback


def infer_main_subject(title: str | None, attendees: list[str]) -> str:
    if attendees:
        return attendees[0]
    return title or "meeting"


def meeting_folder_name(
    *,
    created_at: datetime,
    meeting_type: MeetingType,
    title: str | None,
    attendees: list[str],
) -> str:
    subject = slugify(infer_main_subject(title, attendees), "meeting")
    topic = slugify(title, "notes")
    parts = [f"{created_at:%Y-%m-%d}", meeting_type.value.replace("_", "-"), subject]
    if topic != subject:
        parts.append(topic)
    return "__".join(parts)


def proposed_archive_parent(workspace_dir: Path, project: str | None, meeting_type: MeetingType) -> Path:
    if project:
        return workspace_dir / "Projects" / project
    return workspace_dir
