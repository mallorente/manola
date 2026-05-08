from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class Language(StrEnum):
    auto = "auto"
    es = "es"
    en = "en"


class SharePolicy(StrEnum):
    private = "private"
    report = "report"
    report_transcript = "report_transcript"
    all = "all"


class TranscriptionBackend(StrEnum):
    local = "local"
    remote = "remote"


class MeetingType(StrEnum):
    general = "general"
    sales_discovery = "sales_discovery"
    sales_demo = "sales_demo"
    customer_success = "customer_success"
    internal_sync = "internal_sync"
    one_on_one = "one_on_one"
    job_interview = "job_interview"
    case_interview = "case_interview"
    project_review = "project_review"
    incident_postmortem = "incident_postmortem"
    brainstorm = "brainstorm"


class ProcessOptions(BaseModel):
    audio_path: Path
    meeting_type: MeetingType = MeetingType.general
    project: str | None = None
    language: Language = Language.auto
    title: str | None = None
    attendees: list[str] = Field(default_factory=list)
    share_policy: SharePolicy = SharePolicy.private
    transcription_backend: TranscriptionBackend = TranscriptionBackend.local
    llm_profile: str = "deepseek_fast"


class MeetingMetadata(BaseModel):
    id: str
    title: str
    created_at: datetime
    meeting_type: MeetingType
    project: str | None
    language: Language
    attendees: list[str]
    share_policy: SharePolicy
    transcription_backend: TranscriptionBackend
    transcription_model: str | None = None
    transcription_device: str | None = None
    transcription_compute_type: str | None = None
    llm_profile: str
    audio_original: str
    audio_normalized: str
    transcript: str
    report: str
