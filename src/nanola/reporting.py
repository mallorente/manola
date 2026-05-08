from __future__ import annotations

from datetime import datetime

import httpx

from .config import AppConfig, resolve_secret
from .errors import ConfigurationError, NanolaError
from .models import MeetingType, ProcessOptions


REPORT_SECTIONS = {
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
    prompt = _build_prompt(options, transcript, sections)

    response = httpx.post(
        f"{profile.base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": profile.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You generate concise, evidence-based Markdown meeting reports.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=600,
    )
    if response.status_code >= 400:
        raise NanolaError(f"LLM report generation failed: {response.status_code} {response.text}")

    payload = response.json()
    try:
        body = payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise NanolaError("LLM response did not contain choices[0].message.content.") from exc

    return _frontmatter(
        options,
        created_at,
        config=config,
        transcription_model=transcription_model,
        transcription_device=transcription_device,
        transcription_compute_type=transcription_compute_type,
    ) + "\n\n" + body


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
            "Audio: audio/original",
            "Transcript: transcript.md",
        ]
    )


def _build_prompt(options: ProcessOptions, transcript: str, sections: list[str]) -> str:
    attendees = ", ".join(options.attendees) if options.attendees else "none provided"
    section_list = "\n".join(f"- {section}" for section in sections)
    return f"""Create a Markdown report for this meeting.

Title: {options.title or "auto"}
Type: {options.meeting_type.value}
Project: {options.project or "none"}
Language: {options.language.value}
Attendees: {attendees}

Use these sections:
{section_list}

Transcript:
{transcript}
"""
