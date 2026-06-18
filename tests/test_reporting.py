from pathlib import Path

from manola.config import AppConfig, LlmProfile
from manola.models import MeetingType, ProcessOptions
from manola.reporting import REPORT_SECTIONS, generate_metadata_suggestions, generate_report


def test_every_specialized_meeting_type_has_report_sections() -> None:
    missing = [
        meeting_type.value
        for meeting_type in MeetingType
        if meeting_type is not MeetingType.general and meeting_type not in REPORT_SECTIONS
    ]

    assert missing == []


def test_generate_report_uses_custom_prompts(monkeypatch, tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "system.md").write_text("Custom system", encoding="utf-8")
    (prompts_dir / "general.md").write_text("Custom user {{title}} {{transcript}}", encoding="utf-8")
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Report body"}}]}

    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("manola.reporting.httpx.post", fake_post)

    report = generate_report(
        options=ProcessOptions(audio_path=Path("audio.wav"), title="Planning"),
        transcript="Transcript text",
        config=AppConfig(
            prompts_dir=prompts_dir,
            llm_profiles={
                "deepseek_fast": LlmProfile(
                    base_url="https://example.test",
                    model="model",
                    api_key_env="OPENROUTER_API_KEY",
                    temperature=0.42,
                )
            },
        ),
        created_at=__import__("datetime").datetime(2026, 5, 11),
    )

    messages = captured["json"]["messages"]
    assert messages[0]["content"] == "Custom system"
    assert messages[1]["content"] == "Custom user Planning Transcript text"
    assert captured["json"]["temperature"] == 0.42
    assert "Prompt source:" in report
    assert "Prompt hash:" in report
    assert "Report body" in report


def test_generate_report_uses_profile_specific_prompt(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Report body"}}]}

    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("manola.reporting.httpx.post", fake_post)

    generate_report(
        options=ProcessOptions(audio_path=Path("audio.wav"), title="Planning", llm_profile="deepseek_fast"),
        transcript="Transcript text",
        config=AppConfig(prompts_dir=tmp_path),
        created_at=__import__("datetime").datetime(2026, 5, 11),
    )

    messages = captured["json"]["messages"]
    assert "DeepSeek V4 Flash" in messages[0]["content"]
    assert "RTF prompt" in messages[1]["content"]
    assert "LLM profile: deepseek_fast" in messages[1]["content"]
    assert "LLM model: deepseek/deepseek-v4-flash" in messages[1]["content"]


def test_generate_metadata_suggestions_parses_json(monkeypatch, tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "system.md").write_text("Custom system", encoding="utf-8")
    (prompts_dir / "enrich.md").write_text("Enrich {{title}} {{transcript}}", encoding="utf-8")
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"suggested_title":"Planning","suggested_meeting_type":"general","suggested_attendees":["Ana"],"summary":"Discussed planning."}'
                        }
                    }
                ]
            }

    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("manola.reporting.httpx.post", fake_post)

    suggestions = generate_metadata_suggestions(
        options=ProcessOptions(audio_path=Path("audio.wav"), title="Call"),
        transcript="Transcript text",
        config=AppConfig(
            prompts_dir=prompts_dir,
            llm_profiles={
                "deepseek_fast": LlmProfile(
                    base_url="https://example.test",
                    model="model",
                    api_key_env="OPENROUTER_API_KEY",
                    enrichment_temperature=0.05,
                )
            },
        ),
    )

    messages = captured["json"]["messages"]
    assert messages[0]["content"] == "Custom system"
    assert messages[1]["content"] == "Enrich Call Transcript text"
    assert captured["json"]["temperature"] == 0.05
    assert suggestions.suggested_title == "Planning"
    assert suggestions.suggested_attendees == ["Ana"]
