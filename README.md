# Nanola

Local-first CLI for processing meeting recordings into transcripts and Markdown reports.

## Development

```powershell
uv run nanola config init
uv run nanola doctor
uv run nanola process path\to\recording.m4a --backend remote --title "Meeting title"
```

FFmpeg is required for audio normalization.

For local transcription:

```powershell
uv sync --extra local-transcription
```

The default LLM profile uses DeepSeek through OpenRouter. Secrets are resolved from environment variables first, then `~/.nanola/secrets.toml`.
