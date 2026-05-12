from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .errors import DependencyMissingError, ManolaError


SUPPORTED_AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".mp4"}
VOICE_ENHANCEMENT_MODES = {"light", "denoise"}


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def require_supported_audio(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise ManolaError(f"Unsupported audio format {path.suffix!r}. Supported: {supported}.")


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
        raise ManolaError(f"FFmpeg failed to normalize audio: {details}")
    return target


def enhance_voice(source: Path, target: Path, *, mode: str = "light") -> Path:
    if mode not in VOICE_ENHANCEMENT_MODES:
        supported = ", ".join(sorted(VOICE_ENHANCEMENT_MODES))
        raise ManolaError(f"Unsupported voice enhancement mode {mode!r}. Supported: {supported}.")
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        raise DependencyMissingError(
            "FFmpeg is required for voice enhancement. Install FFmpeg and ensure ffmpeg is on PATH."
        )

    filters = {
        "light": "highpass=f=80,lowpass=f=8000,loudnorm=I=-18:TP=-2:LRA=11,dynaudnorm=f=150:g=15",
        "denoise": "highpass=f=100,lowpass=f=7500,afftdn=nf=-25,loudnorm=I=-18:TP=-2:LRA=11,dynaudnorm=f=150:g=15",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-af",
            filters[mode],
            "-ac",
            "1",
            "-ar",
            "16000",
            str(target),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise ManolaError(f"FFmpeg failed to enhance voice audio: {details}")
    return target
