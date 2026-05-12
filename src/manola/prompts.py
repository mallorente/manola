from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig
from .errors import ManolaError
from .models import MeetingType, ProcessOptions


DEFAULT_PROMPTS_DIR = Path(__file__).parent / "prompts" / "defaults"


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    text: str
    source: Path
    is_user_override: bool
    profile: str | None = None

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:12]


def prompt_name_for_meeting_type(meeting_type: MeetingType) -> str:
    default_path = DEFAULT_PROMPTS_DIR / f"{meeting_type.value}.md"
    if default_path.exists():
        return meeting_type.value
    return MeetingType.general.value


def load_prompt_template(name: str, config: AppConfig, *, profile: str | None = None) -> PromptTemplate:
    if not name.replace("_", "").isalnum():
        raise ManolaError("Prompt name must contain only letters, numbers, and underscores.")
    if profile is not None and not profile.replace("_", "").replace("-", "").isalnum():
        raise ManolaError("Prompt profile must contain only letters, numbers, underscores, and dashes.")

    candidate_paths: list[tuple[Path, bool, str | None]] = []
    if profile is not None:
        candidate_paths.append((config.prompts_dir / "models" / profile / f"{name}.md", True, profile))
    candidate_paths.append((config.prompts_dir / f"{name}.md", True, None))
    if profile is not None:
        candidate_paths.append((DEFAULT_PROMPTS_DIR / "models" / profile / f"{name}.md", False, profile))
    candidate_paths.append((DEFAULT_PROMPTS_DIR / f"{name}.md", False, None))

    for path, is_user_override, template_profile in candidate_paths:
        if path.exists():
            return PromptTemplate(
                name=name,
                text=path.read_text(encoding="utf-8-sig" if is_user_override else "utf-8"),
                source=path,
                is_user_override=is_user_override,
                profile=template_profile,
            )

    fallback_path = DEFAULT_PROMPTS_DIR / "general.md"
    return PromptTemplate(
        name="general",
        text=fallback_path.read_text(encoding="utf-8"),
        source=fallback_path,
        is_user_override=False,
        profile=None,
    )


def load_system_prompt(config: AppConfig, *, profile: str | None = None) -> PromptTemplate:
    return load_prompt_template("system", config, profile=profile)


def load_report_prompt(meeting_type: MeetingType, config: AppConfig, *, profile: str | None = None) -> PromptTemplate:
    return load_prompt_template(prompt_name_for_meeting_type(meeting_type), config, profile=profile)


def render_report_prompt(
    *,
    template: PromptTemplate,
    options: ProcessOptions,
    transcript: str,
    sections: list[str],
    model_profile: str | None = None,
    model_name: str | None = None,
) -> str:
    attendees = ", ".join(options.attendees) if options.attendees else "none provided"
    section_list = "\n".join(f"- {section}" for section in sections)
    values = {
        "title": options.title or "auto",
        "meeting_type": options.meeting_type.value,
        "project": options.project or "none",
        "language": options.language.value,
        "attendees": attendees,
        "sections": section_list,
        "transcript": transcript,
        "model_profile": model_profile or "unknown",
        "model_name": model_name or "unknown",
    }
    rendered = template.text
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def render_enrichment_prompt(
    *,
    template: PromptTemplate,
    options: ProcessOptions,
    transcript: str,
    model_profile: str | None = None,
    model_name: str | None = None,
) -> str:
    attendees = ", ".join(options.attendees) if options.attendees else "none provided"
    values = {
        "title": options.title or "auto",
        "meeting_type": options.meeting_type.value,
        "project": options.project or "none",
        "language": options.language.value,
        "attendees": attendees,
        "transcript": transcript,
        "model_profile": model_profile or "unknown",
        "model_name": model_name or "unknown",
    }
    rendered = template.text
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def iter_prompt_status(config: AppConfig) -> list[tuple[str, Path, bool]]:
    names = ["system", "enrich"] + [meeting_type.value for meeting_type in MeetingType]
    rows: list[tuple[str, Path, bool]] = []
    for name in names:
        template = load_prompt_template(name, config)
        rows.append((name, template.source, template.is_user_override))
    for profile in config.llm_profiles:
        for name in names:
            template = load_prompt_template(name, config, profile=profile)
            if template.profile == profile:
                rows.append((f"{profile}/{name}", template.source, template.is_user_override))
    return rows
