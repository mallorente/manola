from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .errors import DependencyMissingError, NanolaError


SUPPORTED_AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".mp4"}


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def require_supported_audio(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise NanolaError(f"Unsupported audio format {path.suffix!r}. Supported: {supported}.")


def copy_original(source: Path, destination_dir: Path) -> Path:
    require_supported_audio(source)
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / f"original{source.suffix.lower()}"
    shutil.copy2(source, target)
    return target


def normalize_audio(source: Path, target: Path) -> Path:
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        raise DependencyMissingError(
            "FFmpeg is required for audio normalization. Install FFmpeg and ensure ffmpeg is on PATH."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(target),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise NanolaError(f"FFmpeg failed to normalize audio: {details}")
    return target
