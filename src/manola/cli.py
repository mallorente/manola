from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Annotated

import typer

from .config import CONFIG_PATH, SECRETS_PATH, load_config, render_config, update_config_value, write_default_config, write_secrets_template
from .doctor import collect_doctor_checks
from .errors import ManolaError
from .audio import copy_original, enhance_voice, normalize_audio
from .audio_recording import inspect_audio_devices, record_audio_test, record_wav
from .exporting import export_meeting
from .models_store import FASTER_WHISPER_REPOS, download_faster_whisper_model, list_downloaded_models
from .models import Language, MeetingType, MetadataSuggestions, ProcessOptions, SharePolicy, TranscriptionBackend
from .migration import migrate_legacy_meetings
from .naming import generic_recording_title, meeting_folder_name, proposed_archive_parent
from .pipeline import apply_suggested_title, create_recorded_meeting, enrich_meeting, import_recording, iter_meetings, process_recording, resolve_meeting, summarize_meeting, transcribe_meeting
from .prompts import iter_prompt_status, load_prompt_template
from .transcription import transcribe_audio
from .ui_server import run_ui_server


app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Local-first meeting recorder, transcriber, and report generator.\n\n"
        "Start here:\n"
        "  uv run manola meet --language es\n"
        "  uv run manola devices\n"
        "  uv run manola process recording.m4a --language es"
    ),
)
audio_app = typer.Typer(no_args_is_help=True, help="Audio device diagnostics and recording tests.")
config_app = typer.Typer(no_args_is_help=True, help="Manage Manola configuration files.")
models_app = typer.Typer(no_args_is_help=True, help="Manage local faster-whisper models.")
prompts_app = typer.Typer(no_args_is_help=True, help="Inspect report prompt templates.")
app.add_typer(audio_app, name="audio")
app.add_typer(config_app, name="config")
app.add_typer(models_app, name="models")
app.add_typer(prompts_app, name="prompts")


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
    typer.echo('Use devices by index: uv run manola meet --mic-index 1 --speaker-index 3')
    typer.echo('Or by name: uv run manola meet --mic "<microphone>" --speaker "<speaker>"')


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
        raise ManolaError(f"Unknown {kind} index: {index}. Available {kind}s: 1-{len(devices)}")
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
    command = "uv run manola meet"
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


def _effective_llm(flag: bool | None, config_default: bool) -> bool:
    return config_default if flag is None else flag


def _console_safe_text(text: str, encoding: str | None = None) -> str:
    target_encoding = encoding or sys.stdout.encoding or "utf-8"
    return text.encode(target_encoding, errors="replace").decode(target_encoding, errors="replace")


def _print_live_transcript_preview(text: str) -> None:
    typer.echo("")
    typer.echo("[live transcript preview]")
    typer.echo(_console_safe_text(text))


def _audio_level_meter(enabled: bool):
    if not enabled or not sys.stdout.isatty():
        return None

    width = 24

    def render(levels: dict[str, float]) -> None:
        mic = levels.get("mic", 0.0)
        system = levels.get("system", 0.0)
        line = f"\rMIC {_level_bar(mic, width)} {mic:0.4f}  SYS {_level_bar(system, width)} {system:0.4f}"
        sys.stdout.write(line)
        sys.stdout.flush()

    return render


def _level_bar(rms: float, width: int) -> str:
    scaled = min(width, max(0, int(rms * 250)))
    return "[" + ("#" * scaled).ljust(width, ".") + "]"


def _configured_language(value: str) -> Language:
    try:
        return Language(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in Language)
        raise ManolaError(f"Invalid default_language in config: {value!r}. Expected one of: {allowed}") from exc


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
    llm: Annotated[bool | None, typer.Option("--llm/--no-llm", help="Generate a report with the configured remote LLM. Uses default_generate_llm_report from config when omitted.")] = None,
    enhance_voice: Annotated[str | None, typer.Option("--enhance-voice", help="Voice enhancement mode for transcription: off, light, denoise, or speech. Writes audio/enhanced.wav and never overwrites the original. Uses default_enhance_voice from config when omitted.")] = None,
) -> None:
    """Process an existing recording into a transcript, report, and local archive."""
    config = load_config()
    effective_llm = _effective_llm(llm, config.default_generate_llm_report)
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
        enhance_voice=enhance_voice if enhance_voice is not None else config.default_enhance_voice,
    )
    try:
        _status("Starting process workflow...")
        _print_llm_privacy_notice(effective_llm, llm_profile)
        meeting_dir = process_recording(options, config, generate_llm_report=effective_llm, status=_status)
        if share != SharePolicy.private:
            _status(f"Exporting with share policy {share.value}...")
            exported_dir = export_meeting(meeting_dir, config, share)
    except ManolaError as exc:
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
    except ManolaError as exc:
        _fail(str(exc))
    typer.echo(f"Imported meeting: {meeting_dir}")


@app.command()
def doctor() -> None:
    """Check local dependencies and Manola configuration."""
    config = load_config()
    typer.echo(f"Config: {CONFIG_PATH}")
    typer.echo(f"Secrets: {SECRETS_PATH}")
    failed = False
    for check in collect_doctor_checks(config):
        typer.echo(f"{check.status:7} {check.name}: {check.detail}")
        failed = failed or check.status == "missing"
    if failed:
        raise typer.Exit(1)


@app.command()
def ui(
    host: Annotated[str, typer.Option("--host", help="Host for the local web UI.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Port for the local web UI.")] = 8765,
) -> None:
    """Start the local Manola web UI."""
    try:
        run_ui_server(host=host, port=port)
    except OSError as exc:
        _fail(f"Could not start Manola UI on {host}:{port}: {exc}")


@app.command("devices")
def devices() -> None:
    """List input and output audio devices."""
    try:
        report = inspect_audio_devices()
    except ManolaError as exc:
        _fail(str(exc))
    _print_audio_devices(report)


@config_app.command("init")
def config_init(
    workspace_dir: Annotated[Path | None, typer.Option("--workspace-dir")] = None,
    shared_dir: Annotated[Path | None, typer.Option("--shared-dir")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Create ~/.manola/config.toml and a secrets template."""
    try:
        config_path = write_default_config(
            workspace_dir=workspace_dir,
            shared_dir=shared_dir,
            overwrite=force,
        )
        secrets_path = write_secrets_template(overwrite=force)
    except ManolaError as exc:
        _fail(str(exc))
    typer.echo(f"Wrote config: {config_path}")
    typer.echo(f"Wrote secrets template: {secrets_path}")


@config_app.command("show")
def config_show() -> None:
    """Print the effective Manola configuration without secrets."""
    typer.echo(render_config(load_config()))


@models_app.command("download")
def models_download(
    model: Annotated[str, typer.Argument(help="Model alias or Hugging Face repo id.")] = "base",
    set_default: Annotated[bool, typer.Option("--set-default")] = True,
) -> None:
    """Download a faster-whisper model into the local Manola model cache."""
    try:
        _status(f"Downloading model {model}...")
        target = download_faster_whisper_model(model, config=load_config(), set_default=set_default)
    except ManolaError as exc:
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


@prompts_app.command("list")
def prompts_list() -> None:
    """List report prompt templates and their active source."""
    try:
        config = load_config()
        typer.echo(f"User prompts directory: {config.prompts_dir}")
        for name, source, is_user_override in iter_prompt_status(config):
            origin = "user" if is_user_override else "default"
            typer.echo(f"{name:18} {origin:7} {source}")
    except ManolaError as exc:
        _fail(str(exc))


@prompts_app.command("show")
def prompts_show(
    name: Annotated[str, typer.Argument(help="Prompt name, for example system, general, job_interview, or case_interview.")],
    llm_profile: Annotated[str | None, typer.Option("--llm-profile", help="Resolve prompt for a specific LLM profile.")] = None,
) -> None:
    """Show the active prompt template for a name."""
    try:
        config = load_config()
        template = load_prompt_template(name, config, profile=llm_profile)
    except ManolaError as exc:
        _fail(str(exc))
    origin = "user override" if template.is_user_override else "default"
    typer.echo(f"Prompt: {name}")
    if llm_profile:
        typer.echo(f"LLM profile: {llm_profile}")
    typer.echo(f"Source: {template.source}")
    typer.echo(f"Origin: {origin}")
    typer.echo(f"Hash: {template.digest}")
    typer.echo("")
    typer.echo(template.text.rstrip())


@audio_app.command("doctor")
def audio_doctor() -> None:
    """Check audio-specific dependencies."""
    try:
        report = inspect_audio_devices()
    except ManolaError as exc:
        _fail(str(exc))
    _print_audio_devices(report)
    if not report.has_meeting_capture:
        raise typer.Exit(1)


@audio_app.command("devices")
def audio_devices() -> None:
    """List input and output audio devices."""
    try:
        report = inspect_audio_devices()
    except ManolaError as exc:
        _fail(str(exc))
    _print_audio_devices(report)


@audio_app.command("test")
def audio_test(
    source: Annotated[str, typer.Option("--source", help="Audio source to test: mic, system, or meeting.")] = "meeting",
    duration: Annotated[int, typer.Option("--duration", help="Test recording duration in seconds.")] = 30,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory for diagnostic WAV files.")] = Path(".manola-audio-tests"),
    mic: Annotated[str | None, typer.Option("--mic", help="Microphone name or substring from `manola devices`.")] = None,
    mic_index: Annotated[int | None, typer.Option("--mic-index", help="1-based microphone index from `manola devices`.")] = None,
    speaker: Annotated[str | None, typer.Option("--speaker", help="Speaker/output name or substring from `manola devices`.")] = None,
    speaker_index: Annotated[int | None, typer.Option("--speaker-index", help="1-based speaker/output index from `manola devices`.")] = None,
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
    except ManolaError as exc:
        _fail(str(exc))
    typer.echo(f"Wrote WAV: {result.path}")
    typer.echo(f"Duration: {result.duration_seconds:0.2f}s")
    typer.echo(f"RMS: {result.rms:0.6f}")
    typer.echo(f"Sample rate: {result.sample_rate}")
    if result.silent:
        typer.echo("Warning: recorded audio appears silent.")


@audio_app.command("enhance-test")
def audio_enhance_test(
    target: Annotated[str, typer.Argument(help="Meeting id/path or standalone audio path to enhance experimentally.")],
    mode: Annotated[str, typer.Option("--mode", help="Enhancement mode: light, denoise, or speech.")] = "light",
    language: Annotated[Language, typer.Option("--language", help="Transcription language for comparison.")] = Language.auto,
    transcribe: Annotated[bool, typer.Option("--transcribe/--no-transcribe", help="Write baseline and enhanced comparison transcripts.")] = True,
    output_dir: Annotated[Path | None, typer.Option("--output-dir", help="Output directory for standalone audio files. Meetings use their own folder by default.")] = None,
) -> None:
    """Create enhanced.wav and optional baseline/enhanced transcripts for comparison."""
    config = load_config()
    try:
        target_path = Path(target).expanduser()
        if target_path.exists() and target_path.is_file():
            test_dir = output_dir or target_path.parent / f"{target_path.stem}-enhance-test"
            audio_dir = test_dir / "audio"
            _status("Copying original audio for enhancement test...")
            original = copy_original(target_path.resolve(), audio_dir)
            _status("Normalizing baseline audio...")
            baseline_audio = normalize_audio(original, audio_dir / "normalized.wav")
            enhanced_audio = audio_dir / "enhanced.wav"
            transcript_dir = test_dir
        else:
            meeting_dir = resolve_meeting(target, config)
            metadata_path = meeting_dir / "metadata.json"
            if not metadata_path.exists():
                raise ManolaError(f"No metadata.json found in {meeting_dir}.")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            baseline_audio = meeting_dir / metadata["audio_normalized"]
            if not baseline_audio.exists():
                raise ManolaError(f"No normalized audio found at {baseline_audio}.")
            enhanced_audio = meeting_dir / "audio" / "enhanced.wav"
            transcript_dir = meeting_dir

        _status(f"Enhancing voice audio with mode {mode}...")
        enhance_voice(baseline_audio, enhanced_audio, mode=mode)
        typer.echo(f"Wrote enhanced audio: {enhanced_audio}")

        if transcribe:
            _status("Transcribing baseline normalized audio...")
            baseline_text = transcribe_audio(
                baseline_audio,
                backend=TranscriptionBackend.local,
                language=language,
                config=config,
                status=_status,
            )
            baseline_transcript = transcript_dir / "transcript.baseline.md"
            baseline_transcript.write_text(baseline_text.strip() + "\n", encoding="utf-8")
            typer.echo(f"Wrote baseline transcript: {baseline_transcript}")

            _status("Transcribing enhanced audio...")
            enhanced_text = transcribe_audio(
                enhanced_audio,
                backend=TranscriptionBackend.local,
                language=language,
                config=config,
                status=_status,
            )
            enhanced_transcript = transcript_dir / "transcript.enhanced.md"
            enhanced_transcript.write_text(enhanced_text.strip() + "\n", encoding="utf-8")
            typer.echo(f"Wrote enhanced transcript: {enhanced_transcript}")
    except ManolaError as exc:
        _fail(str(exc))


@audio_app.command("setup")
def audio_setup(
    duration: Annotated[int, typer.Option("--duration", help="Duration in seconds for each setup recording.")] = 5,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory for setup WAV files.")] = Path(".manola-audio-tests"),
    mic_index: Annotated[int | None, typer.Option("--mic-index", help="1-based microphone index from `manola devices`.")] = None,
    speaker_index: Annotated[int | None, typer.Option("--speaker-index", help="1-based speaker/output index from `manola devices`.")] = None,
    select: Annotated[bool, typer.Option("--select/--no-select", help="Use an interactive arrow-key selector for devices when available.")] = False,
    save: Annotated[bool, typer.Option("--save/--no-save", help="Persist selected devices as defaults for `manola meet`.")] = False,
) -> None:
    """Guided audio setup for microphone, system audio, and meeting capture."""
    try:
        report = inspect_audio_devices()
        typer.echo("Manola audio setup")
        typer.echo("")
        _print_audio_devices(report)
        if not report.default_microphone:
            raise ManolaError("No default microphone found. Connect or enable a microphone and retry.")
        if not report.loopbacks:
            raise ManolaError("No system-audio loopback found. Meeting capture needs loopback audio.")

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
    except ManolaError as exc:
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
    if save:
        update_config_value("default_mic_index", selected_mic_index)
        update_config_value("default_speaker_index", selected_speaker_index)
        typer.echo(f"Saved defaults to {CONFIG_PATH}:")
        typer.echo(f"- default_mic_index = {selected_mic_index or 'system default'}")
        typer.echo(f"- default_speaker_index = {selected_speaker_index or 'system default'}")


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
    except ManolaError as exc:
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
    except ManolaError as exc:
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
    except ManolaError as exc:
        _fail(str(exc))
    typer.echo(f"Wrote report: {report_path}")
    if export_report:
        typer.echo(f"Exported meeting: {target}")


@app.command()
def enrich(
    meeting: Annotated[str, typer.Argument()],
    force: Annotated[bool, typer.Option("--force", help="Regenerate metadata.suggestions.json if it already exists.")] = False,
) -> None:
    """Generate metadata suggestions for an existing transcribed meeting."""
    config = load_config()
    try:
        _status(f"Resolving meeting {meeting}...")
        meeting_dir = resolve_meeting(meeting, config)
        _print_llm_privacy_notice(True, None)
        suggestions_path = enrich_meeting(meeting_dir, config, status=_status, force=force)
    except ManolaError as exc:
        _fail(str(exc))
    typer.echo(f"Wrote suggestions: {suggestions_path}")


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
def migrate(
    apply: Annotated[bool, typer.Option("--apply", help="Move the folders. Without it, only previews the migration.")] = False,
) -> None:
    """Migrate old nested-layout meetings to the simplified workspace layout."""
    config = load_config()
    try:
        moves = migrate_legacy_meetings(config, status=_status, apply=apply)
    except ManolaError as exc:
        _fail(str(exc))
    if not moves:
        typer.echo("No legacy-layout meetings found. Workspace already uses the simplified layout.")
        return
    verb = "Migrated" if apply else "Would migrate"
    for old, new in moves:
        typer.echo(f"{verb}: {old} -> {new}")
    if apply:
        typer.echo(f"\nMigrated {len(moves)} meeting(s).")
    else:
        typer.echo(f"\n{len(moves)} meeting(s) to migrate. Re-run with --apply to move them.")


@app.command()
def meet(
    duration: Annotated[int | None, typer.Option("--duration", help="Optional maximum recording length in seconds. Omit to record until stopped.")] = None,
    mic: Annotated[str | None, typer.Option("--mic", help="Microphone name or substring from `manola devices`.")] = None,
    mic_index: Annotated[int | None, typer.Option("--mic-index", help="1-based microphone index from `manola devices`.")] = None,
    speaker: Annotated[str | None, typer.Option("--speaker", help="Speaker/output name or substring from `manola devices`.")] = None,
    speaker_index: Annotated[int | None, typer.Option("--speaker-index", help="1-based speaker/output index from `manola devices`.")] = None,
    allow_partial: Annotated[bool, typer.Option("--allow-partial", help="Accept meeting capture even if mic or system audio appears silent.")] = False,
    silence_timeout: Annotated[int, typer.Option("--silence-timeout", help="Stop after this many seconds of system-audio silence. Use 0 to disable.")] = 30,
    pause_after_silence: Annotated[int, typer.Option("--pause-after-silence", help="Pause writing silent audio after this many inactive seconds. Use 0 to disable pause/resume.")] = 10,
    stop_key: Annotated[str, typer.Option("--stop-key", help="Keyboard key that stops recording.")] = "q",
    meeting_type: Annotated[MeetingType, typer.Option("--type", help="Report template / meeting type.")] = MeetingType.general,
    project: Annotated[str | None, typer.Option(help="Optional project folder under Meetings/Projects.")] = None,
    language: Annotated[Language | None, typer.Option(help="Transcription language. Prefer es/en when known. Uses default_language from config when omitted.")] = None,
    title: Annotated[str | None, typer.Option(help="Meeting title used for folder naming and report metadata.")] = None,
    attendee: Annotated[list[str] | None, typer.Option("--attendee", help="Attendee name. Can be repeated or comma-separated.")] = None,
    share: Annotated[SharePolicy, typer.Option("--share", help="Shared-folder export policy. `all` exports metadata, report, transcript, and audio.")] = SharePolicy.private,
    llm_profile: Annotated[str | None, typer.Option("--llm-profile", help="Configured remote LLM profile for report generation. Uses default_llm_profile from config when omitted.")] = None,
    llm: Annotated[bool | None, typer.Option("--llm/--no-llm", help="Generate report with remote LLM. Uses default_generate_llm_report from config when omitted.")] = None,
    enrich: Annotated[bool, typer.Option("--enrich/--no-enrich", help="Generate metadata suggestions after transcription when LLM is enabled.")] = True,
    live_transcript: Annotated[bool, typer.Option("--live-transcript/--no-live-transcript", help="Show and persist preview transcript chunks while recording.")] = True,
    levels: Annotated[bool, typer.Option("--levels/--no-levels", help="Show live mic/system audio input levels while recording.")] = True,
    auto_speaker: Annotated[bool, typer.Option("--auto-speaker/--no-auto-speaker", help="Probe loopback inputs and choose the one with active system audio, ignoring saved speaker defaults.")] = False,
) -> None:
    """Record, transcribe, summarize, and optionally export a meeting with defaults."""
    config = load_config()
    try:
        report = inspect_audio_devices()
        effective_language = language or _configured_language(config.default_language)
        effective_llm_profile = llm_profile or config.default_llm_profile
        effective_llm = _effective_llm(llm, config.default_generate_llm_report)
        effective_mic_index = mic_index if mic_index is not None else (None if mic else config.default_mic_index)
        effective_speaker_index = (
            speaker_index
            if speaker_index is not None
            else (None if speaker or auto_speaker else config.default_speaker_index)
        )
        created_at = datetime.now()
        resolved_title = title or generic_recording_title(created_at)
        expected_meeting_dir = (
            proposed_archive_parent(config.workspace_dir, project, meeting_type)
            / meeting_folder_name(
                created_at=created_at,
                meeting_type=meeting_type,
                title=resolved_title,
                attendees=_attendees(attendee),
            )
        )
        typer.echo("Starting Manola meeting workflow with defaults:")
        typer.echo(f"- source: meeting (microphone + system audio)")
        mic_label = f"#{effective_mic_index}" if effective_mic_index is not None else mic or report.default_microphone or "default"
        speaker_label = f"#{effective_speaker_index}" if effective_speaker_index is not None else speaker or report.default_speaker or "default"
        if auto_speaker and speaker is None and speaker_index is None:
            speaker_label = "auto"
        typer.echo(f"- microphone: {mic_label}")
        typer.echo(f"- speaker/system audio: {speaker_label}")
        stop_rule = f"press '{stop_key}'"
        if silence_timeout:
            stop_rule += f" or wait for {silence_timeout}s of mic/system inactivity"
        typer.echo(f"- stop: {stop_rule}")
        if pause_after_silence and silence_timeout and pause_after_silence < silence_timeout:
            typer.echo(f"- pause/resume: pause after {pause_after_silence}s inactive, resume on mic/system audio")
        if duration is not None:
            typer.echo(f"- max duration: {duration}s")
        typer.echo(f"- language: {effective_language.value}")
        typer.echo(f"- transcription: local faster-whisper model {config.local_whisper_model}")
        typer.echo(f"- device/compute: {config.local_whisper_device}/{config.local_whisper_compute_type}")
        if live_transcript:
            typer.echo(
                f"- live transcript: enabled, preview model {config.live_transcript_model} "
                f"on {config.live_transcript_device}/{config.live_transcript_compute_type}"
            )
        else:
            typer.echo("- live transcript: disabled")
        typer.echo(f"- audio levels: {'enabled' if levels else 'disabled'}")
        typer.echo(f"- report: {'enabled' if effective_llm else 'disabled'} ({effective_llm_profile})")
        typer.echo(f"- enrichment: {'enabled' if effective_llm and enrich else 'disabled'}")
        _print_llm_privacy_notice(effective_llm, effective_llm_profile)
        typer.echo(f"- share: {share.value}")
        typer.echo(f"- meeting folder: {expected_meeting_dir}")
        typer.echo("")
        default_mic_index = _default_device_index(report.microphones, report.default_microphone)
        default_speaker_index = _default_device_index(report.speakers, report.default_speaker)
        typer.echo(f"Change devices with: {_recommended_meet_command(default_mic_index, default_speaker_index)}")
        typer.echo('Or by name: uv run manola meet --mic "<microphone>" --speaker "<speaker>"')
        typer.echo("List devices with: uv run manola devices")
        typer.echo("Use explicit language when known: uv run manola meet --language es")
        typer.echo(f"Stop manually by pressing: {stop_key}")
        typer.echo("")

        options = ProcessOptions(
            audio_path=Path("recorded.wav"),
            meeting_type=meeting_type,
            project=project,
            language=effective_language,
            title=title,
            attendees=_attendees(attendee),
            share_policy=share,
            transcription_backend=TranscriptionBackend.local,
            llm_profile=effective_llm_profile,
        )
        meeting_dir, result = create_recorded_meeting(
            options,
            config,
            source="meeting",
            duration_seconds=duration,
            mic_name=mic,
            mic_index=effective_mic_index,
            speaker_name=speaker,
            speaker_index=effective_speaker_index,
            allow_partial=allow_partial,
            silence_timeout_seconds=silence_timeout,
            pause_after_silence_seconds=pause_after_silence,
            stop_key=stop_key,
            live_transcript=live_transcript,
            live_transcript_preview=_print_live_transcript_preview if live_transcript else None,
            audio_level=_audio_level_meter(levels),
            created_at=created_at,
            status=_status,
        )
        if levels and sys.stdout.isatty():
            typer.echo("")
        typer.echo(f"Created meeting: {meeting_dir}")
        if live_transcript:
            typer.echo(f"Wrote live transcript preview: {meeting_dir / 'live_transcript.md'}")
        _print_recording_result("meeting", result)
        _status("Transcribing recorded meeting...")
        transcript_path = transcribe_meeting(meeting_dir, config, status=_status)
        typer.echo(f"Wrote transcript: {transcript_path}")
        if effective_llm and enrich:
            _status("Generating metadata suggestions...")
            suggestions_path = enrich_meeting(meeting_dir, config, status=_status)
            typer.echo(f"Wrote suggestions: {suggestions_path}")
            if suggestions_path.exists():
                suggestions = MetadataSuggestions.model_validate_json(
                    suggestions_path.read_text(encoding="utf-8")
                )
                retitled_dir = apply_suggested_title(meeting_dir, config, suggestions, status=_status)
                if retitled_dir != meeting_dir:
                    meeting_dir = retitled_dir
                    typer.echo(f"Renamed meeting: {meeting_dir}")
        if effective_llm:
            _status("Generating meeting report...")
            report_path = summarize_meeting(meeting_dir, config, status=_status)
            typer.echo(f"Wrote report: {report_path}")
        if share != SharePolicy.private:
            _status(f"Exporting with share policy {share.value}...")
            exported_dir = export_meeting(meeting_dir, config, share)
            typer.echo(f"Exported meeting: {exported_dir}")
    except ManolaError as exc:
        _fail(str(exc))


@app.command()
def record(
    duration: Annotated[int, typer.Option("--duration", help="Recording duration in seconds.")] = 30,
    source: Annotated[str, typer.Option("--source", help="Audio source: mic, system, or meeting.")] = "meeting",
    mic: Annotated[str | None, typer.Option("--mic", help="Microphone name or substring from `manola devices`.")] = None,
    mic_index: Annotated[int | None, typer.Option("--mic-index", help="1-based microphone index from `manola devices`.")] = None,
    speaker: Annotated[str | None, typer.Option("--speaker", help="Speaker/output name or substring from `manola devices`.")] = None,
    speaker_index: Annotated[int | None, typer.Option("--speaker-index", help="1-based speaker/output index from `manola devices`.")] = None,
    allow_partial: Annotated[bool, typer.Option("--allow-partial", help="Accept meeting capture even if mic or system audio appears silent.")] = False,
    meeting_type: Annotated[MeetingType, typer.Option("--type", help="Report template / meeting type.")] = MeetingType.general,
    project: Annotated[str | None, typer.Option(help="Optional project folder under Meetings/Projects.")] = None,
    language: Annotated[Language, typer.Option(help="Transcription language. Prefer es/en when known.")] = Language.auto,
    title: Annotated[str | None, typer.Option(help="Meeting title used for folder naming and report metadata.")] = None,
    attendee: Annotated[list[str] | None, typer.Option("--attendee", help="Attendee name. Can be repeated or comma-separated.")] = None,
    share: Annotated[SharePolicy, typer.Option("--share", help="Shared-folder export policy. `all` exports metadata, report, transcript, and audio.")] = SharePolicy.private,
    process_after: Annotated[bool, typer.Option("--process/--no-process", help="Transcribe and optionally summarize after recording.")] = False,
    llm: Annotated[bool | None, typer.Option("--llm/--no-llm", help="Generate report with remote LLM when --process is used. Uses default_generate_llm_report from config when omitted.")] = None,
    live_transcript: Annotated[bool, typer.Option("--live-transcript/--no-live-transcript", help="Show and persist preview transcript chunks while recording meeting audio.")] = False,
    enhance_voice: Annotated[str | None, typer.Option("--enhance-voice", help="Voice enhancement mode used when --process transcribes: off, light, denoise, or speech. Writes audio/enhanced.wav and never overwrites the recording. Uses default_enhance_voice from config when omitted.")] = None,
) -> None:
    """Advanced: record a raw WAV. Use `manola meet` for the normal meeting workflow."""
    config = load_config()
    effective_llm = _effective_llm(llm, config.default_generate_llm_report)
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
            enhance_voice=enhance_voice if enhance_voice is not None else config.default_enhance_voice,
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
            live_transcript=live_transcript,
            live_transcript_preview=_print_live_transcript_preview if live_transcript else None,
            status=_status,
        )
        typer.echo(f"Created meeting: {meeting_dir}")
        if live_transcript:
            typer.echo(f"Wrote live transcript preview: {meeting_dir / 'live_transcript.md'}")
        _print_recording_result(source, result)
        if process_after:
            _status("Processing recorded audio...")
            transcribe_meeting(meeting_dir, config, status=_status)
            if effective_llm:
                _print_llm_privacy_notice(True, None)
                summarize_meeting(meeting_dir, config, status=_status)
            if share != SharePolicy.private:
                _status(f"Exporting with share policy {share.value}...")
                exported_dir = export_meeting(meeting_dir, config, share)
                typer.echo(f"Exported meeting: {exported_dir}")
    except ManolaError as exc:
        _fail(str(exc))
