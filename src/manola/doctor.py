from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass

from .audio import ffmpeg_path
from .config import AppConfig, CONFIG_PATH, has_secret
from .cuda import find_dll


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.status in {"ok", "warn"}


def collect_doctor_checks(config: AppConfig) -> list[DoctorCheck]:
    ffmpeg = ffmpeg_path()
    has_faster_whisper = importlib.util.find_spec("faster_whisper") is not None
    checks = [
        DoctorCheck(
            "config",
            "ok" if CONFIG_PATH.exists() else "warn",
            str(CONFIG_PATH) if CONFIG_PATH.exists() else "not created; run manola config init",
        ),
        DoctorCheck("FFmpeg", "ok" if ffmpeg else "missing", ffmpeg or "ffmpeg not found on PATH"),
        DoctorCheck(
            "faster-whisper",
            _local_transcription_status(config, has_faster_whisper),
            "installed"
            if has_faster_whisper
            else "not installed; local transcription will not work",
        ),
        DoctorCheck("workspace_dir", "ok", str(config.workspace_dir)),
    ]

    if config.shared_dir is not None:
        checks.append(
            DoctorCheck(
                "shared_dir",
                "ok" if config.shared_dir.exists() else "warn",
                str(config.shared_dir),
            )
        )
    else:
        checks.append(DoctorCheck("shared_dir", "warn", "not configured; export is disabled"))

    if config.default_transcription_backend == "remote":
        checks.extend(_remote_transcription_checks(config))
    if config.default_transcription_backend == "local" and config.local_whisper_device == "cuda":
        checks.extend(_cuda_checks())

    profile = config.llm_profiles.get(config.default_llm_profile)
    if profile is None:
        checks.append(
            DoctorCheck("default_llm_profile", "missing", f"unknown profile {config.default_llm_profile!r}")
        )
    else:
        checks.append(
            DoctorCheck(
                f"secret:{profile.api_key_env}",
                "ok" if has_secret(profile.api_key_env) else "missing",
                "configured" if has_secret(profile.api_key_env) else "missing; LLM reports will fail until configured",
            )
        )

    return checks


def _local_transcription_status(config: AppConfig, has_faster_whisper: bool) -> str:
    if has_faster_whisper:
        return "ok"
    if config.default_transcription_backend == "local":
        return "missing"
    return "warn"


def _cuda_checks() -> list[DoctorCheck]:
    nvidia_smi = shutil.which("nvidia-smi")
    cublas = find_dll("cublas64_12.dll")
    cudnn = find_dll("cudnn64_9.dll")
    return [
        DoctorCheck(
            "nvidia-smi",
            "ok" if nvidia_smi else "missing",
            nvidia_smi or "not found on PATH; NVIDIA driver/CUDA runtime may be unavailable",
        ),
        DoctorCheck(
            "CUDA cuBLAS",
            "ok" if cublas else "missing",
            str(cublas) if cublas else "cublas64_12.dll not found on PATH or in NVIDIA Python packages",
        ),
        DoctorCheck(
            "CUDA cuDNN",
            "ok" if cudnn else "missing",
            str(cudnn) if cudnn else "cudnn64_9.dll not found on PATH or in NVIDIA Python packages",
        ),
    ]


def _remote_transcription_checks(config: AppConfig) -> list[DoctorCheck]:
    checks = []
    checks.append(
        DoctorCheck(
            "remote_transcription_url",
            "ok" if config.remote_transcription_url else "missing",
            config.remote_transcription_url or "required when default_transcription_backend = remote",
        )
    )
    checks.append(
        DoctorCheck(
            f"secret:{config.remote_transcription_api_key_env}",
            "ok" if has_secret(config.remote_transcription_api_key_env) else "missing",
            "configured" if has_secret(config.remote_transcription_api_key_env) else "missing remote transcription API key",
        )
    )
    return checks
