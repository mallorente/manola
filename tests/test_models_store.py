from pathlib import Path
from types import SimpleNamespace

from nanola import config as config_module
from nanola.config import AppConfig, render_config
from nanola.models_store import download_faster_whisper_model, list_downloaded_models


def test_download_model_uses_known_alias_and_sets_default(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    config_path.write_text(render_config(AppConfig(models_dir=tmp_path / "models")), encoding="utf-8")

    calls = []

    def fake_snapshot_download(*, repo_id: str, local_dir: Path) -> None:
        calls.append((repo_id, local_dir))
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "model.bin").write_text("model", encoding="utf-8")

    monkeypatch.setitem(
        __import__("sys").modules,
        "huggingface_hub",
        SimpleNamespace(snapshot_download=fake_snapshot_download),
    )

    target = download_faster_whisper_model("base", config=AppConfig(models_dir=tmp_path / "models"), set_default=True)

    assert target == tmp_path / "models" / "Systran__faster-whisper-base"
    assert calls == [("Systran/faster-whisper-base", target)]
    assert "local_whisper_model" in config_path.read_text(encoding="utf-8")
    assert str(target).replace("\\", "/") in config_path.read_text(encoding="utf-8")


def test_list_downloaded_models_returns_only_directories(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    (models_dir / "one").mkdir(parents=True)
    (models_dir / "file.txt").write_text("x", encoding="utf-8")

    assert list_downloaded_models(AppConfig(models_dir=models_dir)) == [models_dir / "one"]
