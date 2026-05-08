from __future__ import annotations

from pathlib import Path

from .config import AppConfig, update_config_value
from .errors import DependencyMissingError, NanolaError


FASTER_WHISPER_REPOS = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}


def download_faster_whisper_model(
    model: str,
    *,
    config: AppConfig,
    set_default: bool = False,
) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise DependencyMissingError(
            "Model downloads require huggingface-hub. Install with: uv sync --extra local-transcription"
        ) from exc

    repo_id = FASTER_WHISPER_REPOS.get(model, model)
    target_dir = config.models_dir / _safe_model_dir_name(repo_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=target_dir,
        )
    except Exception as exc:
        raise NanolaError(f"Failed to download model {repo_id}: {exc}") from exc

    if set_default:
        update_config_value("local_whisper_model", target_dir)
    return target_dir


def list_downloaded_models(config: AppConfig) -> list[Path]:
    if not config.models_dir.exists():
        return []
    return sorted(path for path in config.models_dir.iterdir() if path.is_dir())


def _safe_model_dir_name(repo_id: str) -> str:
    return repo_id.replace("/", "__")
