# Manola

Manola is a local-first meeting recorder, transcriber, and report generator.

It records or imports meeting audio, normalizes it with FFmpeg, transcribes it with
Whisper-compatible backends, generates structured Markdown reports with an
OpenAI-compatible LLM API, and stores the complete archive locally by default.

The project is currently CLI-first and Windows-first. The core pipeline is built
to stay portable across platforms, but Windows meeting capture is the validated
recording path today.

## Capabilities

- Import existing `.m4a`, `.mp3`, `.wav`, and `.mp4` recordings.
- Record microphone, system audio, or combined meeting audio on Windows.
- Run the default `manola meet` workflow: record meeting audio, transcribe it,
  generate metadata suggestions, generate a report, and optionally export it.
- Use `manola record` for advanced/raw capture tests, with optional processing.
- Preserve original audio and create a normalized WAV for transcription.
- Transcribe locally with `faster-whisper`, including CUDA support when available.
- Transcribe long local audio in chunks.
- Show and persist preview live transcript chunks during `manola meet`.
- Pause recording during silence and resume when meeting audio returns.
- Stop open-ended meeting recording by keypress or silence timeout.
- Select audio devices by name or 1-based index and persist selected defaults.
- Compare baseline vs FFmpeg-enhanced voice audio with `audio enhance-test`.
- Generate Markdown reports from transcripts through a configured remote LLM.
- Generate `metadata.suggestions.json` with title, type, project, attendees,
  notable terms, possible name corrections, and confidence notes.
- Use built-in meeting-specific report prompts, with user overrides and
  model/profile-specific prompt variants.
- Keep a private local meeting archive and optionally export selected files to a
  synced shared folder such as Google Drive or OneDrive.
- Support meeting metadata such as type, project, title, attendees, language,
  and share policy.
- Protect existing transcripts and generated reports by default unless forced.

## Status

Manola is an early MVP. The local CLI workflow is usable, but the project is not
yet packaged as a stable end-user application.

Implemented workflows include:

- `manola meet`
- `manola record`
- `manola process <audio-path>`
- `manola import <audio-path>`
- `manola transcribe <meeting-id-or-path>`
- `manola summarize <meeting-id-or-path>`
- `manola enrich <meeting-id-or-path>`
- `manola export <meeting-id-or-path>`
- `manola list`
- `manola devices`
- `manola config init`
- `manola config show`
- `manola audio doctor`
- `manola audio devices`
- `manola audio test`
- `manola audio setup`
- `manola audio enhance-test <meeting-id-or-audio-path>`
- `manola models download <model>`
- `manola models list`
- `manola prompts list`
- `manola prompts show <name>`

Planned work includes VAD/live diarization, making voice enhancement production
ready, calendar-assisted naming, a terminal meeting browser/TUI, automatic
meeting detection, and a desktop interface.

## Requirements

- Python 3.11 or newer
- `uv`
- FFmpeg available on `PATH`
- Windows for validated local meeting recording
- Optional NVIDIA CUDA runtime support for faster local transcription
- An OpenAI-compatible LLM API key for report generation

## Installation

Clone the repository and install dependencies with `uv`:

```powershell
git clone https://github.com/mallorente/manola.git
cd manola
uv sync --extra dev
```

Run the CLI through `uv`:

```powershell
uv run manola --help
uv run manola doctor
```

Do not assume `manola` is installed globally during development.

## Configuration

Create the local configuration files:

```powershell
uv run manola config init
```

Configuration is stored outside the repository:

```text
~/.manola/config.toml
~/.manola/secrets.toml
```

Secrets are resolved from environment variables first, then from
`~/.manola/secrets.toml`.

The default report profile is `deepseek_fast` and expects `OPENCODE_API_KEY`.
Other built-in profiles include `gemini_fast` and `sonnet_4_6`, which use
`OPENROUTER_API_KEY`, and `openai_fallback`, which uses `OPENAI_API_KEY`.

```powershell
$env:OPENCODE_API_KEY = "..."
```

Secrets must not be committed to the repository or stored in shared meeting
folders.

## Basic Usage

Process an existing recording:

```powershell
uv run manola process path\to\recording.m4a --language es
```

Record and process a meeting:

```powershell
uv run manola meet --language es
```

Record a meeting until `q` is pressed or silence timeout is reached:

```powershell
uv run manola meet --language es --pause-after-silence 10 --silence-timeout 30
```

Disable remote LLM report generation:

```powershell
uv run manola meet --language es --no-llm
```

Disable automatic metadata enrichment while keeping report generation:

```powershell
uv run manola meet --language es --no-enrich
```

Disable preview live transcript:

```powershell
uv run manola meet --language es --no-live-transcript
```

Record a short meeting capture test:

```powershell
uv run manola audio test --source meeting --duration 10
```

List audio devices:

```powershell
uv run manola devices
```

Run guided audio setup and save selected device defaults:

```powershell
uv run manola audio setup --select --save
```

Download a higher-quality local Whisper model:

```powershell
uv run manola models download large-v3 --set-default
```

List downloaded local Whisper models:

```powershell
uv run manola models list
```

List local meetings:

```powershell
uv run manola list
```

For short or noisy recordings, pass the known language explicitly:

```powershell
uv run manola process path\to\recording.m4a --language es
uv run manola process path\to\recording.m4a --language en
```

## Meeting Archive Layout

Manola keeps the complete local archive private by default:

```text
Meetings/
  YYYY-MM-DD__type__topic/
    metadata.json
    report.md
    transcript.md
    metadata.suggestions.json
    live_transcript.md
    audio/
      original.m4a
      normalized.wav
```

Recordings created by Manola use:

```text
audio/
  recorded.wav
  normalized.wav
```

Original audio is never overwritten.

`live_transcript.md` is preview-only. The canonical transcript used for reports
and exports is `transcript.md`.

## Meeting Types

Report generation supports meeting-specific templates for:

- `general`
- `sales_discovery`
- `sales_demo`
- `customer_success`
- `client_update`
- `internal_sync`
- `one_on_one`
- `job_interview`
- `case_interview`
- `project_review`
- `incident_postmortem`
- `brainstorm`
- `strategy`
- `workshop`
- `refinement`
- `daily`
- `retro`
- `planning`

Example:

```powershell
uv run manola meet --type client_update --project "Acme" --language es
```

## Prompts and LLM Profiles

Reports are generated through configurable LLM profiles. The built-in profiles
are:

- `deepseek_fast`: default low-cost report profile through OpenCode Go.
- `gemini_fast`: fast Gemini profile through OpenRouter.
- `sonnet_4_6`: premium Claude Sonnet profile through OpenRouter.
- `openai_fallback`: OpenAI-compatible fallback profile.

Prompt templates are externalized:

- Built-in defaults live in `src/manola/prompts/defaults/`.
- Built-in model/profile prompts live in
  `src/manola/prompts/defaults/models/<llm_profile>/`.
- User overrides live in `~/.manola/prompts/`.
- User model/profile overrides live in
  `~/.manola/prompts/models/<llm_profile>/`.

Inspect active prompts:

```powershell
uv run manola prompts list
uv run manola prompts show general
uv run manola prompts show general --llm-profile sonnet_4_6
```

Generated reports include prompt source and prompt hash metadata.

## Metadata Enrichment

`manola meet` runs enrichment by default when LLM generation is enabled.
Enrichment writes `metadata.suggestions.json` and does not mutate
`metadata.json`.

Run enrichment separately:

```powershell
uv run manola enrich <meeting-id-or-path>
```

Use `--force` to regenerate existing suggestions.

## Sharing

Manola shares through a configured local synced folder, not through a hosted
workspace.

Supported share policies:

- `private`: export nothing
- `report`: export only `report.md`
- `report_transcript`: export `report.md` and `transcript.md`
- `all`: export metadata, report, transcript, and audio

Example:

```powershell
uv run manola process path\to\recording.m4a --language es --share all
```

Export an existing meeting:

```powershell
uv run manola export <meeting-id-or-path> --share all
```

## Existing Output Protection

`transcribe` and `summarize` skip existing generated outputs by default:

- `transcribe` skips a non-empty `transcript.md` unless `--force` is used.
- `summarize` skips an existing generated `report.md` unless `--force` is used.
- `--skip-existing/--no-skip-existing` is available for explicit overwrite
  control.

Examples:

```powershell
uv run manola transcribe <meeting-id-or-path> --summarize --export
uv run manola transcribe <meeting-id-or-path> --force
uv run manola summarize <meeting-id-or-path> --force
```

## Development

Run tests with a workspace-local temp directory:

```powershell
New-Item -ItemType Directory -Force -Path .tmp-pytest | Out-Null
$env:UV_CACHE_DIR='.uv-cache'
$env:TMP=(Resolve-Path .tmp-pytest).Path
$env:TEMP=$env:TMP
uv run --extra dev python -m pytest --basetemp .tmp-pytest\run
```

Run diagnostics:

```powershell
uv run manola doctor
uv run manola audio doctor
```

## Architecture

Main modules:

- `src/manola/cli.py`: Typer CLI commands
- `src/manola/pipeline.py`: import, process, transcribe, summarize orchestration
- `src/manola/audio.py`: FFmpeg normalization and audio import
- `src/manola/audio_recording.py`: soundcard-based recording helpers
- `src/manola/transcription.py`: local and remote transcription
- `src/manola/transcribe_worker.py`: isolated CUDA transcription worker
- `src/manola/reporting.py`: LLM report generation and fallback reports
- `src/manola/prompts.py`: prompt template resolution and rendering
- `src/manola/live_transcription.py`: preview live transcript chunking
- `src/manola/exporting.py`: shared-folder export policies
- `src/manola/config.py`: local config and secret resolution
- `src/manola/doctor.py`: dependency and configuration diagnostics

Product and technical decisions are documented in `docs/`.

## Privacy Model

The local archive is private and complete. Sharing is opt-in through explicit
share policies.

Transcription can run locally with `faster-whisper`. Report generation sends the
transcript to the configured remote LLM provider unless disabled or replaced by a
local reporting backend in the future. The CLI prints this privacy boundary
before report generation in the main meeting workflow.
