# ADR-0001: Local-First CLI Architecture

## Status

Accepted

## Context

Manola needs to capture or import meeting audio, transcribe it, generate structured meeting reports, and optionally share reports with a team. The product must work locally first, support sensitive meeting data, and remain viable for Windows, Linux, and macOS.

The repository is starting empty, so the first decision is the shape of the product and implementation, not integration with existing code.

## Decision

Manola will start as a local-first Python CLI using `uv` and Typer.

The CLI is the first product surface. A desktop UI may be added later on top of the same backend services.

Core technical decisions:

- Python package managed with `uv`.
- Typer for CLI.
- FFmpeg required for audio normalization.
- `faster-whisper` as the primary local transcription backend.
- Remote Whisper-compatible transcription supported from the start.
- Remote OpenAI-compatible LLM abstraction for report generation.
- DeepSeek `deepseek/deepseek-v4-flash` through OpenRouter as the default report model.
- Gemini Flash-Lite through OpenRouter as a cheap alternate report model.
- Claude Sonnet through OpenRouter as the premium report model.
- OpenAI `gpt-4.1-mini` as an optional fallback.
- Markdown as the canonical report format.
- Local synced folders, especially Google Drive for Desktop and OneDrive, for sharing.
- Configuration in `~/.manola`.
- Secrets from environment variables or `~/.manola/secrets.toml`.

## Rationale

CLI-first gives the shortest path to value because the user already has `.m4a` recordings. It also avoids delaying the core transcription/report loop behind desktop capture and UI complexity.

Python is the pragmatic choice because the audio/transcription ecosystem is strongest there, especially around Whisper, FFmpeg wrappers, and optional diarization libraries.

Local-first protects raw meeting data by default. Using a synced folder for sharing avoids building a SaaS workspace or requiring Google Drive API integration in the MVP.

Remote LLM summarization is accepted because high-quality report generation matters and local LLM support would add substantial complexity. Provider choice remains configurable.

## Consequences

Positive:

- Fast MVP path.
- Good fit for Whisper and audio processing.
- Easy to run locally during development.
- Desktop UI can reuse the same backend later.
- Sharing works with existing company sync tools.

Tradeoffs:

- Users must install system dependencies such as FFmpeg.
- CLI UX is less friendly than a desktop app.
- Remote summarization sends transcript content to the selected LLM provider.
- Cross-platform recording remains a separate technical risk.

## Configuration Shape

Example:

```toml
workspace_dir = "C:/Users/Usuario/Meetings"
shared_dir = "G:/Mi unidad/Team Meetings"
default_llm_profile = "deepseek_fast"
default_transcription_backend = "local"
default_language = "auto"

[llm_profiles.deepseek_fast]
base_url = "https://openrouter.ai/api/v1"
model = "deepseek/deepseek-v4-flash"
thinking = false
temperature = 0.2
enrichment_temperature = 0.0
api_key_env = "OPENROUTER_API_KEY"

[llm_profiles.gemini_fast]
base_url = "https://openrouter.ai/api/v1"
model = "google/gemini-2.5-flash-lite"
thinking = false
temperature = 0.2
enrichment_temperature = 0.0
api_key_env = "OPENROUTER_API_KEY"

[llm_profiles.sonnet_4_6]
base_url = "https://openrouter.ai/api/v1"
model = "anthropic/claude-sonnet-4.6"
thinking = false
temperature = 0.3
enrichment_temperature = 0.0
api_key_env = "OPENROUTER_API_KEY"

[llm_profiles.openai_fallback]
base_url = "https://api.openai.com/v1"
model = "gpt-4.1-mini"
temperature = 0.2
enrichment_temperature = 0.0
api_key_env = "OPENAI_API_KEY"
```

Report generation and enrichment use separate temperature settings. `temperature` controls prose reports; `enrichment_temperature` controls JSON metadata extraction and defaults to `0.0` to reduce invented titles, attendees, projects, and corrections.

## Related Decisions

- ADR-0002 covers Windows meeting recording and the audio spike.

