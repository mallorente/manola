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
    client_update = "client_update"
    internal_sync = "internal_sync"
    one_on_one = "one_on_one"
    job_interview = "job_interview"
    case_interview = "case_interview"
    project_review = "project_review"
    incident_postmortem = "incident_postmortem"
    brainstorm = "brainstorm"
    strategy = "strategy"
    workshop = "workshop"
    refinement = "refinement"
    daily = "daily"
    retro = "retro"
    planning = "planning"


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
    enhance_voice: str | None = None


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
    audio_enhanced: str | None = None
    enhancement_mode: str | None = None
    diarized: bool = False
    transcript: str
    report: str


class NameCorrectionSuggestion(BaseModel):
    heard_as: str
    suggested: str
    confidence: str = "medium"
    evidence: str | None = None


class MetadataSuggestions(BaseModel):
    suggested_title: str | None = None
    suggested_meeting_type: MeetingType | None = None
    suggested_project: str | None = None
    suggested_attendees: list[str] = Field(default_factory=list)
    notable_terms: list[str] = Field(default_factory=list)
    possible_name_corrections: list[NameCorrectionSuggestion] = Field(default_factory=list)
    summary: str | None = None
    confidence_notes: list[str] = Field(default_factory=list)
