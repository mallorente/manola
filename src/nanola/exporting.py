from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config import AppConfig
from .errors import ConfigurationError, NanolaError
from .models import SharePolicy


def export_meeting(meeting_dir: Path, config: AppConfig, policy: SharePolicy | None = None) -> Path:
    if config.shared_dir is None:
        raise ConfigurationError("Export requires shared_dir in ~/.nanola/config.toml.")

    metadata_path = meeting_dir / "metadata.json"
    if not metadata_path.exists():
        raise NanolaError(f"No metadata.json found in {meeting_dir}.")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    chosen_policy = policy or SharePolicy(metadata.get("share_policy", SharePolicy.private.value))
    if chosen_policy == SharePolicy.private:
        raise NanolaError("Share policy is private; nothing to export.")

    target_dir = config.shared_dir / meeting_dir.name
    target_dir.mkdir(parents=True, exist_ok=True)
    files = _files_for_policy(chosen_policy, metadata)
    for relative in files:
        source = meeting_dir / relative
        if source.exists():
            destination = target_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    return target_dir


def _files_for_policy(policy: SharePolicy, metadata: dict) -> list[Path]:
    if policy == SharePolicy.report:
        return [Path("report.md")]
    if policy == SharePolicy.report_transcript:
        return [Path("report.md"), Path("transcript.md")]
    if policy == SharePolicy.all:
        audio_original = Path(metadata.get("audio_original", "audio/original.m4a"))
        audio_normalized = Path(metadata.get("audio_normalized", "audio/normalized.wav"))
        return [
            Path("metadata.json"),
            Path("report.md"),
            Path("transcript.md"),
            audio_original,
            audio_normalized,
        ]
    return []
