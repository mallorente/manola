from pathlib import Path

from typer.testing import CliRunner

from nanola.audio_recording import AudioDeviceReport, AudioTestResult
from nanola.cli import app
from nanola.config import AppConfig


runner = CliRunner()


def test_devices_lists_inputs_outputs_and_usage(monkeypatch) -> None:
    monkeypatch.setattr(
        "nanola.cli.inspect_audio_devices",
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
    assert "uv run nanola meet --mic-index 1 --speaker-index 3" in result.output
    assert "uv run nanola meet --mic" in result.output


def test_meet_runs_default_record_transcribe_report_workflow(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"
    transcript_path = meeting_dir / "transcript.md"
    report_path = meeting_dir / "report.md"

    class FakeRecording:
        path = meeting_dir / "audio" / "recorded.wav"
        duration_seconds = 60.0
        rms = 0.1
        sample_rate = 48000
        silent = False
        component_rms = {"mic": 0.1, "system": 0.2}

    monkeypatch.setattr(
        "nanola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr("nanola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))

    def fake_create_recorded_meeting(*args, **kwargs):
        assert kwargs["source"] == "meeting"
        assert kwargs["duration_seconds"] == 60
        assert kwargs["mic_index"] is None
        assert kwargs["speaker_index"] is None
        return meeting_dir, FakeRecording()

    monkeypatch.setattr("nanola.cli.create_recorded_meeting", fake_create_recorded_meeting)
    monkeypatch.setattr("nanola.cli.transcribe_meeting", lambda *args, **kwargs: transcript_path)
    monkeypatch.setattr("nanola.cli.summarize_meeting", lambda *args, **kwargs: report_path)

    result = runner.invoke(app, ["meet", "--duration", "60", "--language", "es"])

    assert result.exit_code == 0
    assert "Starting Nanola meeting workflow with defaults" in result.output
    assert "language: es" in result.output
    assert "transcript will be sent to remote LLM profile 'deepseek_fast'" in result.output
    assert "meeting folder:" in result.output
    assert "- recording:" not in result.output
    assert "- transcript:" not in result.output
    assert "- report file:" not in result.output
    assert f"Wrote transcript: {transcript_path}" in result.output
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
        "nanola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr("nanola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))

    def fake_create_recorded_meeting(*args, **kwargs):
        assert kwargs["duration_seconds"] is None
        assert kwargs["silence_timeout_seconds"] == 30
        assert kwargs["stop_key"] == "q"
        return meeting_dir, FakeRecording()

    monkeypatch.setattr("nanola.cli.create_recorded_meeting", fake_create_recorded_meeting)
    monkeypatch.setattr("nanola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")
    monkeypatch.setattr("nanola.cli.summarize_meeting", lambda *args, **kwargs: meeting_dir / "report.md")

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
        "nanola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A", "Mic B"],
            speakers=["Speaker A", "Speaker B", "Speaker C"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr("nanola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))

    def fake_create_recorded_meeting(*args, **kwargs):
        assert kwargs["mic_index"] == 2
        assert kwargs["speaker_index"] == 3
        return meeting_dir, FakeRecording()

    monkeypatch.setattr("nanola.cli.create_recorded_meeting", fake_create_recorded_meeting)
    monkeypatch.setattr("nanola.cli.transcribe_meeting", lambda *args, **kwargs: meeting_dir / "transcript.md")
    monkeypatch.setattr("nanola.cli.summarize_meeting", lambda *args, **kwargs: meeting_dir / "report.md")

    result = runner.invoke(app, ["meet", "--mic-index", "2", "--speaker-index", "3"])

    assert result.exit_code == 0
    assert "microphone: #2" in result.output
    assert "speaker/system audio: #3" in result.output


def test_transcribe_passes_overwrite_flags(monkeypatch, tmp_path: Path) -> None:
    meeting_dir = tmp_path / "meetings" / "2026-05-08__general__recording"
    transcript_path = meeting_dir / "transcript.md"
    captured = {}

    monkeypatch.setattr("nanola.cli.load_config", lambda: AppConfig(workspace_dir=tmp_path / "meetings"))
    monkeypatch.setattr("nanola.cli.resolve_meeting", lambda meeting, config: meeting_dir)

    def fake_transcribe_meeting(*args, **kwargs):
        captured.update(kwargs)
        return transcript_path

    monkeypatch.setattr("nanola.cli.transcribe_meeting", fake_transcribe_meeting)

    result = runner.invoke(app, ["transcribe", "meeting-id", "--force", "--no-skip-existing", "--no-export"])

    assert result.exit_code == 0
    assert captured["force"] is True
    assert captured["skip_existing"] is False


def test_audio_setup_runs_guided_checks(monkeypatch, tmp_path: Path) -> None:
    test_calls = []
    meeting_calls = []

    monkeypatch.setattr(
        "nanola.cli.inspect_audio_devices",
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

    monkeypatch.setattr("nanola.cli.record_audio_test", fake_record_audio_test)
    monkeypatch.setattr("nanola.cli.record_wav", fake_record_wav)

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
    assert "Recommended command: uv run nanola meet --mic-index 2 --speaker-index 3" in result.output


def test_audio_setup_uses_default_devices_without_prompting(monkeypatch, tmp_path: Path) -> None:
    test_calls = []
    meeting_calls = []

    monkeypatch.setattr(
        "nanola.cli.inspect_audio_devices",
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

    monkeypatch.setattr("nanola.cli.record_audio_test", fake_record_audio_test)
    monkeypatch.setattr("nanola.cli.record_wav", fake_record_wav)

    result = runner.invoke(app, ["audio", "setup", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert test_calls[0]["mic_index"] == 2
    assert test_calls[1]["speaker_index"] == 3
    assert meeting_calls[0]["mic_index"] == 2
    assert meeting_calls[0]["speaker_index"] == 3
    assert "Recommended command: uv run nanola meet --mic-index 2 --speaker-index 3" in result.output


def test_audio_setup_warns_when_meeting_system_audio_is_silent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "nanola.cli.inspect_audio_devices",
        lambda: AudioDeviceReport(
            default_microphone="Mic A",
            default_speaker="Speaker A",
            microphones=["Mic A"],
            speakers=["Speaker A"],
            loopbacks=["Speaker A Loopback"],
        ),
    )
    monkeypatch.setattr(
        "nanola.cli.record_audio_test",
        lambda **kwargs: AudioTestResult(
            path=tmp_path / f"{kwargs['source']}.wav",
            duration_seconds=5.0,
            rms=0.1,
            sample_rate=48000,
            silent=False,
        ),
    )
    monkeypatch.setattr(
        "nanola.cli.record_wav",
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
