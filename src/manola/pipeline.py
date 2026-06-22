from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from .audio import copy_original, enhance_voice, normalize_audio, normalize_enhance_mode
from .audio_recording import AudioTestResult, record_meeting_until_stopped, record_wav
from .config import AppConfig
from .errors import ManolaError
from .live_transcription import LiveTranscriptSession
from .models import MeetingMetadata, MetadataSuggestions, ProcessOptions
from .naming import (
    generic_recording_title,
    is_generic_recording_title,
    meeting_folder_name,
    proposed_archive_parent,
    slugify,
)
from .reporting import fallback_report, generate_metadata_suggestions, generate_report
from .status import StatusCallback, noop_status
from .transcription import transcribe_audio


def _maybe_enhance_audio(
    normalized: Path,
    mode: str | None,
    status: StatusCallback,
) -> tuple[Path | None, str | None]:
    """Produce ``enhanced.wav`` next to ``normalized`` when a mode is requested.

    Returns the enhanced audio path (or ``None``) and the resolved filtering mode
    (or ``None``). Never touches the original or normalized audio.
    """
    resolved = normalize_enhance_mode(mode)
    if resolved is None:
        return None, None
    status(f"Enhancing voice audio (mode: {resolved})...")
    enhanced = enhance_voice(normalized, normalized.with_name("enhanced.wav"), mode=resolved)
    return enhanced, resolved


def import_recording(
    options: ProcessOptions,
    config: AppConfig,
    status: StatusCallback = noop_status,
) -> Path:
    source = options.audio_path.expanduser().resolve()
    status(f"Preparing meeting archive for {source.name}...")
    created_at = datetime.now()
    title = options.title or source.stem
    meeting_dir = (
        proposed_archive_parent(config.workspace_dir, options.project, options.meeting_type)
        / meeting_folder_name(
            created_at=created_at,
            meeting_type=options.meeting_type,
            title=title,
            attendees=options.attendees,
        )
    )

    audio_dir = meeting_dir / "audio"
    status("Copying original audio...")
    original = copy_original(source, audio_dir)
    status("Normalizing audio with FFmpeg...")
    normalized = normalize_audio(original, audio_dir / "normalized.wav")
    enhanced, enhancement_mode = _maybe_enhance_audio(normalized, options.enhance_voice, status)

    options = options.model_copy(update={"title": title})
    status("Writing metadata and placeholder files...")
    transcript_path = meeting_dir / "transcript.md"
    report_path = meeting_dir / "report.md"
    transcript_path.write_text("", encoding="utf-8")
    report_path.write_text(
        fallback_report(options=options, transcript="", created_at=created_at) + "\n",
        encoding="utf-8",
    )

    metadata = MeetingMetadata(
        id=meeting_dir.name,
        title=title,
        created_at=created_at,
        meeting_type=options.meeting_type,
        project=options.project,
        language=options.language,
        attendees=options.attendees,
        share_policy=options.share_policy,
        transcription_backend=options.transcription_backend,
        transcription_model=config.local_whisper_model if options.transcription_backend == "local" else None,
        transcription_device=config.local_whisper_device if options.transcription_backend == "local" else None,
        transcription_compute_type=config.local_whisper_compute_type if options.transcription_backend == "local" else None,
        llm_profile=options.llm_profile,
        audio_original=str(original.relative_to(meeting_dir)),
        audio_normalized=str(normalized.relative_to(meeting_dir)),
        audio_enhanced=str(enhanced.relative_to(meeting_dir)) if enhanced else None,
        enhancement_mode=enhancement_mode,
        transcript=str(transcript_path.relative_to(meeting_dir)),
        report=str(report_path.relative_to(meeting_dir)),
    )
    (meeting_dir / "metadata.json").write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return meeting_dir


def create_recorded_meeting(
    options: ProcessOptions,
    config: AppConfig,
    *,
    source: str,
    duration_seconds: int | None,
    mic_name: str | None = None,
    mic_index: int | None = None,
    speaker_name: str | None = None,
    speaker_index: int | None = None,
    allow_partial: bool = False,
    silence_timeout_seconds: int = 30,
    pause_after_silence_seconds: int = 10,
    stop_key: str = "q",
    use_vad: bool = True,
    vad_aggressiveness: int = 2,
    live_transcript: bool = False,
    live_transcript_preview: StatusCallback | None = None,
    audio_level: Callable[[dict[str, float]], None] | None = None,
    created_at: datetime | None = None,
    status: StatusCallback = noop_status,
) -> tuple[Path, AudioTestResult]:
    created_at = created_at or datetime.now()
    title = options.title or generic_recording_title(created_at)
    meeting_dir = (
        proposed_archive_parent(config.workspace_dir, options.project, options.meeting_type)
        / meeting_folder_name(
            created_at=created_at,
            meeting_type=options.meeting_type,
            title=title,
            attendees=options.attendees,
        )
    )
    audio_dir = meeting_dir / "audio"
    recorded = audio_dir / "recorded.wav"
    normalized = audio_dir / "normalized.wav"
    transcript_path = meeting_dir / "transcript.md"
    live_transcript_path = meeting_dir / "live_transcript.md"
    report_path = meeting_dir / "report.md"

    status(f"Meeting archive: {meeting_dir}")
    if live_transcript and source != "meeting":
        raise ManolaError("Live transcript is only supported for meeting capture.")

    if duration_seconds is None or live_transcript:
        if source != "meeting":
            raise ManolaError("Open-ended recording is only supported for meeting capture.")
        auto_stop = (
            f" or inactive for {silence_timeout_seconds}s" if silence_timeout_seconds else ""
        )
        if duration_seconds is None:
            status(f"Recording meeting audio until '{stop_key}' is pressed{auto_stop}...")
        else:
            status(f"Recording meeting audio with live transcript for {duration_seconds}s...")
        if live_transcript:
            with LiveTranscriptSession(
                target=live_transcript_path,
                language=options.language,
                config=config,
                status=status,
                preview=live_transcript_preview,
            ) as live:
                recording = record_meeting_until_stopped(
                    target=recorded,
                    mic_name=mic_name,
                    mic_index=mic_index,
                    speaker_name=speaker_name,
                    speaker_index=speaker_index,
                    allow_partial=allow_partial,
                    duration_seconds=duration_seconds,
                    silence_timeout_seconds=silence_timeout_seconds,
                    pause_after_silence_seconds=pause_after_silence_seconds,
                    stop_key=stop_key,
                    use_vad=use_vad,
                    vad_aggressiveness=vad_aggressiveness,
                    status=status,
                    on_audio_chunk=live.add_audio,
                    on_audio_level=audio_level,
                )
        else:
            recording = record_meeting_until_stopped(
                target=recorded,
                mic_name=mic_name,
                mic_index=mic_index,
                speaker_name=speaker_name,
                speaker_index=speaker_index,
                allow_partial=allow_partial,
                duration_seconds=duration_seconds,
                silence_timeout_seconds=silence_timeout_seconds,
                pause_after_silence_seconds=pause_after_silence_seconds,
                stop_key=stop_key,
                use_vad=use_vad,
                vad_aggressiveness=vad_aggressiveness,
                status=status,
                on_audio_level=audio_level,
            )
    else:
        status(f"Recording {source} audio into meeting archive for {duration_seconds}s...")
        recording = record_wav(
            source=source,
            duration_seconds=duration_seconds,
            target=recorded,
            mic_name=mic_name,
            mic_index=mic_index,
            speaker_name=speaker_name,
            speaker_index=speaker_index,
            allow_partial=allow_partial,
        )
    status("Normalizing recorded audio with FFmpeg...")
    normalize_audio(recorded, normalized)
    enhanced, enhancement_mode = _maybe_enhance_audio(normalized, options.enhance_voice, status)

    options = options.model_copy(update={"title": title, "audio_path": recorded})
    status("Writing metadata and placeholder files...")
    transcript_path.write_text("", encoding="utf-8")
    report_path.write_text(
        fallback_report(options=options, transcript="", created_at=created_at) + "\n",
        encoding="utf-8",
    )
    metadata = MeetingMetadata(
        id=meeting_dir.name,
        title=title,
        created_at=created_at,
        meeting_type=options.meeting_type,
        project=options.project,
        language=options.language,
        attendees=options.attendees,
        share_policy=options.share_policy,
        transcription_backend=options.transcription_backend,
        transcription_model=config.local_whisper_model if options.transcription_backend == "local" else None,
        transcription_device=config.local_whisper_device if options.transcription_backend == "local" else None,
        transcription_compute_type=config.local_whisper_compute_type if options.transcription_backend == "local" else None,
        llm_profile=options.llm_profile,
        audio_original=str(recorded.relative_to(meeting_dir)),
        audio_normalized=str(normalized.relative_to(meeting_dir)),
        audio_enhanced=str(enhanced.relative_to(meeting_dir)) if enhanced else None,
        enhancement_mode=enhancement_mode,
        transcript=str(transcript_path.relative_to(meeting_dir)),
        report=str(report_path.relative_to(meeting_dir)),
    )
    (meeting_dir / "metadata.json").write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return meeting_dir, recording


def process_recording(
    options: ProcessOptions,
    config: AppConfig,
    *,
    generate_llm_report: bool,
    status: StatusCallback = noop_status,
) -> Path:
    meeting_dir = import_recording(options, config, status)
    transcribe_meeting(meeting_dir, config, status)
    if generate_llm_report:
        summarize_meeting(meeting_dir, config, status)
    return meeting_dir


def iter_meetings(workspace_dir: Path) -> list[Path]:
    if not workspace_dir.exists():
        return []
    return sorted(workspace_dir.rglob("metadata.json"), reverse=True)


def resolve_meeting(meeting: str | Path, config: AppConfig) -> Path:
    candidate = Path(meeting).expanduser()
    if candidate.exists():
        return candidate.resolve()

    matches = [
        metadata_path.parent
        for metadata_path in iter_meetings(config.workspace_dir)
        if metadata_path.parent.name == str(meeting)
    ]
    if not matches:
        raise ManolaError(f"Meeting not found: {meeting}")
    if len(matches) > 1:
        raise ManolaError(f"Meeting id is ambiguous: {meeting}")
    return matches[0]


def transcribe_meeting(
    meeting_dir: Path,
    config: AppConfig,
    status: StatusCallback = noop_status,
    *,
    force: bool = False,
    skip_existing: bool = True,
) -> Path:
    status(f"Loading meeting metadata from {meeting_dir}...")
    metadata_path = meeting_dir / "metadata.json"
    if not metadata_path.exists():
        raise ManolaError(f"No metadata.json found in {meeting_dir}.")

    metadata = MeetingMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    metadata = metadata.model_copy(
        update={
            "transcription_model": config.local_whisper_model,
            "transcription_device": config.local_whisper_device,
            "transcription_compute_type": config.local_whisper_compute_type,
        }
    )
    normalized = meeting_dir / metadata.audio_normalized
    if not normalized.exists():
        raise ManolaError(f"No normalized audio found at {normalized}.")

    # Prefer enhanced audio for transcription when it was produced; the original
    # and normalized audio are always preserved regardless.
    source_audio = normalized
    if metadata.audio_enhanced:
        enhanced = meeting_dir / metadata.audio_enhanced
        if enhanced.exists():
            source_audio = enhanced

    transcript_path = meeting_dir / metadata.transcript
    if (
        transcript_path.exists()
        and transcript_path.read_text(encoding="utf-8").strip()
        and skip_existing
        and not force
    ):
        status("Transcript already exists; skipping transcription. Use --force to regenerate.")
        return transcript_path

    status(f"Transcribing audio: {source_audio.name}...")
    transcript = transcribe_audio(
        source_audio,
        backend=metadata.transcription_backend,
        language=metadata.language,
        config=config,
        status=status,
    )
    status("Writing transcript.md...")
    transcript_path.write_text(_transcript_document(metadata, transcript), encoding="utf-8")
    metadata_path.write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return transcript_path


def summarize_meeting(
    meeting_dir: Path,
    config: AppConfig,
    status: StatusCallback = noop_status,
    *,
    force: bool = False,
    skip_existing: bool = True,
) -> Path:
    status(f"Loading transcript from {meeting_dir}...")
    metadata_path = meeting_dir / "metadata.json"
    if not metadata_path.exists():
        raise ManolaError(f"No metadata.json found in {meeting_dir}.")

    metadata = MeetingMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    transcript_path = meeting_dir / metadata.transcript
    if not transcript_path.exists():
        raise ManolaError(f"No transcript.md found in {meeting_dir}.")

    report_path = meeting_dir / metadata.report
    if report_path.exists() and skip_existing and not force:
        existing_report = report_path.read_text(encoding="utf-8")
        if "LLM model: not generated" not in existing_report and existing_report.strip():
            status("Report already exists; skipping summary. Use --force to regenerate.")
            return report_path

    options = ProcessOptions(
        audio_path=meeting_dir / metadata.audio_original,
        meeting_type=metadata.meeting_type,
        project=metadata.project,
        language=metadata.language,
        title=metadata.title,
        attendees=metadata.attendees,
        share_policy=metadata.share_policy,
        transcription_backend=metadata.transcription_backend,
        llm_profile=metadata.llm_profile,
    )
    status(f"Generating report with LLM profile {metadata.llm_profile}...")
    report = generate_report(
        options=options,
        transcript=transcript_path.read_text(encoding="utf-8"),
        config=config,
        created_at=metadata.created_at,
        transcription_model=metadata.transcription_model,
        transcription_device=metadata.transcription_device,
        transcription_compute_type=metadata.transcription_compute_type,
    )
    status("Writing report.md...")
    report_path.write_text(report + "\n", encoding="utf-8")
    return report_path


def enrich_meeting(
    meeting_dir: Path,
    config: AppConfig,
    status: StatusCallback = noop_status,
    *,
    force: bool = False,
) -> Path:
    status(f"Loading transcript from {meeting_dir}...")
    metadata_path = meeting_dir / "metadata.json"
    if not metadata_path.exists():
        raise ManolaError(f"No metadata.json found in {meeting_dir}.")

    metadata = MeetingMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    transcript_path = meeting_dir / metadata.transcript
    if not transcript_path.exists() or not transcript_path.read_text(encoding="utf-8").strip():
        raise ManolaError(f"No non-empty transcript.md found in {meeting_dir}.")

    suggestions_path = meeting_dir / "metadata.suggestions.json"
    if suggestions_path.exists() and not force:
        status("Metadata suggestions already exist; skipping enrichment. Use --force to regenerate.")
        return suggestions_path

    options = ProcessOptions(
        audio_path=meeting_dir / metadata.audio_original,
        meeting_type=metadata.meeting_type,
        project=metadata.project,
        language=metadata.language,
        title=metadata.title,
        attendees=metadata.attendees,
        share_policy=metadata.share_policy,
        transcription_backend=metadata.transcription_backend,
        llm_profile=metadata.llm_profile,
    )
    status(f"Generating metadata suggestions with LLM profile {metadata.llm_profile}...")
    suggestions = generate_metadata_suggestions(
        options=options,
        transcript=transcript_path.read_text(encoding="utf-8"),
        config=config,
    )
    status("Writing metadata.suggestions.json...")
    suggestions_path.write_text(
        json.dumps(suggestions.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return suggestions_path


def apply_suggested_title(
    meeting_dir: Path,
    config: AppConfig,
    suggestions: MetadataSuggestions,
    status: StatusCallback = noop_status,
) -> Path:
    """Re-title a freshly created meeting from a high-confidence enrichment title.

    Only acts when the meeting still carries the generic ``Recording HH:MM``
    fallback title and enrichment produced a usable ``suggested_title``. The
    enrichment prompt is told to null out the title when evidence is weak, so a
    present, non-empty title is treated as high-confidence. Renames the meeting
    folder via :func:`meeting_folder_name` and rewrites ``metadata.json``.
    Returns the (possibly unchanged) meeting directory. This is the only
    re-title path; retroactive re-titling of existing meetings is out of scope.
    """
    suggested = (suggestions.suggested_title or "").strip()
    if not suggested:
        return meeting_dir

    metadata_path = meeting_dir / "metadata.json"
    metadata = MeetingMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    if not is_generic_recording_title(metadata.title):
        return meeting_dir
    if not slugify(suggested, ""):
        return meeting_dir

    parent = proposed_archive_parent(config.workspace_dir, metadata.project, metadata.meeting_type)
    target_dir = parent / meeting_folder_name(
        created_at=metadata.created_at,
        meeting_type=metadata.meeting_type,
        title=suggested,
        attendees=metadata.attendees,
    )
    new_dir = meeting_dir
    if target_dir != meeting_dir and not target_dir.exists():
        status(f"Renaming meeting folder to {target_dir.name}...")
        meeting_dir.rename(target_dir)
        new_dir = target_dir

    metadata = metadata.model_copy(update={"title": suggested, "id": new_dir.name})
    (new_dir / "metadata.json").write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    status(f"Applied enrichment title: {suggested}")
    return new_dir


def repair_meeting(
    meeting_dir: Path,
    config: AppConfig,
    status: StatusCallback = noop_status,
) -> Path:
    """Re-normalize from the original audio and re-transcribe, as a recovery step.

    Used when a meeting's health check flags truncated normalized audio or a
    transcript shorter than the source. The original recording
    (``audio_original``) is never overwritten; only ``audio_normalized`` and the
    transcript are regenerated.
    """
    status(f"Loading meeting metadata from {meeting_dir}...")
    metadata_path = meeting_dir / "metadata.json"
    if not metadata_path.exists():
        raise ManolaError(f"No metadata.json found in {meeting_dir}.")

    metadata = MeetingMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    original = meeting_dir / metadata.audio_original
    if not original.exists():
        raise ManolaError(f"No source audio found at {original}; cannot repair.")

    normalized = meeting_dir / metadata.audio_normalized
    status("Re-normalizing source audio with FFmpeg...")
    normalize_audio(original, normalized)
    if metadata.enhancement_mode:
        # Keep enhanced audio consistent with the freshly normalized audio.
        _maybe_enhance_audio(normalized, metadata.enhancement_mode, status)
    status("Re-transcribing repaired audio...")
    return transcribe_meeting(meeting_dir, config, status=status, force=True)


_APPLICABLE_METADATA_FIELDS = ("title", "project", "attendees", "meeting_type", "language", "share_policy")


def apply_metadata_suggestions(
    meeting_dir: Path,
    config: AppConfig,
    updates: dict[str, object],
    status: StatusCallback = noop_status,
) -> Path:
    """Apply user-confirmed metadata fields into ``metadata.json``.

    Only keys in ``_APPLICABLE_METADATA_FIELDS`` are honored; everything else is
    ignored. Raw ``transcript.md`` and untouched metadata fields are preserved.
    If the change alters the canonical folder name (title/type/project/attendees),
    the meeting folder is renamed via :func:`meeting_folder_name`; relative
    artifact paths stay valid, only ``id`` and the folder change. A name
    collision keeps the current folder and still writes the metadata. Unlike
    :func:`apply_suggested_title`, this works on meetings that already have a
    non-generic title (retroactive re-title).
    """
    metadata_path = meeting_dir / "metadata.json"
    if not metadata_path.exists():
        raise ManolaError(f"No metadata.json found in {meeting_dir}.")

    current = MeetingMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    confirmed = {key: value for key, value in updates.items() if key in _APPLICABLE_METADATA_FIELDS}
    if not confirmed:
        return meeting_dir
    if "title" in confirmed and not str(confirmed["title"]).strip():
        raise ManolaError("Refusing to apply an empty meeting title.")

    merged = {**current.model_dump(mode="json"), **confirmed}
    updated = MeetingMetadata.model_validate(merged)  # validates types/enums

    target_parent = proposed_archive_parent(config.workspace_dir, updated.project, updated.meeting_type)
    target_dir = target_parent / meeting_folder_name(
        created_at=updated.created_at,
        meeting_type=updated.meeting_type,
        title=updated.title,
        attendees=updated.attendees,
    )
    new_dir = meeting_dir
    if target_dir != meeting_dir and not target_dir.exists():
        status(f"Renaming meeting folder to {target_dir.name}...")
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        meeting_dir.rename(target_dir)
        new_dir = target_dir
    elif target_dir != meeting_dir:
        status("Target folder already exists; keeping current folder name.")

    updated = updated.model_copy(update={"id": new_dir.name})
    (new_dir / "metadata.json").write_text(
        json.dumps(updated.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    status("Applied metadata suggestions.")
    return new_dir


def _transcript_document(metadata: MeetingMetadata, transcript: str) -> str:
    lines = [
        f"# Transcript: {metadata.title}",
        "",
        f"Transcription backend: {metadata.transcription_backend.value}",
        f"Whisper model: {metadata.transcription_model or 'unknown'}",
        f"Device: {metadata.transcription_device or 'unknown'}",
        f"Compute type: {metadata.transcription_compute_type or 'unknown'}",
        f"Language: {metadata.language.value}",
        "",
        "## Transcript",
        "",
        transcript.strip(),
        "",
    ]
    return "\n".join(lines)
