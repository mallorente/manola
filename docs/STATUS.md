# Nanola Status

Last updated: 2026-05-08

## Current State

Nanola is a Python CLI managed with `uv` and Typer. The MVP workflow for imported audio and basic Windows recording is implemented.

Working local configuration on the current machine:

- Workspace: `C:/Users/Usuario/Nanola/Meetings`
- Shared folder: `G:/Mi unidad/Proyectos/20260502_Legaltech/nanola`
- Default transcription backend: local `faster-whisper`
- Default transcription device: CUDA
- OpenRouter is configured through `OPENROUTER_API_KEY`
- CUDA runtime DLLs are provided by NVIDIA Python packages inside `.venv`

## Implemented Commands

Primary workflows:

```powershell
uv run nanola meet --language es
uv run nanola process <audio-path> --language es --share all
uv run nanola import <audio-path> --language es --share all
uv run nanola transcribe <meeting-id-or-path> --summarize --export
uv run nanola summarize <meeting-id-or-path> --export
uv run nanola export <meeting-id-or-path> --share all
uv run nanola record --duration 30 --source meeting --process --language es --share all
```

Setup and diagnostics:

```powershell
uv run nanola doctor
uv run nanola config show
uv run nanola models list
uv run nanola models download large-v3 --set-default
uv run nanola devices
uv run nanola audio doctor
uv run nanola audio devices
uv run nanola audio setup
uv run nanola audio setup --select
uv run nanola audio test --source mic --duration 10
uv run nanola audio test --source system --duration 10
uv run nanola audio test --source meeting --duration 10
uv run nanola record --mic-index 1 --speaker-index 3 --allow-partial
```

## Verified

- `uv run nanola doctor` passes on this machine.
- `faster-whisper` works with CUDA through the worker process.
- Imported `.m4a` audio can be normalized, transcribed, summarized with OpenRouter, and exported.
- `record --source mic`, `record --source system`, and `record --source meeting` are backed by `soundcard`.
- `meet` is the simple user-facing workflow: record meeting audio with defaults, stop with `q` or 30s of system-audio silence, transcribe, summarize, and export only if requested.
- `audio doctor` detects microphones, speakers, and loopbacks.
- `devices` and `audio devices` are aliases that list input/output devices and show how to pass `--mic-index` / `--speaker-index` or `--mic` / `--speaker`.
- `audio setup` is a guided audio configuration flow: it lists devices, uses default microphone/speaker unless indices are passed, can show a Windows arrow-key selector with `--select`, runs mic/system/meeting test recordings, reports RMS/silence warnings, and prints the recommended `nanola meet` command.
- System loopback was verified with real audio playing:
  - `system` RMS: `0.006546`
  - `meeting` RMS: `0.005141`
- Current test suite passes:

```powershell
New-Item -ItemType Directory -Force -Path .tmp-pytest | Out-Null
$env:UV_CACHE_DIR='.uv-cache'
$env:TMP=(Resolve-Path .tmp-pytest).Path
$env:TEMP=$env:TMP
uv run --extra dev python -m pytest --basetemp .tmp-pytest\run
```

Latest observed result: `42 passed`.

## Important Implementation Notes

- Use `uv run nanola ...`; `nanola` is not installed globally.
- `record` now writes directly into a meeting archive:

```text
C:/Users/Usuario/Nanola/Meetings/YYYY-MM-DD__general__recording-HH-MM/
  metadata.json
  report.md
  transcript.md
  audio/
    recorded.wav
    normalized.wav
```

- Imported files use:

```text
audio/
  original.<ext>
  normalized.wav
```

- Shared export policies:
  - `private`: nothing exported
  - `report`: `report.md`
  - `report_transcript`: `report.md`, `transcript.md`
  - `all`: `metadata.json`, `report.md`, `transcript.md`, audio files

- CUDA transcription is isolated in `nanola.transcribe_worker` because CTranslate2 can abort during CUDA cleanup on Windows. The worker writes the transcript then exits immediately with `os._exit(0)`.
- Long audio is transcribed in chunks using `local_whisper_chunk_seconds`.
- Transcript and report now include the Whisper model/device/compute type used.
- CLI preflight now makes LLM privacy explicit: report generation sends the transcript to the configured remote LLM profile unless `--no-llm` is used.
- `meet` prints the selected defaults before recording: source, microphone, speaker/system audio, stop rule, optional max duration, language, Whisper model, device/compute, report profile, share policy, and local output paths.
- `meet --duration <seconds>` is optional. Without it, recording runs until `--stop-key` is pressed or `--silence-timeout` seconds of system-audio silence are observed.
- `record`, `meet`, and `audio test` accept explicit `--mic-index <n>` / `--speaker-index <n>` selectors, plus name-based `--mic "<name>"` / `--speaker "<name>"`.
- `record` remains for advanced/raw capture; `meet` is the normal user-facing command.
- `record --source meeting` now fails if either microphone or system RMS appears silent, unless `--allow-partial` is supplied. The diagnostic WAV is kept at `audio/recorded.wav` when this happens.
- The noisy Windows `soundcard` warning `data discontinuity in recording` is suppressed during capture. Nanola relies on explicit duration, RMS, silence, and partial-capture checks for user-facing audio health.
- `transcribe` and `summarize` protect existing generated outputs by default:
  - `transcribe` skips a non-empty `transcript.md` unless `--force` is used.
  - `summarize` skips an existing generated `report.md` unless `--force` is used.
  - Initial fallback reports with `LLM model: not generated` are still replaced by the first real summary.
  - `--skip-existing/--no-skip-existing` is available for explicit overwrite policy control.

## Known Issues / Product Gaps

- `base` Whisper is too weak for faithful meeting transcripts. Prefer `large-v3` for quality or `turbo` for speed.
- Name-based device selection matches names by exact case-insensitive match or substring; ambiguous matches fail and ask for a more specific name. Prefer indices from `nanola devices` when names are duplicated.
- Current auto-stop is simple: it stops after system-audio silence. A richer pause/resume design is still pending.
- No live transcript yet.
- No voice enhancement yet. PRD documents this as V2.
- No diarization yet.
- There may be old meeting folders with the former verbose path layout:

```text
Meetings/General/General/Meetings/...
```

New meetings use the simplified layout directly under `Meetings/` unless a project is set.

## Recommended Next Steps

1. Download and test a higher-quality model:

```powershell
uv run nanola models download large-v3 --set-default
```

2. Re-transcribe a known recording with explicit language:

```powershell
uv run nanola transcribe <meeting-id> --summarize --export
```

3. Design pause/resume auto-stop:

```text
pause after X seconds of silence, resume on mic/system voice or keypress, stop after Y seconds
```

4. Implement live transcript:

```powershell
uv run nanola record --live-transcript
```

5. Prototype voice enhancement V2 with the audio sample:

```text
C:/Users/Usuario/OneDrive/Documentos/Grabaciones de sonido/Grabación (38).m4a
```
