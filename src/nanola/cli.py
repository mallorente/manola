from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Annotated

import typer

from .config import CONFIG_PATH, SECRETS_PATH, load_config, render_config, write_default_config, write_secrets_template
from .doctor import collect_doctor_checks
from .errors import NanolaError
from .audio_recording import inspect_audio_devices, record_audio_test, record_wav
from .exporting import export_meeting
from .models_store import FASTER_WHISPER_REPOS, download_faster_whisper_model, list_downloaded_models
from .models import Language, MeetingType, ProcessOptions, SharePolicy, TranscriptionBackend
from .naming import meeting_folder_name, proposed_archive_parent
from .pipeline import create_recorded_meeting, import_recording, iter_meetings, process_recording, resolve_meeting, summarize_meeting, transcribe_meeting


app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Local-first meeting recorder, transcriber, and report generator.\n\n"
        "Start here:\n"
        "  uv run nanola meet --language es\n"
        "  uv run nanola devices\n"
        "  uv run nanola process recording.m4a --language es"
    ),
)
audio_app = typer.Typer(no_args_is_help=True, help="Audio device diagnostics and recording tests.")
config_app = typer.Typer(no_args_is_help=True, help="Manage Nanola configuration files.")
models_app = typer.Typer(no_args_is_help=True, help="Manage local faster-whisper models.")
app.add_typer(audio_app, name="audio")
app.add_typer(config_app, name="config")
app.add_typer(models_app, name="models")


def _attendees(values: list[str] | None) -> list[str]:
    attendees: list[str] = []
    for value in values or []:
        attendees.extend(part.strip() for part in value.split(",") if part.strip())
    return attendees


def _fail(message: str) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(1)


def _status(message: str) -> None:
    typer.echo(f"... {message}")


def _print_audio_devices(report) -> None:
    typer.echo(f"default microphone: {report.default_microphone or 'missing'}")
    typer.echo(f"default speaker: {report.default_speaker or 'missing'}")
    typer.echo("")
    typer.echo(f"microphones (--mic): {len(report.microphones)}")
    for index, name in enumerate(report.microphones, start=1):
        marker = " [default]" if name == report.default_microphone else ""
        typer.echo(f"  {index}. {name}{marker}")
    typer.echo(f"speakers (--speaker): {len(report.speakers)}")
    for index, name in enumerate(report.speakers, start=1):
        marker = " [default]" if name == report.default_speaker else ""
        typer.echo(f"  {index}. {name}{marker}")
    typer.echo(f"loopback inputs (system-audio capture): {len(report.loopbacks)}")
    for index, name in enumerate(report.loopbacks, start=1):
        typer.echo(f"  {index}. {name}")
    typer.echo(f"meeting capture: {'ok' if report.has_meeting_capture else 'missing'}")
    typer.echo("")
    typer.echo('Use devices by index: uv run nanola meet --mic-index 1 --speaker-index 3')
    typer.echo('Or by name: uv run nanola meet --mic "<microphone>" --speaker "<speaker>"')


def _print_recording_result(source: str, result) -> None:
    typer.echo(f"Wrote recording: {result.path}")
    typer.echo(f"Duration: {result.duration_seconds:0.2f}s")
    typer.echo(f"RMS: {result.rms:0.6f}")
    if result.component_rms:
        for name, rms in result.component_rms.items():
            typer.echo(f"{name} RMS: {rms:0.6f}")
            if source == "meeting" and rms <= 0.0001:
                typer.echo(f"Warning: {name} audio appears silent in meeting capture.")
    if result.silent:
        typer.echo("Warning: recorded audio appears silent.")


def _default_device_index(devices: list[str], default_name: str | None) -> int | None:
    if default_name in devices:
        return devices.index(default_name) + 1
    return None


def _validate_device_index(kind: str, devices: list[str], index: int | None) -> int | None:
    if index is None:
        return None
    if index <= 0 or index > len(devices):
        raise NanolaError(f"Unknown {kind} index: {index}. Available {kind}s: 1-{len(devices)}")
    return index


def _select_device_index(kind: str, devices: list[str], default_name: str | None, provided_index: int | None, enabled: bool) -> int | None:
    if provided_index is not None:
        return _validate_device_index(kind, devices, provided_index)

    default_index = _default_device_index(devices, default_name)
    if not enabled:
        return default_index
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        typer.echo(f"Interactive selector unavailable; using default {kind}.")
        return default_index
    if not devices:
        return None
    if sys.platform != "win32":
        typer.echo(f"Interactive selector is currently Windows-only; using default {kind}.")
        return default_index
    return _windows_arrow_select(kind, devices, default_index)


def _windows_arrow_select(kind: str, devices: list[str], default_index: int | None) -> int:
    import msvcrt

    selected = (default_index or 1) - 1
    typer.echo("")
    typer.echo(f"Select {kind}. Use arrow keys and Enter.")
    for _device in devices:
        typer.echo("")

    while True:
        sys.stdout.write(f"\033[{len(devices)}A")
        for index, name in enumerate(devices):
            marker = ">" if index == selected else " "
            default_marker = " [default]" if default_index == index + 1 else ""
            sys.stdout.write(f"\033[2K{marker} {index + 1}. {name}{default_marker}\n")
        sys.stdout.flush()

        key = msvcrt.getwch()
        if key in ("\r", "\n"):
            return selected + 1
        if key in ("\x00", "\xe0"):
            key = msvcrt.getwch()
            if key == "H":
                selected = (selected - 1) % len(devices)
            elif key == "P":
                selected = (selected + 1) % len(devices)


def _print_setup_step(source: str, duration: int) -> None:
    instructions = {
        "mic": "Speak into the microphone while this runs.",
        "system": "Play audio from the meeting app, browser, or speakers while this runs.",
        "meeting": "Speak while system audio is playing so both sides are present.",
    }
    typer.echo("")
    typer.echo(f"Testing {source} capture for {duration}s.")
    typer.echo(instructions[source])


def _recommended_meet_command(mic_index: int | None, speaker_index: int | None) -> str:
    command = "uv run nanola meet"
    if mic_index is not None:
        command += f" --mic-index {mic_index}"
    if speaker_index is not None:
        command += f" --speaker-index {speaker_index}"
    return command


def _print_llm_privacy_notice(enabled: bool, profile: str | None) -> None:
    if not enabled:
        typer.echo("- report privacy: disabled; transcript will not be sent to a report LLM")
        return
    profile_text = f" profile '{profile}'" if profile else ""
    typer.echo(f"- report privacy: enabled; transcript will be sent to remote LLM{profile_text}")
    typer.echo("  Use --no-llm to keep report generation off.")


@app.command()
def process(
    audio_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    meeting_type: Annotated[MeetingType, typer.Option("--type")] = MeetingType.general,
    project: Annotated[str | None, typer.Option()] = None,
    language: Annotated[Language, typer.Option()] = Language.auto,
    title: Annotated[str | None, typer.Option()] = None,
    attendee: Annotated[list[str] | None, typer.Option("--attendee")] = None,
    share: Annotated[SharePolicy, typer.Option("--share")] = SharePolicy.private,
    backend: Annotated[TranscriptionBackend, typer.Option("--backend")] = TranscriptionBackend.local,
    llm_profile: Annotated[str, typer.Option("--llm-profile")] = "deepseek_fast",
    llm: Annotated[bool, typer.Option("--llm/--no-llm", help="Generate a report with the configured remote LLM.")] = True,
) -> None:
    """Process an existing recording into a transcript, report, and local archive."""
    config = load_config()
    options = ProcessOptions(
        audio_path=audio_path,
        meeting_type=meeting_type,
        project=project,
        language=language,
        title=title,
        attendees=_attendees(attendee),
        share_policy=share,
        transcription_backend=backend,
        llm_profile=llm_profile,
    )
    try:
        _status("Starting process workflow...")
        _print_llm_privacy_notice(llm, llm_profile)
        meeting_dir = process_recording(options, config, generate_llm_report=llm, status=_status)
        if share != SharePolicy.private:
            _status(f"Exporting with share policy {share.value}...")
            exported_dir = export_meeting(meeting_dir, config, share)
    except NanolaError as exc:
        _fail(str(exc))
    typer.echo(f"Created meeting: {meeting_dir}")
    if share != SharePolicy.private:
        typer.echo(f"Exported meeting: {exported_dir}")


@app.command("import")
def import_audio(
    audio_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    meeting_type: Annotated[MeetingType, typer.Option("--type")] = MeetingType.general,
    project: Annotated[str | None, typer.Option()] = None,
    language: Annotated[Language, typer.Option()] = Language.auto,
    title: Annotated[str | None, typer.Option()] = None,
    attendee: Annotated[list[str] | None, typer.Option("--attendee")] = None,
    share: Annotated[SharePolicy, typer.Option("--share")] = SharePolicy.private,
    backend: Annotated[TranscriptionBackend, typer.Option("--backend")] = TranscriptionBackend.local,
    llm_profile: Annotated[str, typer.Option("--llm-profile")] = "deepseek_fast",
) -> None:
    """Import and normalize audio without transcribing or summarizing."""
    config = load_config()
    options = ProcessOptions(
        audio_path=audio_path,
        meeting_type=meeting_type,
        project=project,
        language=language,
        title=title,
        attendees=_attendees(attendee),
        share_policy=share,
        transcription_backend=backend,
        llm_profile=llm_profile,
    )
    try:
        _status("Starting import workflow...")
        meeting_dir = import_recording(options, config, status=_status)
    except NanolaError as exc:
        _fail(str(exc))
    typer.echo(f"Imported meeting: {meeting_dir}")


@app.command()
def doctor() -> None:
    """Check local dependencies and Nanola configuration."""
    config = load_config()
    typer.echo(f"Config: {CONFIG_PATH}")
    typer.echo(f"Secrets: {SECRETS_PATH}")
    failed = False
    for check in collect_doctor_checks(config):
        typer.echo(f"{check.status:7} {check.name}: {check.detail}")
        failed = failed or check.status == "missing"
    if failed:
        raise typer.Exit(1)


@app.command("devices")
def devices() -> None:
    """List input and output audio devices."""
    try:
        report = inspect_audio_devices()
    except NanolaError as exc:
        _fail(str(exc))
    _print_audio_devices(report)


@config_app.command("init")
def config_init(
    workspace_dir: Annotated[Path | None, typer.Option("--workspace-dir")] = None,
    shared_dir: Annotated[Path | None, typer.Option("--shared-dir")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Create ~/.nanola/config.toml and a secrets template."""
    try:
        config_path = write_default_config(
            workspace_dir=workspace_dir,
            shared_dir=shared_dir,
            overwrite=force,
        )
        secrets_path = write_secrets_template(overwrite=force)
    except NanolaError as exc:
        _fail(str(exc))
    typer.echo(f"Wrote config: {config_path}")
    typer.echo(f"Wrote secrets template: {secrets_path}")


@config_app.command("show")
def config_show() -> None:
    """Print the effective Nanola configuration without secrets."""
    typer.echo(render_config(load_config()))


@models_app.command("download")
def models_download(
    model: Annotated[str, typer.Argument(help="Model alias or Hugging Face repo id.")] = "base",
    set_default: Annotated[bool, typer.Option("--set-default")] = True,
) -> None:
    """Download a faster-whisper model into the local Nanola model cache."""
    try:
        _status(f"Downloading model {model}...")
        target = download_faster_whisper_model(model, config=load_config(), set_default=set_default)
    except NanolaError as exc:
        _fail(str(exc))
    typer.echo(f"Downloaded model: {target}")
    if set_default:
        typer.echo("Updated config: local_whisper_model now points to this local folder.")


@models_app.command("list")
def models_list() -> None:
    """List downloaded local faster-whisper models."""
    config = load_config()
    models = list_downloaded_models(config)
    if not models:
        typer.echo("No downloaded models found.")
        typer.echo(f"Model directory: {config.models_dir}")
        typer.echo("Known aliases: " + ", ".join(sorted(FASTER_WHISPER_REPOS)))
        return
    for model in models:
        typer.echo(str(model))


@audio_app.command("doctor")
def audio_doctor() -> None:
    """Check audio-specific dependencies."""
    try:
        report = inspect_audio_devices()
    except NanolaError as exc:
        _fail(str(exc))
    _print_audio_devices(report)
    if not report.has_meeting_capture:
        raise typer.Exit(1)


@audio_app.command("devices")
def audio_devices() -> None:
    """List input and output audio devices."""
    try:
        report = inspect_audio_devices()
    except NanolaError as exc:
        _fail(str(exc))
    _print_audio_devices(report)


@audio_app.command("test")
def audio_test(
    source: Annotated[str, typer.Option("--source", help="Audio source to test: mic, system, or meeting.")] = "meeting",
    duration: Annotated[int, typer.Option("--duration", help="Test recording duration in seconds.")] = 30,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory for diagnostic WAV files.")] = Path(".nanola-audio-tests"),
    mic: Annotated[str | None, typer.Option("--mic", help="Microphone name or substring from `nanola devices`.")] = None,
    mic_index: Annotated[int | None, typer.Option("--mic-index", help="1-based microphone index from `nanola devices`.")] = None,
    speaker: Annotated[str | None, typer.Option("--speaker", help="Speaker/output name or substring from `nanola devices`.")] = None,
    speaker_index: Annotated[int | None, typer.Option("--speaker-index", help="1-based speaker/output index from `nanola devices`.")] = None,
) -> None:
    """Record a short WAV sample from mic, system, or meeting sources."""
    try:
        _status(f"Recording {source} audio for {duration}s...")
        result = record_audio_test(
            source=source,
            duration_seconds=duration,
            output_dir=output_dir,
            mic_name=mic,
            mic_index=mic_index,
            speaker_name=speaker,
            speaker_index=speaker_index,
        )
    except NanolaError as exc:
        _fail(str(exc))
    typer.echo(f"Wrote WAV: {result.path}")
    typer.echo(f"Duration: {result.duration_seconds:0.2f}s")
    typer.echo(f"RMS: {result.rms:0.6f}")
    typer.echo(f"Sample rate: {result.sample_rate}")
    if result.silent:
        typer.echo("Warning: recorded audio appears silent.")


@audio_app.command("setup")
def audio_setup(
    duration: Annotated[int, typer.Option("--duration", help="Duration in seconds for each setup recording.")] = 5,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory for setup WAV files.")] = Path(".nanola-audio-tests"),
    mic_index: Annotated[int | None, typer.Option("--mic-index", help="1-based microphone index from `nanola devices`.")] = None,
    speaker_index: Annotated[int | None, typer.Option("--speaker-index", help="1-based speaker/output index from `nanola devices`.")] = None,
    select: Annotated[bool, typer.Option("--select/--no-select", help="Use an interactive arrow-key selector for devices when available.")] = False,
) -> None:
    """Guided audio setup for microphone, system audio, and meeting capture."""
    try:
        report = inspect_audio_devices()
        typer.echo("Nanola audio setup")
        typer.echo("")
        _print_audio_devices(report)
        if not report.default_microphone:
            raise NanolaError("No default microphone found. Connect or enable a microphone and retry.")
        if not report.loopbacks:
            raise NanolaError("No system-audio loopback found. Meeting capture needs loopback audio.")

        selected_mic_index = _select_device_index("microphone", report.microphones, report.default_microphone, mic_index, select)
        selected_speaker_index = _select_device_index("speaker", report.speakers, report.default_speaker, speaker_index, select)

        selected_mic_label = f"#{selected_mic_index}" if selected_mic_index is not None else "system default"
        selected_speaker_label = f"#{selected_speaker_index}" if selected_speaker_index is not None else "system default"
        typer.echo("")
        typer.echo(f"Selected microphone: {selected_mic_label}")
        typer.echo(f"Selected speaker/system audio: {selected_speaker_label}")

        _print_setup_step("mic", duration)
        mic_result = record_audio_test(
            source="mic",
            duration_seconds=duration,
            output_dir=output_dir,
            mic_index=selected_mic_index,
        )
        _print_recording_result("mic", mic_result)

        _print_setup_step("system", duration)
        system_result = record_audio_test(
            source="system",
            duration_seconds=duration,
            output_dir=output_dir,
            speaker_index=selected_speaker_index,
        )
        _print_recording_result("system", system_result)

        _print_setup_step("meeting", duration)
        output_dir.mkdir(parents=True, exist_ok=True)
        meeting_result = record_wav(
            source="meeting",
            duration_seconds=duration,
            target=output_dir / f"audio-setup-meeting-{datetime.now():%Y%m%d-%H%M%S}.wav",
            mic_index=selected_mic_index,
            speaker_index=selected_speaker_index,
            allow_partial=True,
        )
        _print_recording_result("meeting", meeting_result)
    except NanolaError as exc:
        _fail(str(exc))

    typer.echo("")
    silent_components = meeting_result.component_rms or {}
    silent_meeting_components = [name for name, rms in silent_components.items() if rms <= 0.0001]
    if mic_result.silent or system_result.silent or meeting_result.silent or silent_meeting_components:
        typer.echo("Audio setup completed with warnings.")
        if mic_result.silent:
            typer.echo("- microphone capture was silent")
        if system_result.silent:
            typer.echo("- system audio capture was silent")
        if meeting_result.silent:
            typer.echo("- meeting capture was silent")
        for component in silent_meeting_components:
            typer.echo(f"- meeting capture had silent {component} audio")
    else:
        typer.echo("Audio setup passed.")

    typer.echo(f"Recommended command: {_recommended_meet_command(selected_mic_index, selected_speaker_index)}")


@app.command()
def export(
    meeting: Annotated[str, typer.Argument()],
    policy: Annotated[SharePolicy | None, typer.Option("--share")] = None,
) -> None:
    """Export a processed meeting to the configured shared folder."""
    config = load_config()
    try:
        _status(f"Resolving meeting {meeting}...")
        meeting_dir = resolve_meeting(meeting, config)
        _status(f"Exporting meeting with policy {(policy.value if policy else 'metadata default')}...")
        target = export_meeting(meeting_dir, config, policy)
    except NanolaError as exc:
        _fail(str(exc))
    typer.echo(f"Exported meeting: {target}")


@app.command()
def transcribe(
    meeting: Annotated[str, typer.Argument()],
    summarize_after: Annotated[bool, typer.Option("--summarize/--no-summarize")] = False,
    export_after: Annotated[bool, typer.Option("--export/--no-export")] = True,
    force: Annotated[bool, typer.Option("--force", help="Regenerate transcript/report even if they already exist.")] = False,
    skip_existing: Annotated[
        bool,
        typer.Option("--skip-existing/--no-skip-existing", help="Do not overwrite existing transcript/report unless --force is used."),
    ] = True,
) -> None:
    """Transcribe an imported meeting by id or path."""
    config = load_config()
    try:
        _status(f"Resolving meeting {meeting}...")
        meeting_dir = resolve_meeting(meeting, config)
        transcript_path = transcribe_meeting(meeting_dir, config, status=_status, force=force, skip_existing=skip_existing)
        if summarize_after:
            report_path = summarize_meeting(meeting_dir, config, status=_status, force=force, skip_existing=skip_existing)
        if export_after:
            _status("Exporting meeting...")
            target = export_meeting(meeting_dir, config)
    except NanolaError as exc:
        _fail(str(exc))
    typer.echo(f"Wrote transcript: {transcript_path}")
    if summarize_after:
        typer.echo(f"Wrote report: {report_path}")
    if export_after:
        typer.echo(f"Exported meeting: {target}")


@app.command()
def summarize(
    meeting: Annotated[str, typer.Argument()],
    export_report: Annotated[bool, typer.Option("--export/--no-export")] = True,
    force: Annotated[bool, typer.Option("--force", help="Regenerate report even if it already exists.")] = False,
    skip_existing: Annotated[
        bool,
        typer.Option("--skip-existing/--no-skip-existing", help="Do not overwrite an existing generated report unless --force is used."),
    ] = True,
) -> None:
    """Generate or replace report.md for an existing transcribed meeting."""
    config = load_config()
    try:
        _status(f"Resolving meeting {meeting}...")
        meeting_dir = resolve_meeting(meeting, config)
        _print_llm_privacy_notice(True, None)
        report_path = summarize_meeting(meeting_dir, config, status=_status, force=force, skip_existing=skip_existing)
        if export_report:
            _status("Exporting meeting...")
            target = export_meeting(meeting_dir, config)
    except NanolaError as exc:
        _fail(str(exc))
    typer.echo(f"Wrote report: {report_path}")
    if export_report:
        typer.echo(f"Exported meeting: {target}")


@app.command("list")
def list_meetings() -> None:
    """List processed meetings in the local workspace."""
    config = load_config()
    meetings = iter_meetings(config.workspace_dir)
    if not meetings:
        typer.echo("No meetings found.")
        return
    for metadata_path in meetings:
        typer.echo(str(metadata_path.parent))


@app.command()
def meet(
    duration: Annotated[int | None, typer.Option("--duration", help="Optional maximum recording length in seconds. Omit to record until stopped.")] = None,
    mic: Annotated[str | None, typer.Option("--mic", help="Microphone name or substring from `nanola devices`.")] = None,
    mic_index: Annotated[int | None, typer.Option("--mic-index", help="1-based microphone index from `nanola devices`.")] = None,
    speaker: Annotated[str | None, typer.Option("--speaker", help="Speaker/output name or substring from `nanola devices`.")] = None,
    speaker_index: Annotated[int | None, typer.Option("--speaker-index", help="1-based speaker/output index from `nanola devices`.")] = None,
    allow_partial: Annotated[bool, typer.Option("--allow-partial", help="Accept meeting capture even if mic or system audio appears silent.")] = False,
    silence_timeout: Annotated[int, typer.Option("--silence-timeout", help="Stop after this many seconds of system-audio silence. Use 0 to disable.")] = 30,
    stop_key: Annotated[str, typer.Option("--stop-key", help="Keyboard key that stops recording.")] = "q",
    meeting_type: Annotated[MeetingType, typer.Option("--type", help="Report template / meeting type.")] = MeetingType.general,
    project: Annotated[str | None, typer.Option(help="Optional project folder under Meetings/Projects.")] = None,
    language: Annotated[Language, typer.Option(help="Transcription language. Prefer es/en when known.")] = Language.auto,
    title: Annotated[str | None, typer.Option(help="Meeting title used for folder naming and report metadata.")] = None,
    attendee: Annotated[list[str] | None, typer.Option("--attendee", help="Attendee name. Can be repeated or comma-separated.")] = None,
    share: Annotated[SharePolicy, typer.Option("--share", help="Shared-folder export policy. `all` exports metadata, report, transcript, and audio.")] = SharePolicy.private,
    llm_profile: Annotated[str, typer.Option("--llm-profile", help="Configured remote LLM profile for report generation.")] = "deepseek_fast",
    llm: Annotated[bool, typer.Option("--llm/--no-llm", help="Generate report with remote LLM. Use --no-llm to avoid sending transcript to LLM.")] = True,
) -> None:
    """Record, transcribe, summarize, and optionally export a meeting with defaults."""
    config = load_config()
    try:
        report = inspect_audio_devices()
        created_at = datetime.now()
        resolved_title = title or f"Recording {created_at:%H:%M}"
        expected_meeting_dir = (
            proposed_archive_parent(config.workspace_dir, project, meeting_type)
            / meeting_folder_name(
                created_at=created_at,
                meeting_type=meeting_type,
                title=resolved_title,
                attendees=_attendees(attendee),
            )
        )
        typer.echo("Starting Nanola meeting workflow with defaults:")
        typer.echo(f"- source: meeting (microphone + system audio)")
        mic_label = f"#{mic_index}" if mic_index is not None else mic or report.default_microphone or "default"
        speaker_label = f"#{speaker_index}" if speaker_index is not None else speaker or report.default_speaker or "default"
        typer.echo(f"- microphone: {mic_label}")
        typer.echo(f"- speaker/system audio: {speaker_label}")
        stop_rule = f"press '{stop_key}'"
        if silence_timeout:
            stop_rule += f" or wait for {silence_timeout}s of system-audio silence"
        typer.echo(f"- stop: {stop_rule}")
        if duration is not None:
            typer.echo(f"- max duration: {duration}s")
        typer.echo(f"- language: {language.value}")
        typer.echo(f"- transcription: local faster-whisper model {config.local_whisper_model}")
        typer.echo(f"- device/compute: {config.local_whisper_device}/{config.local_whisper_compute_type}")
        typer.echo(f"- report: {'enabled' if llm else 'disabled'} ({llm_profile})")
        _print_llm_privacy_notice(llm, llm_profile)
        typer.echo(f"- share: {share.value}")
        typer.echo(f"- meeting folder: {expected_meeting_dir}")
        typer.echo("")
        default_mic_index = _default_device_index(report.microphones, report.default_microphone)
        default_speaker_index = _default_device_index(report.speakers, report.default_speaker)
        typer.echo(f"Change devices with: {_recommended_meet_command(default_mic_index, default_speaker_index)}")
        typer.echo('Or by name: uv run nanola meet --mic "<microphone>" --speaker "<speaker>"')
        typer.echo("List devices with: uv run nanola devices")
        typer.echo("Use explicit language when known: uv run nanola meet --language es")
        typer.echo(f"Stop manually by pressing: {stop_key}")
        typer.echo("")

        options = ProcessOptions(
            audio_path=Path("recorded.wav"),
            meeting_type=meeting_type,
            project=project,
            language=language,
            title=title,
            attendees=_attendees(attendee),
            share_policy=share,
            transcription_backend=TranscriptionBackend.local,
            llm_profile=llm_profile,
        )
        meeting_dir, result = create_recorded_meeting(
            options,
            config,
            source="meeting",
            duration_seconds=duration,
            mic_name=mic,
            mic_index=mic_index,
            speaker_name=speaker,
            speaker_index=speaker_index,
            allow_partial=allow_partial,
            silence_timeout_seconds=silence_timeout,
            stop_key=stop_key,
            created_at=created_at,
            status=_status,
        )
        typer.echo(f"Created meeting: {meeting_dir}")
        _print_recording_result("meeting", result)
        _status("Transcribing recorded meeting...")
        transcript_path = transcribe_meeting(meeting_dir, config, status=_status)
        typer.echo(f"Wrote transcript: {transcript_path}")
        if llm:
            _status("Generating meeting report...")
            report_path = summarize_meeting(meeting_dir, config, status=_status)
            typer.echo(f"Wrote report: {report_path}")
        if share != SharePolicy.private:
            _status(f"Exporting with share policy {share.value}...")
            exported_dir = export_meeting(meeting_dir, config, share)
            typer.echo(f"Exported meeting: {exported_dir}")
    except NanolaError as exc:
        _fail(str(exc))


@app.command()
def record(
    duration: Annotated[int, typer.Option("--duration", help="Recording duration in seconds.")] = 30,
    source: Annotated[str, typer.Option("--source", help="Audio source: mic, system, or meeting.")] = "meeting",
    mic: Annotated[str | None, typer.Option("--mic", help="Microphone name or substring from `nanola devices`.")] = None,
    mic_index: Annotated[int | None, typer.Option("--mic-index", help="1-based microphone index from `nanola devices`.")] = None,
    speaker: Annotated[str | None, typer.Option("--speaker", help="Speaker/output name or substring from `nanola devices`.")] = None,
    speaker_index: Annotated[int | None, typer.Option("--speaker-index", help="1-based speaker/output index from `nanola devices`.")] = None,
    allow_partial: Annotated[bool, typer.Option("--allow-partial", help="Accept meeting capture even if mic or system audio appears silent.")] = False,
    meeting_type: Annotated[MeetingType, typer.Option("--type", help="Report template / meeting type.")] = MeetingType.general,
    project: Annotated[str | None, typer.Option(help="Optional project folder under Meetings/Projects.")] = None,
    language: Annotated[Language, typer.Option(help="Transcription language. Prefer es/en when known.")] = Language.auto,
    title: Annotated[str | None, typer.Option(help="Meeting title used for folder naming and report metadata.")] = None,
    attendee: Annotated[list[str] | None, typer.Option("--attendee", help="Attendee name. Can be repeated or comma-separated.")] = None,
    share: Annotated[SharePolicy, typer.Option("--share", help="Shared-folder export policy. `all` exports metadata, report, transcript, and audio.")] = SharePolicy.private,
    process_after: Annotated[bool, typer.Option("--process/--no-process", help="Transcribe and optionally summarize after recording.")] = False,
    llm: Annotated[bool, typer.Option("--llm/--no-llm", help="Generate report with remote LLM when --process is used.")] = True,
) -> None:
    """Advanced: record a raw WAV. Use `nanola meet` for the normal meeting workflow."""
    config = load_config()
    try:
        options = ProcessOptions(
            audio_path=Path("recorded.wav"),
            meeting_type=meeting_type,
            project=project,
            language=language,
            title=title,
            attendees=_attendees(attendee),
            share_policy=share,
            transcription_backend=TranscriptionBackend.local,
        )
        meeting_dir, result = create_recorded_meeting(
            options,
            config,
            source=source,
            duration_seconds=duration,
            mic_name=mic,
            mic_index=mic_index,
            speaker_name=speaker,
            speaker_index=speaker_index,
            allow_partial=allow_partial,
            status=_status,
        )
        typer.echo(f"Created meeting: {meeting_dir}")
        _print_recording_result(source, result)
        if process_after:
            _status("Processing recorded audio...")
            transcribe_meeting(meeting_dir, config, status=_status)
            if llm:
                _print_llm_privacy_notice(True, None)
                summarize_meeting(meeting_dir, config, status=_status)
            if share != SharePolicy.private:
                _status(f"Exporting with share policy {share.value}...")
                exported_dir = export_meeting(meeting_dir, config, share)
                typer.echo(f"Exported meeting: {exported_dir}")
    except NanolaError as exc:
        _fail(str(exc))
