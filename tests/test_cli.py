from pathlib import Path

from typer.testing import CliRunner

from manola.audio_recording import AudioDeviceReport, AudioTestResult
from manola.cli import _console_safe_text, app
from manola.config import AppConfig


runner = CliRunner()


def test_console_safe_text_replaces_unencodable_characters() -> None:
    assert _console_safe_text("hola 說", "cp1252") == "hola ?"


def test_devices_lists_inputs_outputs_and_usage(monkeypatch) -> None:
    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A", "Mic B"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )

    result = runner.invoke(app, ["devices"])

    assert result.exit_code == 0
    assert "microphones (--mic): 2" in result.output
    assert "1. Mic A [default]" in result.output
    assert "speakers (--speaker): 1" in result.output
    assert "uv run manola meet --mic-index 1 --speaker-index 3" in result.output
    assert "uv run manola meet --mic" in result.output


def test_prompts_list_shows_sources(monkeypatch, tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "general.md").write_text("Custom", encoding="utf-8")
    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(prompts_dir=prompts_dir))

    result = runner.invoke(app, ["prompts", "list"])

    assert result.exit_code == 0
    assert f"User prompts directory: {prompts_dir}" in result.output
    assert "general" in result.output
    assert "user" in result.output
    assert "system" in result.output


def test_prompts_show_prints_active_prompt(monkeypatch, tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "general.md").write_text("Custom prompt body", encoding="utf-8")
    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(prompts_dir=prompts_dir))

    result = runner.invoke(app, ["prompts", "show", "general"])

    assert result.exit_code == 0
    assert "Origin: user override" in result.output
    assert "Custom prompt body" in result.output


def test_prompts_show_can_resolve_llm_profile_prompt(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(prompts_dir=tmp_path))

    result = runner.invoke(app, ["prompts", "show", "general", "--llm-profile", "sonnet_4_6"])

    assert result.exit_code == 0
    assert "LLM profile: sonnet_4_6" in result.output
    assert "RISEN + CREA" in result.output


def test_meet_runs_default_record_transcribe_report_workflow(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"
    transcript_path = meeting_dir / "transcript.md"
    report_path = meeting_dir / "report.md"
    suggestions_path = meeting_dir / "metadata.suggestions.json"

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 60.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))

    def fake_create_recorded_meeting(*args, **kwargs):
        assert kwargs["source"] == "meeting"
        assert kwargs["duration_seconds"] == 60
        assert kwargs["mic_index"] is None
        assert kwargs["speaker_index"] is None
        assert kwargs["live_transcript"] is True
        return meeting_dir, FakeRecording()

    monkeypatch.setattr("manola.cli.create_recorded_meeting", fake_create_recorded_meeting)
    monkeypatch.setattr("manola.cli.transcribe_meeting", lambda *args, **kwargs: transcript_path)
    monkeypatch.setattr("manola.cli.enrich_meeting", lambda *args, **kwargs: suggestions_path)
    monkeypatch.setattr("manola.cli.summarize_meeting", lambda *args, **kwargs: report_path)

    result = runner.invoke(app, ["meet", "--duration", "60", "--language", "es"])

    assert result.exit_code == 0
    assert "Starting Manola meeting workflow with defaults" in result.output
    assert "language: es" in result.output
    assert "live transcript: enabled" in result.output
    assert "transcript will be sent to remote LLM profile 'deepseek_fast'" in result.output
    assert "meeting folder:" in result.output
    assert "- recording:" not in result.output
    assert "- transcript:" not in result.output
    assert "- report file:" not in result.output
    assert f"Wrote transcript: {transcript_path}" in result.output
    assert f"Wrote live transcript preview: {meeting_dir / 'live_transcript.md'}" in result.output
    assert f"Wrote suggestions: {suggestions_path}" in result.output
    assert f"Wrote report: {report_path}" in result.output


def test_meet_defaults_to_open_ended_recording(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 31.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))

    def fake_create_recorded_meeting(*args, **kwargs):
        assert kwargs["duration_seconds"] is None
        assert kwargs["silence_timeout_seconds"] == 30
        assert kwargs["stop_key"] == "q"
        assert kwargs["live_transcript"] is True
        return meeting_dir, FakeRecording()

    monkeypatch.setattr("manola.cli.create_recorded_meeting", fake_create_recorded_meeting)
    monkeypatch.setattr("manola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")
    monkeypatch.setattr("manola.cli.enrich_meeting", lambda *args, **kwargs: meeting_dir / "metadata.suggestions.json")
    monkeypatch.setattr("manola.cli.summarize_meeting", lambda *args, **kwargs: meeting_dir / "report.md")

    result = runner.invoke(app, ["meet"])

    assert result.exit_code == 0
    assert "press 'q' or wait for 30s" in result.output


def test_meet_accepts_device_indices(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 10.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A", "Mic B"],
            speakers=["Speaker A", "Speaker B", "Speaker C"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))

    def fake_create_recorded_meeting(*args, **kwargs):
        assert kwargs["mic_index"] == 2
        assert kwargs["speaker_index"] == 3
        assert kwargs["live_transcript"] is True
        return meeting_dir, FakeRecording()

    monkeypatch.setattr("manola.cli.create_recorded_meeting", fake_create_recorded_meeting)
    monkeypatch.setattr("manola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")
    monkeypatch.setattr("manola.cli.enrich_meeting", lambda *args, **kwargs: meeting_dir / "metadata.suggestions.json")
    monkeypatch.setattr("manola.cli.summarize_meeting", lambda *args, **kwargs: meeting_dir / "report.md")

    result = runner.invoke(app, ["meet", "--mic-index", "2", "--speaker-index", "3"])

    assert result.exit_code == 0
    assert "microphone: #2" in result.output
    assert "speaker/system audio: #3" in result.output


def test_meet_uses_configured_defaults_when_flags_are_omitted(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"
    captured = {}

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 10.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A", "Mic B", "Mic C", "Mic D", "Mic E"],
            speakers=["Speaker A", "Speaker B", "Speaker C"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr(
        "manola.cli.load_config",
        lambda: AppConfig(
            workspace_dir=tmp_path / "meetings",
            default_language="es",
            default_llm_profile="openai_fallback",
            default_mic_index=5,
            default_speaker_index=3,
        ),
    )

    def fake_create_recorded_meeting(options, *args, **kwargs):
        captured["language"] = options.language
        captured["llm_profile"] = options.llm_profile
        captured.update(kwargs)
        return meeting_dir, FakeRecording()

    monkeypatch.setattr("manola.cli.create_recorded_meeting", fake_create_recorded_meeting)
    monkeypatch.setattr("manola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")
    monkeypatch.setattr("manola.cli.enrich_meeting", lambda *args, **kwargs: meeting_dir / "metadata.suggestions.json")
    monkeypatch.setattr("manola.cli.summarize_meeting", lambda *args, **kwargs: meeting_dir / "report.md")

    result = runner.invoke(app, ["meet", "--duration", "10"])

    assert result.exit_code == 0
    assert captured["mic_index"] == 5
    assert captured["speaker_index"] == 3
    assert captured["language"].value == "es"
    assert captured["llm_profile"] == "openai_fallback"
    assert "microphone: #5" in result.output
    assert "speaker/system audio: #3" in result.output
    assert "language: es" in result.output
    assert "report: enabled (openai_fallback)" in result.output


def test_meet_auto_speaker_ignores_configured_speaker_default(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"
    captured = {}

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 10.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A", "Speaker B", "Speaker C"],
            loopbacks=["Speaker A Loopback", "Speaker C Loopback"],
        ),
    )
    monkeypatch.setattr(
        "manola.cli.load_config",
        lambda: AppConfig(workspace_dir=tmp_path / "meetings", default_speaker_index=3),
    )

    def fake_create_recorded_meeting(*args, **kwargs):
        captured.update(kwargs)
        return meeting_dir, FakeRecording()

    monkeypatch.setattr("manola.cli.create_recorded_meeting", fake_create_recorded_meeting)
    monkeypatch.setattr("manola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")
    monkeypatch.setattr("manola.cli.enrich_meeting", lambda *args, **kwargs: meeting_dir / "metadata.suggestions.json")
    monkeypatch.setattr("manola.cli.summarize_meeting", lambda *args, **kwargs: meeting_dir / "report.md")

    result = runner.invoke(app, ["meet", "--duration", "10", "--auto-speaker"])

    assert result.exit_code == 0
    assert captured["speaker_index"] is None
    assert "speaker/system audio: auto" in result.output


def test_meet_uses_configured_llm_default_when_flag_is_omitted(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 10.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr(
        "manola.cli.load_config",
        lambda: AppConfig(
            workspace_dir=tmp_path / "meetings",
            default_generate_llm_report=False,
        ),
    )
    monkeypatch.setattr("manola.cli.create_recorded_meeting", lambda *args, **kwargs: (meeting_dir, FakeRecording()))
    monkeypatch.setattr("manola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")

    def fail_llm_step(*args, **kwargs):
        raise AssertionError("LLM step should follow config default and stay disabled")

    monkeypatch.setattr("manola.cli.enrich_meeting", fail_llm_step)
    monkeypatch.setattr("manola.cli.summarize_meeting", fail_llm_step)

    result = runner.invoke(app, ["meet", "--duration", "10"])

    assert result.exit_code == 0
    assert "report: disabled" in result.output
    assert "report privacy: disabled" in result.output


def test_meet_llm_flag_overrides_configured_default(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"
    report_path = meeting_dir / "report.md"

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 10.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr(
        "manola.cli.load_config",
        lambda: AppConfig(
            workspace_dir=tmp_path / "meetings",
            default_generate_llm_report=False,
        ),
    )
    monkeypatch.setattr("manola.cli.create_recorded_meeting", lambda *args, **kwargs: (meeting_dir, FakeRecording()))
    monkeypatch.setattr("manola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")
    monkeypatch.setattr("manola.cli.enrich_meeting", lambda *args, **kwargs: meeting_dir / "metadata.suggestions.json")
    monkeypatch.setattr("manola.cli.summarize_meeting", lambda *args, **kwargs: report_path)

    result = runner.invoke(app, ["meet", "--duration", "10", "--llm"])

    assert result.exit_code == 0
    assert f"Wrote report: {report_path}" in result.output


def test_meet_can_disable_enrichment(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 10.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))
    monkeypatch.setattr("manola.cli.create_recorded_meeting", lambda *args, **kwargs: (meeting_dir, FakeRecording()))
    monkeypatch.setattr("manola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")
    monkeypatch.setattr("manola.cli.summarize_meeting", lambda *args, **kwargs: meeting_dir / "report.md")

    def fail_enrich(*args, **kwargs):
        raise AssertionError("enrichment should be disabled")

    monkeypatch.setattr("manola.cli.enrich_meeting", fail_enrich)

    result = runner.invoke(app, ["meet", "--duration", "10", "--no-enrich"])

    assert result.exit_code == 0
    assert "enrichment: disabled" in result.output
    assert "Wrote suggestions:" not in result.output


def test_meet_can_disable_default_live_transcript(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 10.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))

    def fake_create_recorded_meeting(*args, **kwargs):
        assert kwargs["live_transcript"] is False
        assert kwargs["live_transcript_preview"] is None
        return meeting_dir, FakeRecording()

    monkeypatch.setattr("manola.cli.create_recorded_meeting", fake_create_recorded_meeting)
    monkeypatch.setattr("manola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")
    monkeypatch.setattr("manola.cli.enrich_meeting", lambda *args, **kwargs: meeting_dir / "metadata.suggestions.json")
    monkeypatch.setattr("manola.cli.summarize_meeting", lambda *args, **kwargs: meeting_dir / "report.md")

    result = runner.invoke(app, ["meet", "--duration", "10", "--no-live-transcript"])

    assert result.exit_code == 0
    assert "live transcript: disabled" in result.output
    assert "Wrote live transcript preview:" not in result.output


def test_transcribe_passes_overwrite_flags(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"
    transcript_path = meeting_dir / "transcript.md"
    captured = {}

    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))
    monkeypatch.setattr("manola.cli.resolve_meeting", lambda meeting, config: meeting_dir)

    def fake_transcribe_meeting(*args, **kwargs):
        captured.update(kwargs)
        return transcript_path

    monkeypatch.setattr("manola.cli.transcribe_meeting", fake_transcribe_meeting)

    result = runner.invoke(app, ["transcribe", "meeting-id", "--force", "--no-skip-existing", "--no-export"])

    assert result.exit_code == 0
    assert captured["force"] is True
    assert captured["skip_existing"] is False


def test_enrich_resolves_meeting_and_writes_suggestions(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-11__general__planning"
    suggestions_path = meeting_dir / "metadata.suggestions.json"
    captured = {}

    monkeypatch.setattr("manola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))
    monkeypatch.setattr("manola.cli.resolve_meeting", lambda meeting, config: meeting_dir)

    def fake_enrich_meeting(*args, **kwargs):
        captured.update(kwargs)
        return suggestions_path

    monkeypatch.setattr("manola.cli.enrich_meeting", fake_enrich_meeting)

    result = runner.invoke(app, ["enrich", "meeting-id", "--force"])

    assert result.exit_code == 0
    assert captured["force"] is True
    assert f"Wrote suggestions: {suggestions_path}" in result.output


def test_audio_setup_runs_guided_checks(monkeypatch, tmp_path: Path) -> None:
    test_calls = []
    meeting_calls = []

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A", "Mic B"],
            speakers=["Speaker A", "Speaker B", "Speaker C"],
            loopbacks=["Speaker A Loopback"],
        ),
    )

    def fake_record_audio_test(**kwargs):
        test_calls.append(kwargs)
        return AudioTestResult(
            path=tmp_path / f"{kwargs['source']}.wav",
            duration_seconds=5.0,
            rms=0.1,
            sample_rate=48000,
            silent=False,
        )

    def fake_record_wav(**kwargs):
        meeting_calls.append(kwargs)
        return AudioTestResult(
            path=kwargs["target"],
            duration_seconds=5.0,
            rms=0.1,
            sample_rate=48000,
            silent=False,
            component_rms={"mic": 0.1, "system": 0.2},
        )

    monkeypatch.setattr("manola.cli.record_audio_test", fake_record_audio_test)
    monkeypatch.setattr("manola.cli.record_wav", fake_record_wav)

    result = runner.invoke(
        app,
        [
            "audio",
            "setup",
            "--duration",
            "5",
            "--output-dir",
            str(tmp_path),
            "--mic-index",
            "2",
            "--speaker-index",
            "3",
        ],
    )

    assert result.exit_code == 0
    assert [call["source"] for call in test_calls] == ["mic", "system"]
    assert test_calls[0]["mic_index"] == 2
    assert test_calls[1]["speaker_index"] == 3
    assert meeting_calls[0]["source"] == "meeting"
    assert meeting_calls[0]["mic_index"] == 2
    assert meeting_calls[0]["speaker_index"] == 3
    assert meeting_calls[0]["allow_partial"] is True
    assert "Audio setup passed." in result.output
    assert "Recommended command: uv run manola meet --mic-index 2 --speaker-index 3" in result.output


def test_audio_setup_can_save_selected_devices(monkeypatch, tmp_path: Path) -> None:
    saved = []

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A", "Mic B"],
            speakers=["Speaker A", "Speaker B", "Speaker C"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr(
        "manola.cli.record_audio_test",
        lambda **kwargs: AudioTestResult(
            path=tmp_path / f"{kwargs['source']}.wav",
            duration_seconds=5.0,
            rms=0.1,
            sample_rate=48000,
            silent=False,
        ),
    )
    monkeypatch.setattr(
        "manola.cli.record_wav",
        lambda **kwargs: AudioTestResult(
            path=kwargs["target"],
            duration_seconds=5.0,
            rms=0.1,
            sample_rate=48000,
            silent=False,
            component_rms={"mic": 0.1, "system": 0.2},
        ),
    )
    monkeypatch.setattr("manola.cli.update_config_value", lambda name, value: saved.append((name, value)))

    result = runner.invoke(
        app,
        [
            "audio",
            "setup",
            "--output-dir",
            str(tmp_path),
            "--mic-index",
            "2",
            "--speaker-index",
            "3",
            "--save",
        ],
    )

    assert result.exit_code == 0
    assert saved == [("default_mic_index", 2), ("default_speaker_index", 3)]
    assert "Saved defaults to" in result.output


def test_audio_setup_uses_default_devices_without_prompting(monkeypatch, tmp_path: Path) -> None:
    test_calls = []
    meeting_calls = []

    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic B",
            default_speaker="Speaker C",
            microphones=["Mic A", "Mic B"],
            speakers=["Speaker A", "Speaker B", "Speaker C"],
            loopbacks=["Speaker C Loopback"],
        ),
    )

    def fake_record_audio_test(**kwargs):
        test_calls.append(kwargs)
        return AudioTestResult(
            path=tmp_path / f"{kwargs['source']}.wav",
            duration_seconds=5.0,
            rms=0.1,
            sample_rate=48000,
            silent=False,
        )

    def fake_record_wav(**kwargs):
        meeting_calls.append(kwargs)
        return AudioTestResult(
            path=kwargs["target"],
            duration_seconds=5.0,
            rms=0.1,
            sample_rate=48000,
            silent=False,
            component_rms={"mic": 0.1, "system": 0.2},
        )

    monkeypatch.setattr("manola.cli.record_audio_test", fake_record_audio_test)
    monkeypatch.setattr("manola.cli.record_wav", fake_record_wav)

    result = runner.invoke(app, ["audio", "setup", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert test_calls[0]["mic_index"] == 2
    assert test_calls[1]["speaker_index"] == 3
    assert meeting_calls[0]["mic_index"] == 2
    assert meeting_calls[0]["speaker_index"] == 3
    assert "Recommended command: uv run manola meet --mic-index 2 --speaker-index 3" in result.output


def test_audio_setup_warns_when_meeting_system_audio_is_silent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "manola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr(
        "manola.cli.record_audio_test",
        lambda **kwargs: AudioTestResult(
            path=tmp_path / f"{kwargs['source']}.wav",
            duration_seconds=5.0,
            rms=0.1,
            sample_rate=48000,
            silent=False,
        ),
    )
    monkeypatch.setattr(
        "manola.cli.record_wav",
        lambda **kwargs: AudioTestResult(
            path=kwargs["target"],
            duration_seconds=5.0,
            rms=0.1,
            sample_rate=48000,
            silent=False,
            component_rms={"mic": 0.1, "system": 0.0},
        ),
    )

    result = runner.invoke(app, ["audio", "setup", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "system RMS: 0.000000" in result.output
    assert "meeting capture had silent system audio" in result.output


def test_audio_enhance_test_standalone_without_transcription(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "recording.m4a"
    source.write_text("audio", encoding="utf-8")
    copied = tmp_path / "out" / "audio" / "original.m4a"
    normalized = tmp_path / "out" / "audio" / "normalized.wav"
    enhanced = tmp_path / "out" / "audio" / "enhanced.wav"

    def fake_copy_original(source_path: Path, destination_dir: Path) -> Path:
        destination_dir.mkdir(parents=True, exist_ok=True)
        copied.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        return copied

    def fake_normalize(source_path: Path, target: Path) -> Path:
        target.write_text("normalized", encoding="utf-8")
        return target

    def fake_enhance(source_path: Path, target: Path, *, mode: str) -> Path:
        assert source_path == normalized
        assert mode == "denoise"
        target.write_text("enhanced", encoding="utf-8")
        return target

    monkeypatch.setattr("manola.cli.copy_original", fake_copy_original)
    monkeypatch.setattr("manola.cli.normalize_audio", fake_normalize)
    monkeypatch.setattr("manola.cli.enhance_voice", fake_enhance)

    result = runner.invoke(
        app,
        [
            "audio",
            "enhance-test",
            str(source),
            "--output-dir",
            str(tmp_path / "out"),
            "--mode",
            "denoise",
            "--no-transcribe",
        ],
    )

    assert result.exit_code == 0
    assert enhanced.read_text(encoding="utf-8") == "enhanced"
    assert f"Wrote enhanced audio: {enhanced}" in result.output
