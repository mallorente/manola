from __future__ import annotations

import json
from datetime import datetime

import httpx

from .config import AppConfig, resolve_secret
from .errors import ConfigurationError, ManolaError
from pydantic import ValidationError

from .models import MetadataSuggestions, MeetingType, ProcessOptions
from .prompts import load_prompt_template, load_report_prompt, load_system_prompt, render_enrichment_prompt, render_report_prompt


REPORT_SECTIONS = {
    MeetingType.sales_discovery: [
        "Account Snapshot",
        "Customer Context",
        "Pain Points",
        "Current Process",
        "Decision Criteria",
        "Stakeholders",
        "Risks / Objections",
        "Next Steps",
    ],
    MeetingType.sales_demo: [
        "Demo Context",
        "Customer Goals",
        "Features Covered",
        "Customer Reactions",
        "Questions / Objections",
        "Fit Assessment",
        "Follow-up Items",
        "Next Steps",
    ],
    MeetingType.customer_success: [
        "Account Health",
        "Customer Goals",
        "Progress Since Last Check-in",
        "Issues / Risks",
        "Requests / Feedback",
        "Renewal or Expansion Signals",
        "Action Items",
        "Next Steps",
    ],
    MeetingType.client_update: [
        "Executive Summary",
        "Progress Update",
        "Decisions",
        "Risks / Blockers",
        "Client Feedback",
        "Action Items",
        "Next Steps",
    ],
    MeetingType.internal_sync: [
        "Summary",
        "Team Updates",
        "Decisions",
        "Blockers",
        "Dependencies",
        "Action Items",
        "Next Steps",
    ],
    MeetingType.one_on_one: [
        "Summary",
        "Topics Discussed",
        "Feedback",
        "Support Needed",
        "Growth / Development",
        "Action Items",
        "Follow-up",
    ],
    MeetingType.job_interview: [
        "Recommendation",
        "Candidate profile",
        "Motivation",
        "Relevant experience",
        "Strong signals",
        "Weak signals",
        "Risks / doubts",
        "Fit with role",
        "Follow-up questions",
        "Next steps",
    ],
    MeetingType.case_interview: [
        "Recommendation",
        "Case context",
        "Reasoning structure",
        "Analysis quality",
        "Use of data and assumptions",
        "Communication",
        "Response to questions",
        "Strong signals",
        "Weak signals",
        "Risks / doubts",
        "Next steps",
    ],
    MeetingType.project_review: [
        "Project Status",
        "Milestones",
        "Scope / Timeline / Budget",
        "Risks",
        "Decisions",
        "Open Questions",
        "Action Items",
        "Next Steps",
    ],
    MeetingType.incident_postmortem: [
        "Incident Summary",
        "Impact",
        "Timeline",
        "Root Cause / Contributing Factors",
        "What Went Well",
        "What Went Wrong",
        "Corrective Actions",
        "Owners and Deadlines",
    ],
    MeetingType.brainstorm: [
        "Goal",
        "Ideas",
        "Themes",
        "Promising Directions",
        "Concerns / Constraints",
        "Decisions",
        "Next Experiments",
    ],
    MeetingType.strategy: [
        "Strategic Context",
        "Options Discussed",
        "Tradeoffs",
        "Decisions",
        "Risks",
        "Open Questions",
        "Action Items",
        "Next Steps",
    ],
    MeetingType.workshop: [
        "Workshop Goal",
        "Participants / Roles",
        "Activities",
        "Outputs",
        "Decisions",
        "Open Questions",
        "Action Items",
        "Next Steps",
    ],
    MeetingType.refinement: [
        "Scope Reviewed",
        "User Stories / Items",
        "Clarifications",
        "Acceptance Criteria",
        "Dependencies",
        "Risks / Unknowns",
        "Decisions",
        "Next Steps",
    ],
    MeetingType.daily: [
        "Team Progress",
        "Today",
        "Blockers",
        "Dependencies",
        "Risks",
        "Action Items",
    ],
    MeetingType.retro: [
        "Context",
        "What Went Well",
        "What Did Not Go Well",
        "Learnings",
        "Improvement Ideas",
        "Action Items",
        "Owners and Follow-up",
    ],
    MeetingType.planning: [
        "Planning Goal",
        "Scope",
        "Priorities",
        "Capacity / Constraints",
        "Risks",
        "Decisions",
        "Action Items",
        "Next Steps",
    ],
}

DEFAULT_SECTIONS = [
    "Summary",
    "Key Points",
    "Decisions",
    "Action Items",
    "Open Questions",
    "Notes by Topic",
]


def generate_report(
    *,
    options: ProcessOptions,
    transcript: str,
    config: AppConfig,
    created_at: datetime,
    transcription_model: str | None = None,
    transcription_device: str | None = None,
    transcription_compute_type: str | None = None,
) -> str:
    profile = config.llm_profiles.get(options.llm_profile)
    if profile is None:
        raise ConfigurationError(f"Unknown LLM profile {options.llm_profile!r}.")

    api_key = resolve_secret(profile.api_key_env)
    sections = REPORT_SECTIONS.get(options.meeting_type, DEFAULT_SECTIONS)
    system_prompt = load_system_prompt(config, profile=options.llm_profile)
    report_prompt = load_report_prompt(options.meeting_type, config, profile=options.llm_profile)
    prompt = render_report_prompt(
        template=report_prompt,
        options=options,
        transcript=transcript,
        sections=sections,
        model_profile=options.llm_profile,
        model_name=profile.model,
    )

    response = httpx.post(
        f"{profile.base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": profile.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt.text.strip(),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": profile.temperature,
        },
        timeout=600,
    )
    if response.status_code >= 400:
        raise ManolaError(f"LLM report generation failed: {response.status_code} {response.text}")

    payload = response.json()
    try:
        body = payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ManolaError("LLM response did not contain choices[0].message.content.") from exc

    return _frontmatter(
        options,
        created_at,
        config=config,
        transcription_model=transcription_model,
        transcription_device=transcription_device,
        transcription_compute_type=transcription_compute_type,
        prompt_source=report_prompt.source,
        prompt_hash=report_prompt.digest,
    ) + "\n\n" + body


def generate_metadata_suggestions(
    *,
    options: ProcessOptions,
    transcript: str,
    config: AppConfig,
) -> MetadataSuggestions:
    profile = config.llm_profiles.get(options.llm_profile)
    if profile is None:
        raise ConfigurationError(f"Unknown LLM profile {options.llm_profile!r}.")

    api_key = resolve_secret(profile.api_key_env)
    system_prompt = load_system_prompt(config, profile=options.llm_profile)
    enrichment_prompt = load_prompt_template("enrich", config, profile=options.llm_profile)
    prompt = render_enrichment_prompt(
        template=enrichment_prompt,
        options=options,
        transcript=transcript,
        model_profile=options.llm_profile,
        model_name=profile.model,
    )
    response = httpx.post(
        f"{profile.base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": profile.model,
            "messages": [
                {"role": "system", "content": system_prompt.text.strip()},
                {"role": "user", "content": prompt},
            ],
            "temperature": profile.enrichment_temperature,
        },
        timeout=600,
    )
    if response.status_code >= 400:
        raise ManolaError(f"LLM enrichment failed: {response.status_code} {response.text}")

    payload = response.json()
    try:
        body = payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ManolaError("LLM response did not contain choices[0].message.content.") from exc

    try:
        raw_suggestions = json.loads(_strip_json_fence(body))
        return MetadataSuggestions.model_validate(raw_suggestions)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ManolaError(f"LLM enrichment response was not valid metadata suggestions JSON: {exc}") from exc


def fallback_report(*, options: ProcessOptions, transcript: str, created_at: datetime) -> str:
    sections = REPORT_SECTIONS.get(options.meeting_type, DEFAULT_SECTIONS)
    body = "\n\n".join(f"## {section}\n\nTBD" for section in sections)
    transcript_preview = transcript[:2000].strip()
    if transcript_preview:
        body += f"\n\n## Transcript Preview\n\n{transcript_preview}"
    return _frontmatter(options, created_at) + "\n\n" + body


def _frontmatter(
    options: ProcessOptions,
    created_at: datetime,
    *,
    config: AppConfig | None = None,
    transcription_model: str | None = None,
    transcription_device: str | None = None,
    transcription_compute_type: str | None = None,
    prompt_source=None,
    prompt_hash: str | None = None,
) -> str:
    attendees = ", ".join(options.attendees) if options.attendees else "none"
    llm_profile = config.llm_profiles.get(options.llm_profile) if config else None
    llm_model = llm_profile.model if llm_profile else "not generated"
    return "\n".join(
        [
            f"# {options.title or 'Untitled meeting'}",
            "",
            f"Date: {created_at:%Y-%m-%d}",
            f"Type: {options.meeting_type.value}",
            f"Project: {options.project or 'none'}",
            f"Attendees: {attendees}",
            f"Language: {options.language.value}",
            f"Whisper model: {transcription_model or 'unknown'}",
            f"Whisper device: {transcription_device or 'unknown'}",
            f"Whisper compute type: {transcription_compute_type or 'unknown'}",
            f"LLM profile: {options.llm_profile}",
            f"LLM model: {llm_model}",
            f"Prompt source: {prompt_source or 'default fallback'}",
            f"Prompt hash: {prompt_hash or 'unknown'}",
            "Audio: audio/original",
            "Transcript: transcript.md",
        ]
    )


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
