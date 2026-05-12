import tomllib
from pathlib import Path

import pytest

from manola import config as config_module
from manola.config import AppConfig, ConfigurationError, load_config, render_config, write_default_config, write_secrets_template


def test_render_config_outputs_valid_toml() -> None:
    rendered = render_config(AppConfig(workspace_dir=Path("C:/Meetings")))

    parsed = tomllib.loads(rendered)

    assert parsed["workspace_dir"] == "C:/Meetings"
    assert parsed["default_llm_profile"] == "deepseek_fast"
    assert "default_mic_index" not in parsed
    assert "default_speaker_index" not in parsed
    assert "llm_profiles" in parsed
    assert parsed["llm_profiles"]["deepseek_fast"]["base_url"] == "https://opencode.ai/zen/go/v1"
    assert parsed["llm_profiles"]["deepseek_fast"]["model"] == "deepseek-v4-flash"
    assert parsed["llm_profiles"]["deepseek_fast"]["api_key_env"] == "OPENCODE_API_KEY"
    assert parsed["llm_profiles"]["deepseek_fast"]["temperature"] == 0.2
    assert parsed["llm_profiles"]["deepseek_fast"]["enrichment_temperature"] == 0.0
    assert parsed["llm_profiles"]["gemini_fast"]["model"] == "google/gemini-2.5-flash-lite"
    assert parsed["llm_profiles"]["gemini_fast"]["api_key_env"] == "OPENROUTER_API_KEY"
    assert parsed["llm_profiles"]["gemini_fast"]["temperature"] == 0.2
    assert parsed["llm_profiles"]["gemini_fast"]["enrichment_temperature"] == 0.0
    assert parsed["llm_profiles"]["sonnet_4_6"]["model"] == "anthropic/claude-sonnet-4.6"
    assert parsed["llm_profiles"]["sonnet_4_6"]["api_key_env"] == "OPENROUTER_API_KEY"
    assert parsed["llm_profiles"]["sonnet_4_6"]["temperature"] == 0.3
    assert parsed["llm_profiles"]["sonnet_4_6"]["enrichment_temperature"] == 0.0


def test_render_config_includes_persisted_meet_device_defaults() -> None:
    rendered = render_config(AppConfig(default_mic_index=5, default_speaker_index=3))

    parsed = tomllib.loads(rendered)

    assert parsed["default_mic_index"] == 5
    assert parsed["default_speaker_index"] == 3


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
    secrets_path.write_text('OPENROUTER_API_KEY = "real"\n', encoding="utf-8")

    write_secrets_template()

    assert secrets_path.read_text(encoding="utf-8") == 'OPENROUTER_API_KEY = "real"\n'


def test_load_config_accepts_utf8_bom(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    config_path.write_text(render_config(AppConfig()), encoding="utf-8-sig")

    loaded = load_config()

    assert loaded.default_llm_profile == "deepseek_fast"

