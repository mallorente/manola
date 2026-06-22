"""Optional speaker diarization (Speaker 1/2/... labels) for transcripts.

Diarization answers "who spoke when". We run pyannote.audio to get speaker turns,
then label each timestamped transcript segment with the speaker whose turn it
overlaps most. Named identification is out of scope (see PRD-Future-Vision F4).

pyannote.audio is an optional dependency (``manola[diarization]``) that also needs
a Hugging Face access token to download the pretrained pipeline. When the library
or token is missing, :func:`diarize_audio` returns ``None`` and the transcript is
written without speaker labels — transcription always works regardless.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig, has_secret, resolve_secret
from .status import StatusCallback, noop_status


_SEGMENT_RE = re.compile(r"^\[(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\]\s*(.*)$")


@dataclass(frozen=True)
class SpeakerTurn:
    start: float
    end: float
    speaker: str


def assign_speakers(transcript: str, turns: list[SpeakerTurn]) -> str:
    """Prefix each timestamped transcript line with its dominant speaker.

    A line ``[start-end] text`` becomes ``[start-end] Speaker N: text`` using the
    turn that overlaps the segment most. Lines without a parsable ``[start-end]``
    prefix, or with no overlapping turn, are returned unchanged. This is a pure
    function so it is fully testable without pyannote.
    """
    if not turns:
        return transcript

    labeled_lines: list[str] = []
    for line in transcript.splitlines():
        match = _SEGMENT_RE.match(line.strip())
        if match is None:
            labeled_lines.append(line)
            continue
        start, end, text = float(match.group(1)), float(match.group(2)), match.group(3)
        speaker = _dominant_speaker(start, end, turns)
        if speaker is None:
            labeled_lines.append(line)
            continue
        labeled_lines.append(f"[{start:0.2f}-{end:0.2f}] {speaker}: {text}")
    return "\n".join(labeled_lines)


def _dominant_speaker(start: float, end: float, turns: list[SpeakerTurn]) -> str | None:
    best_speaker: str | None = None
    best_overlap = 0.0
    for turn in turns:
        overlap = min(end, turn.end) - max(start, turn.start)
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = turn.speaker
    return best_speaker


def diarize_audio(
    audio_path: Path,
    config: AppConfig,
    status: StatusCallback = noop_status,
) -> list[SpeakerTurn] | None:
    """Run pyannote diarization, or return ``None`` when unavailable.

    Missing pyannote, a missing Hugging Face token, or any pipeline error are all
    non-fatal: the caller keeps the unlabeled transcript.
    """
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        status(
            "Speaker diarization unavailable (pyannote.audio not installed); "
            "writing transcript without speaker labels. Install with "
            "`uv sync --extra diarization`."
        )
        return None

    if not has_secret(config.huggingface_token_env):
        status(
            f"Speaker diarization needs a Hugging Face token in {config.huggingface_token_env}; "
            "writing transcript without speaker labels."
        )
        return None

    try:
        status(f"Loading diarization pipeline {config.diarization_model}...")
        pipeline = Pipeline.from_pretrained(
            config.diarization_model,
            use_auth_token=resolve_secret(config.huggingface_token_env),
        )
        status("Running speaker diarization...")
        diarization = pipeline(str(audio_path))
    except Exception as exc:  # pyannote raises a variety of runtime errors
        status(f"Speaker diarization failed ({exc}); writing transcript without speaker labels.")
        return None

    return _relabel_turns(diarization)


def _relabel_turns(diarization) -> list[SpeakerTurn]:
    """Convert a pyannote annotation into stable ``Speaker N`` turns."""
    labels: dict[str, str] = {}
    turns: list[SpeakerTurn] = []
    for segment, _track, label in diarization.itertracks(yield_label=True):
        if label not in labels:
            labels[label] = f"Speaker {len(labels) + 1}"
        turns.append(SpeakerTurn(start=float(segment.start), end=float(segment.end), speaker=labels[label]))
    return turns
