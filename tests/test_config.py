import tomllib
from pathlib import Path

import pytest

from nanola import config as config_module
from nanola.config import AppConfig, ConfigurationError, load_config, render_config, write_default_config, write_secrets_template


def test_render_config_outputs_valid_toml() -> None:
    rendered = render_config(AppConfig(workspace_dir=Path("C:/Meetings")))

    parsed = tomllib.loads(rendered)

    assert parsed["workspace_dir"] == "C:/Meetings"
    assert parsed["default_llm_profile"] == "deepseek_fast"
    assert "llm_profiles" in parsed
    assert parsed["llm_profiles"]["deepseek_fast"]["base_url"] == "https://openrouter.ai/api/v1"
    assert parsed["llm_profiles"]["deepseek_fast"]["api_key_env"] == "OPENROUTER_API_KEY"


def test_write_default_config_refuses_to_overwrite_without_force(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    secrets_path = tmp_path / "secrets.toml"
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(config_module, "SECRETS_PATH", secrets_path)

    write_default_config(workspace_dir=tmp_path / "meetings")

    with pytest.raises(ConfigurationError):
        write_default_config(workspace_dir=tmp_path / "other")


def test_write_secrets_template_is_non_destructive(monkeypatch, tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.toml"
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "SECRETS_PATH", secrets_path)
    secrets_path.write_text('DEEPSEEK_API_KEY = "real"\n', encoding="utf-8")

    write_secrets_template()

    assert secrets_path.read_text(encoding="utf-8") == 'DEEPSEEK_API_KEY = "real"\n'


def test_load_config_accepts_utf8_bom(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    config_path.write_text(render_config(AppConfig()), encoding="utf-8-sig")

    loaded = load_config()

    assert loaded.default_llm_profile == "deepseek_fast"
