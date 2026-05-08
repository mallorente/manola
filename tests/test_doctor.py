from nanola.config import AppConfig
from nanola.doctor import collect_doctor_checks


def test_doctor_reports_missing_default_capabilities() -> None:
    checks = collect_doctor_checks(AppConfig(default_transcription_backend="local"))
    by_name = {check.name: check for check in checks}

    assert by_name["shared_dir"].status == "warn"
    assert by_name["faster-whisper"].status in {"ok", "missing"}
    assert by_name["secret:OPENROUTER_API_KEY"].status in {"ok", "missing"}


def test_doctor_marks_remote_transcription_requirements_missing() -> None:
    checks = collect_doctor_checks(AppConfig(default_transcription_backend="remote"))
    by_name = {check.name: check for check in checks}

    assert by_name["remote_transcription_url"].status == "missing"
    assert by_name["secret:WHISPER_API_KEY"].status in {"ok", "missing"}


def test_doctor_checks_cuda_dependencies_when_cuda_is_configured() -> None:
    checks = collect_doctor_checks(
        AppConfig(default_transcription_backend="local", local_whisper_device="cuda")
    )
    names = {check.name for check in checks}

    assert "CUDA cuBLAS" in names
    assert "CUDA cuDNN" in names
