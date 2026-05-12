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
- Preserve original audio and create a normalized WAV for transcription.
- Transcribe locally with `faster-whisper`, including CUDA support when available.
- Show a preview live transcript during `manola meet`.
- Pause recording during silence and resume when meeting audio returns.
- Compare baseline vs FFmpeg-enhanced voice audio with `audio enhance-test`.
- Generate Markdown reports from transcripts through a configured remote LLM.
- Keep a private local meeting archive and optionally export selected files to a
  synced shared folder such as Google Drive or OneDrive.
- Support meeting metadata such as type, project, title, attendees, language,
  and share policy.

## Status

Manola is an early MVP. The local CLI workflow is usable, but the project is not
yet packaged as a stable end-user application.

Implemented workflows include:

- `manola meet`
- `manola process <audio-path>`
- `manola import <audio-path>`
- `manola transcribe <meeting-id-or-path>`
- `manola summarize <meeting-id-or-path>`
- `manola export <meeting-id-or-path>`
- `manola audio doctor`
- `manola audio setup`
- `manola audio enhance-test <meeting-id-or-audio-path>`
- `manola models download <model>`

Planned work includes VAD/live diarization, making voice enhancement production
ready, diarization, and a desktop interface.

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

The default report profile expects `OPENROUTER_API_KEY` unless the configuration
is changed:

```powershell
$env:OPENROUTER_API_KEY = "..."
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

Record a short meeting capture test:

```powershell
uv run manola audio test --source meeting --duration 10
```

List audio devices:

```powershell
uv run manola devices
```

Download a higher-quality local Whisper model:

```powershell
uv run manola models download large-v3 --set-default
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
