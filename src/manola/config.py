from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import BaseModel, Field

from .errors import ConfigurationError


CONFIG_DIR = Path.home() / ".manola"
CONFIG_PATH = CONFIG_DIR / "config.toml"
SECRETS_PATH = CONFIG_DIR / "secrets.toml"


class LlmProfile(BaseModel):
    base_url: str
    model: str
    api_key_env: str
    thinking: bool = False
    temperature: float = 0.2
    enrichment_temperature: float = 0.0


class AppConfig(BaseModel):
    workspace_dir: Path = Path.home() / "Manola" / "Meetings"
    shared_dir: Path | None = None
    models_dir: Path = Path.home() / ".manola" / "models"
    prompts_dir: Path = Path.home() / ".manola" / "prompts"
    default_llm_profile: str = "deepseek_fast"
    default_generate_llm_report: bool = True
    default_transcription_backend: str = "local"
    default_language: str = "auto"
    default_mic_index: int | None = None
    default_speaker_index: int | None = None
    local_whisper_model: str = "base"
    local_whisper_device: str = "cpu"
    local_whisper_compute_type: str = "int8"
    local_whisper_cpu_fallback: bool = False
    local_whisper_chunk_seconds: int = 300
    live_transcript_model: str = "base"
    live_transcript_device: str = "cpu"
    live_transcript_compute_type: str = "int8"
    live_transcript_window_seconds: int = 20
    live_transcript_overlap_seconds: int = 2
    remote_transcription_url: str | None = None
    remote_transcription_api_key_env: str = "WHISPER_API_KEY"
    llm_profiles: dict[str, LlmProfile] = Field(
        default_factory=lambda: {
            "deepseek_fast": LlmProfile(
                base_url="https://openrouter.ai/api/v1",
                model="deepseek/deepseek-v4-flash",
                api_key_env="OPENROUTER_API_KEY",
                thinking=False,
                temperature=0.2,
                enrichment_temperature=0.0,
            ),
            "gemini_fast": LlmProfile(
                base_url="https://openrouter.ai/api/v1",
                model="google/gemini-2.5-flash-lite",
                api_key_env="OPENROUTER_API_KEY",
                thinking=False,
                temperature=0.2,
                enrichment_temperature=0.0,
            ),
            "sonnet_4_6": LlmProfile(
                base_url="https://openrouter.ai/api/v1",
                model="anthropic/claude-sonnet-4.6",
                api_key_env="OPENROUTER_API_KEY",
                thinking=False,
                temperature=0.3,
                enrichment_temperature=0.0,
            ),
            "openai_fallback": LlmProfile(
                base_url="https://api.openai.com/v1",
                model="gpt-4.1-mini",
                api_key_env="OPENAI_API_KEY",
                temperature=0.2,
                enrichment_temperature=0.0,
            ),
        }
    )


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        return AppConfig()

    raw = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    return AppConfig.model_validate(raw)


def write_default_config(
    *,
    workspace_dir: Path | None = None,
    shared_dir: Path | None = None,
    overwrite: bool = False,
) -> Path:
    if CONFIG_PATH.exists() and not overwrite:
        raise ConfigurationError(f"Config already exists at {CONFIG_PATH}. Use --force to overwrite.")

    config = AppConfig()
    if workspace_dir is not None:
        config.workspace_dir = workspace_dir
    if shared_dir is not None:
        config.shared_dir = shared_dir

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(render_config(config), encoding="utf-8")
    config.workspace_dir.mkdir(parents=True, exist_ok=True)
    if config.shared_dir is not None:
        config.shared_dir.mkdir(parents=True, exist_ok=True)
    return CONFIG_PATH


def write_secrets_template(*, overwrite: bool = False) -> Path:
    if SECRETS_PATH.exists() and not overwrite:
        return SECRETS_PATH

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SECRETS_PATH.write_text(
        "\n".join(
            [
                "# Manola secrets. Prefer environment variables when possible.",
                '# OPENROUTER_API_KEY = "..."',
                '# OPENAI_API_KEY = "..."',
                '# WHISPER_API_KEY = "..."',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return SECRETS_PATH


def update_config_value(name: str, value: str | Path | bool | int | None) -> Path:
    config = load_config()
    if not hasattr(config, name):
        raise ConfigurationError(f"Unknown config field {name!r}.")
    if isinstance(value, Path):
        value = _toml_path(value)
    setattr(config, name, value)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(render_config(config), encoding="utf-8")
    return CONFIG_PATH


def render_config(config: AppConfig) -> str:
    lines = [
        f'workspace_dir = "{_toml_path(config.workspace_dir)}"',
        f'models_dir = "{_toml_path(config.models_dir)}"',
        f'prompts_dir = "{_toml_path(config.prompts_dir)}"',
        f'default_llm_profile = "{config.default_llm_profile}"',
        f"default_generate_llm_report = {str(config.default_generate_llm_report).lower()}",
        f'default_transcription_backend = "{config.default_transcription_backend}"',
        f'default_language = "{config.default_language}"',
        _optional_int_line("default_mic_index", config.default_mic_index, 1),
        _optional_int_line("default_speaker_index", config.default_speaker_index, 3),
        f'local_whisper_model = "{_toml_string(config.local_whisper_model)}"',
        f'local_whisper_device = "{config.local_whisper_device}"',
        f'local_whisper_compute_type = "{config.local_whisper_compute_type}"',
        f"local_whisper_cpu_fallback = {str(config.local_whisper_cpu_fallback).lower()}",
        f"local_whisper_chunk_seconds = {config.local_whisper_chunk_seconds}",
        f'live_transcript_model = "{_toml_string(config.live_transcript_model)}"',
        f'live_transcript_device = "{config.live_transcript_device}"',
        f'live_transcript_compute_type = "{config.live_transcript_compute_type}"',
        f"live_transcript_window_seconds = {config.live_transcript_window_seconds}",
        f"live_transcript_overlap_seconds = {config.live_transcript_overlap_seconds}",
        f'remote_transcription_api_key_env = "{config.remote_transcription_api_key_env}"',
        "",
    ]
    if config.shared_dir is not None:
        lines.insert(1, f'shared_dir = "{_toml_path(config.shared_dir)}"')
    else:
        lines.insert(1, '# shared_dir = "G:/Mi unidad/Team Meetings"')

    if config.remote_transcription_url is not None:
        lines.insert(10, f'remote_transcription_url = "{config.remote_transcription_url}"')
    else:
        lines.insert(10, '# remote_transcription_url = "https://example.com/v1/audio/transcriptions"')

    for name, profile in config.llm_profiles.items():
        lines.extend(
            [
                f'[llm_profiles.{name}]',
                f'base_url = "{profile.base_url}"',
                f'model = "{profile.model}"',
                f"thinking = {str(profile.thinking).lower()}",
                f"temperature = {_toml_float(profile.temperature)}",
                f"enrichment_temperature = {_toml_float(profile.enrichment_temperature)}",
                f'api_key_env = "{profile.api_key_env}"',
                "",
            ]
        )
    return "\n".join(lines)


def load_secrets() -> dict[str, str]:
    if not SECRETS_PATH.exists():
        return {}

    raw = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8-sig"))
    return {str(key): str(value) for key, value in raw.items()}


def has_secret(name: str) -> bool:
    return bool(os.getenv(name) or load_secrets().get(name))


def resolve_secret(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value

    secrets = load_secrets()
    value = secrets.get(name)
    if value:
        return value

    raise ConfigurationError(
        f"Missing secret {name}. Set environment variable {name} or add it to {SECRETS_PATH}."
    )


def _toml_path(path: Path | None) -> str:
    if path is None:
        return ""
    return str(path).replace("\\", "/")


def _toml_string(value: str) -> str:
    return value.replace("\\", "/")


def _optional_int_line(name: str, value: int | None, example: int) -> str:
    if value is None:
        return f"# {name} = {example}"
    return f"{name} = {value}"


def _toml_float(value: float) -> str:
    return f"{value:g}"

