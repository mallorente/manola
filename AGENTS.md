# AGENTS.md

## Project

Nanola is a local-first meeting recorder, transcriber, and report generator.

Stack:

- Python 3.11+
- `uv`
- Typer CLI
- FFmpeg
- `faster-whisper`
- `soundcard`
- OpenRouter/OpenAI-compatible LLM API

## Commands

Run tests with a workspace-local temp directory:

```powershell
New-Item -ItemType Directory -Force -Path .tmp-pytest | Out-Null
$env:UV_CACHE_DIR='.uv-cache'
$env:TMP=(Resolve-Path .tmp-pytest).Path
$env:TEMP=$env:TMP
uv run --extra dev python -m pytest --basetemp .tmp-pytest\run
```

Run the CLI through `uv`:

```powershell
uv run nanola doctor
uv run nanola --help
```

Do not assume `nanola` is installed globally.

## Repo Structure

```text
src/nanola/
  cli.py              Typer commands
  pipeline.py         import/process/transcribe/summarize orchestration
  audio.py            FFmpeg normalization and audio import
  audio_recording.py  soundcard-based recording spike and record helpers
  transcription.py    local/remote transcription
  transcribe_worker.py CUDA worker process
  reporting.py        LLM report generation and fallback reports
  exporting.py        shared-folder export policies
  config.py           ~/.nanola config/secrets
  naming.py           meeting folder naming
  models_store.py     local faster-whisper model downloads
  doctor.py           dependency/config diagnostics
docs/
  PRD.md
  ADR-0001-local-first-cli.md
  ADR-0002-windows-recording-spike.md
  STATUS.md
```

## Current Behavior

- Local archive is private and complete.
- Shared export is controlled by `share_policy`.
- `record` writes directly into a meeting folder, not a separate staging folder.
- Meeting folder layout is intentionally simple:

```text
Meetings/YYYY-MM-DD__type__topic/
Meetings/Projects/<project>/YYYY-MM-DD__type__topic/
```

- Avoid reintroducing the old nested layout:

```text
Meetings/General/General/Meetings/...
```

## Important Constraints

- Preserve original audio. Never overwrite raw input.
- Keep `audio/recorded.wav` or `audio/original.<ext>` plus `audio/normalized.wav`.
- `--share all` must export `metadata.json`, `report.md`, `transcript.md`, and audio.
- Transcript/report should include the Whisper model, device, and compute type.
- Use explicit `--language es` or `--language en` when known; `auto` can reduce quality on short/noisy recordings.
- `base` Whisper is for smoke tests only. Prefer `large-v3` for faithful transcripts.

## Windows CUDA Note

CTranslate2/faster-whisper works with CUDA on this machine through NVIDIA Python packages in `.venv`.

Do not remove:

- `nvidia-cublas-cu12`
- `nvidia-cudnn-cu12`
- `cuda.py`
- `transcribe_worker.py`

The worker exists because CTranslate2 can abort on CUDA cleanup on Windows. The worker persists output, then exits with `os._exit(0)`.

## Audio Recording Note

`soundcard` is the current backend.

Validated commands:

```powershell
uv run nanola audio doctor
uv run nanola audio test --source mic --duration 10
uv run nanola audio test --source system --duration 10
uv run nanola audio test --source meeting --duration 10
```

System loopback and meeting capture have been verified with non-zero RMS.

## Documentation

Update `docs/PRD.md` for product requirements.

Use ADRs for durable technical decisions:

- ADR = Architecture Decision Record.
- PRD says what the product should do.
- ADR says why a technical approach was chosen and what tradeoffs it creates.

Update `docs/STATUS.md` after meaningful implementation milestones so future sessions can resume quickly.
