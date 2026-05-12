from pathlib import Path

from manola.config import AppConfig
from manola.models import MeetingType, ProcessOptions
from manola.prompts import (
    DEFAULT_PROMPTS_DIR,
    load_prompt_template,
    load_report_prompt,
    load_system_prompt,
    render_report_prompt,
)


def test_load_report_prompt_uses_default_for_general(tmp_path: Path) -> None:
    template = load_report_prompt(MeetingType.general, AppConfig(prompts_dir=tmp_path))

    assert template.name == "general"
    assert not template.is_user_override
    assert "{{transcript}}" in template.text


def test_every_meeting_type_has_default_report_prompt() -> None:
    missing = [
        meeting_type.value
        for meeting_type in MeetingType
        if not (DEFAULT_PROMPTS_DIR / f"{meeting_type.value}.md").exists()
    ]

    assert missing == []


def test_enrichment_prompts_list_every_meeting_type() -> None:
    enrich_paths = [
        DEFAULT_PROMPTS_DIR / "enrich.md",
        DEFAULT_PROMPTS_DIR / "models" / "deepseek_fast" / "enrich.md",
        DEFAULT_PROMPTS_DIR / "models" / "gemini_fast" / "enrich.md",
        DEFAULT_PROMPTS_DIR / "models" / "sonnet_4_6" / "enrich.md",
    ]
    missing = []
    for path in enrich_paths:
        text = path.read_text(encoding="utf-8")
        missing.extend(
            f"{path}:{meeting_type.value}"
            for meeting_type in MeetingType
            if meeting_type.value not in text
        )

    assert missing == []


def test_load_report_prompt_uses_user_override(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "general.md").write_text("Custom prompt: {{transcript}}", encoding="utf-8")

    template = load_report_prompt(MeetingType.general, AppConfig(prompts_dir=prompts_dir))

    assert template.is_user_override
    assert template.text == "Custom prompt: {{transcript}}"


def test_load_system_prompt_can_be_overridden(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "system.md").write_text("System override", encoding="utf-8")

    template = load_system_prompt(AppConfig(prompts_dir=prompts_dir))

    assert template.is_user_override
    assert template.text == "System override"


def test_load_prompt_uses_model_specific_default(tmp_path: Path) -> None:
    template = load_report_prompt(MeetingType.general, AppConfig(prompts_dir=tmp_path), profile="sonnet_4_6")

    assert template.name == "general"
    assert template.profile == "sonnet_4_6"
    assert not template.is_user_override
    assert "RISEN + CREA" in template.text


def test_priority_meeting_types_have_model_specific_prompts(tmp_path: Path) -> None:
    meeting_types = [
        MeetingType.customer_success,
        MeetingType.client_update,
        MeetingType.daily,
        MeetingType.retro,
    ]
    profiles = ["deepseek_fast", "gemini_fast", "sonnet_4_6"]
    missing = []
    for profile in profiles:
        for meeting_type in meeting_types:
            template = load_report_prompt(meeting_type, AppConfig(prompts_dir=tmp_path), profile=profile)
            if template.profile != profile:
                missing.append(f"{profile}/{meeting_type.value}")

    assert missing == []


def test_load_prompt_uses_model_specific_user_override_first(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    model_dir = prompts_dir / "models" / "deepseek_fast"
    model_dir.mkdir(parents=True)
    (prompts_dir / "general.md").write_text("Global override", encoding="utf-8")
    (model_dir / "general.md").write_text("Model override {{model_profile}}", encoding="utf-8")

    template = load_prompt_template("general", AppConfig(prompts_dir=prompts_dir), profile="deepseek_fast")

    assert template.is_user_override
    assert template.profile == "deepseek_fast"
    assert template.text == "Model override {{model_profile}}"


def test_load_prompt_falls_back_to_global_user_override(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "general.md").write_text("Global override", encoding="utf-8")

    template = load_prompt_template("general", AppConfig(prompts_dir=prompts_dir), profile="missing_profile")

    assert template.is_user_override
    assert template.profile is None
    assert template.text == "Global override"


def test_render_report_prompt_replaces_placeholders(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "general.md").write_text(
        "{{title}}|{{meeting_type}}|{{project}}|{{language}}|{{attendees}}|{{sections}}|{{transcript}}",
        encoding="utf-8",
    )
    template = load_report_prompt(MeetingType.general, AppConfig(prompts_dir=prompts_dir))

    rendered = render_report_prompt(
        template=template,
        options=ProcessOptions(
            audio_path=Path("audio.wav"),
            title="Weekly",
            project="manola",
            attendees=["Ana", "Luis"],
        ),
        transcript="Hello",
        sections=["Summary"],
    )

    assert rendered == "Weekly|general|manola|auto|Ana, Luis|- Summary|Hello"


def test_render_report_prompt_replaces_model_placeholders(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "general.md").write_text("{{model_profile}}|{{model_name}}", encoding="utf-8")
    template = load_report_prompt(MeetingType.general, AppConfig(prompts_dir=prompts_dir))

    rendered = render_report_prompt(
        template=template,
        options=ProcessOptions(audio_path=Path("audio.wav")),
        transcript="Hello",
        sections=["Summary"],
        model_profile="deepseek_fast",
        model_name="deepseek-v4-flash",
    )

    assert rendered == "deepseek_fast|deepseek-v4-flash"

