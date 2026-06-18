# Manola Status

Last updated: 2026-06-18

## Current State

Manola is a Python CLI managed with `uv` and Typer. The MVP workflow for imported audio and basic Windows recording is implemented.

GUI scaffold added on 2026-06-17:

- Added the first local web UI scaffold, launched with `uv run manola ui`.
- The UI is served by `src/manola/ui_server.py` with static frontend assets in `src/manola/ui_static/`.
- Published the design-completion PRD and AFK task set to GitHub Issues:
  - PRD: https://github.com/mallorente/manola/issues/9
  - Tasks: https://github.com/mallorente/manola/issues/10 through https://github.com/mallorente/manola/issues/24
- Implemented the frontend shell from the Claude Design handoff direction: sidebar navigation, meeting archive, meeting detail tabs, import/record placeholders, devices, doctor, and settings.
- Settings includes an app-language selector and highlight color picker. These UI-only preferences are stored in browser `localStorage`; they are not yet persisted in `~/.manola/config.toml`.
- The UI reads existing meeting metadata, `transcript.md`, `report.md`, audio WAV durations, device diagnostics, and doctor checks through existing Manola functionality.
- Archive rows are grouped by meeting date, show type/language/share/duration metadata with graceful fallbacks, and have an explicit selected-row state.
- The report tab renders `report.md` as readable sections, shows generation context, warns on stale reports, and keeps regeneration as an explicit backend-gap action.
- The transcript tab renders timestamped and speaker-labeled transcript rows, shows Whisper model/device/compute/language context, warns on truncated transcripts, and keeps retranscription as an explicit backend-gap action.
- The audio tab lists source and normalized audio artifacts with duration, file, size, sample-rate/channel details, missing-artifact warnings, truncated-normalized warnings, and an explicit backend-gap repair action.
- The metadata tab shows core metadata, attendees, model/profile details, metadata suggestions from `metadata.suggestions.json`, empty-value fallbacks, and read-only edit/apply/save affordances for missing write endpoints.
- Settings clearly separates browser-local app language/highlight preferences from read-only Manola backend config, including workspace, transcription, LLM, sharing, prompts, and advanced config sections.
- Devices and Doctor screens use real backend data with static readiness indicators, recommended CLI commands, and disabled rerun/test actions for missing browser job endpoints.
- The Record screen is a complete inert workflow with meeting/capture defaults, static mic/system meters, live transcript placeholder, disabled start/stop/process actions, backend-gap messaging, and CLI recording commands.
- The Import screen is a complete inert workflow with source and metadata controls, proposed Manola folder preview, copy/normalize/transcribe/summarize/export pipeline steps, disabled choose/process actions, backend-gap messaging, and CLI import/process commands.
- Disabled enrich/export/repair/retranscribe/regenerate/apply actions now carry specific backend-gap explanations, show CLI alternatives where available, and metadata suggestions surface confidence/evidence detail when present.
- Added health checks for truncated `audio/normalized.wav`, transcript shorter than audio, and stale reports.
- Backend gaps intentionally not implemented yet: recording job API, browser import/file-picker processing API, async transcribe/summarize/export/repair jobs, and Google Recorder-specific import handling. See `docs/UI_PLAN.md`.
- UI verification on 2026-06-17:
  - UI/server subset passed in a separate Python 3.11 verification environment: `9 passed`.
  - Full suite passed in the same environment: `98 passed`.
- Python environment repair on 2026-06-18:
  - Installed `uv`-managed CPython 3.11.15.
  - Recreated `.venv` with `uv venv --python 3.11.15 --clear`.
  - Reinstalled project and dev dependencies with `uv sync --extra dev`.
  - Verified `uv run python --version`, `uv run manola --help`, the documented full test command, the UI/server test subset, and `uv run manola ui --host 127.0.0.1 --port 8765`.
- UI design-completion verification on 2026-06-18:
  - UI/server subset passed with `21 passed`.
  - Full suite passed with `110 passed`.
  - Current smoke command: `uv run manola ui --host 127.0.0.1 --port 8765`.
  - Headless Edge smoke covered archive, selected meeting details, transcript/report/audio/metadata tabs, Record, Import, Settings, Devices, and Doctor screens. Devices rendered the backend error fallback plus CLI commands in the headless browser session.

Roadmap planning published on 2026-06-18:

- Converted the docs backlog + a new feature/bug list into GitHub Issues, organized into dependency-ordered batches with human-check gates (milestone per batch + tracking issue).
- New planning docs: `docs/PRD-UI-Functional-Completion.md` (Batches 1–4), `docs/PRD-Future-Vision.md` (epics F1–F7), and `docs/ADR-0003-ui-job-model.md` (in-process job registry + polling, single-GPU queue, remote-LLM privacy gate).
- GitHub structure:
  - PRDs: #58 (UI Functional Completion), #59 (Intelligence / Future Vision).
  - Milestones: `Batch 1 · Cosmetic & read-only`, `Batch 2 · Job-API keystone`, `Batch 3 · Wire actions`, `Batch 4 · Audio without a terminal`, `Batch 5 · Near-term capability`.
  - Tracking issues (human-check gates): #53–#57.
  - Implementation issues: #26–#45. Future epics: #46–#52.
  - Only Batch 1 (#26–#29) carries `ready-for-agent`; later batches stay `needs-triage` until each gate opens. Tracking issues carry `ready-for-human`.
- Gate workflow: run a batch → human check on its tracking issue → flip the next milestone's issues to `ready-for-agent`.

Security hardening added on 2026-05-12:

- Shared export rejects absolute or parent-traversal paths read from meeting metadata.
- Project names are slugified before becoming `Meetings/Projects/<project>` folders.
- `default_generate_llm_report = true` controls the default LLM behavior for `process`, `meet`, and `record --process`; `--llm/--no-llm` still override it.
- GitHub CI and Dependabot configuration now live under `.github/`.

Working local configuration on the current machine:

- Workspace: `C:/Users/Usuario/Manola/Meetings`
- Shared folder: `G:/Mi unidad/Proyectos/20260502_Legaltech/manola`
- Default transcription backend: local `faster-whisper`
- Default transcription device: CUDA
- DeepSeek/Gemini report generation through OpenRouter is configured with `OPENROUTER_API_KEY`
- CUDA runtime DLLs are provided by NVIDIA Python packages inside `.venv`

## Implemented Commands

Primary workflows:

```powershell
uv run manola meet --language es
uv run manola meet --language es --levels
uv run manola meet --language es --no-levels
uv run manola meet --language es --auto-speaker
uv run manola meet --language es --no-enrich
uv run manola meet --language es --no-live-transcript
uv run manola process <audio-path> --language es --share all
uv run manola import <audio-path> --language es --share all
uv run manola transcribe <meeting-id-or-path> --summarize --export
uv run manola summarize <meeting-id-or-path> --export
uv run manola enrich <meeting-id-or-path>
uv run manola export <meeting-id-or-path> --share all
uv run manola record --duration 30 --source meeting --process --language es --share all
uv run manola record --duration 30 --source meeting --live-transcript
uv run manola ui
```

Setup and diagnostics:

```powershell
uv run manola doctor
uv run manola config show
uv run manola models list
uv run manola models download large-v3 --set-default
uv run manola prompts list
uv run manola prompts show general
uv run manola prompts show general --llm-profile sonnet_4_6
uv run manola devices
uv run manola audio doctor
uv run manola audio devices
uv run manola audio setup
uv run manola audio setup --select
uv run manola audio test --source mic --duration 10
uv run manola audio test --source system --duration 10
uv run manola audio test --source meeting --duration 10
uv run manola audio enhance-test <meeting-id-or-audio-path> --language es
uv run manola record --mic-index 1 --speaker-index 3 --allow-partial
```

## Verified

- `uv run manola doctor` passes on this machine.
- `faster-whisper` works with CUDA through the worker process.
- Imported `.m4a` audio can be normalized, transcribed, summarized with OpenRouter, and exported.
- `record --source mic`, `record --source system`, and `record --source meeting` are backed by `soundcard`.
- `meet` is the simple user-facing workflow: record meeting audio with defaults, pause writing silence after 10s of mic/system inactivity, stop with `q` or after 30s inactive, transcribe, generate metadata suggestions when LLM/enrichment are enabled, summarize, and export only if requested.
- `meet` shows live microphone and system-audio level bars by default in an interactive terminal; use `--no-levels` to disable them.
- Open-ended meeting capture can auto-probe available loopback devices and choose the loopback with active system audio. Use `--auto-speaker` to force probing even if a saved `default_speaker_index` exists.
- `meet` shows confirmed preview transcript chunks by default and persists them to `live_transcript.md`; use `--no-live-transcript` to disable it. `record --source meeting --live-transcript` enables the same preview mode for the advanced recording command. The final `transcript.md` generated after recording remains canonical.
- `audio enhance-test` creates `audio/enhanced.wav` with FFmpeg voice-focused filters and can write `transcript.baseline.md` plus `transcript.enhanced.md` for comparison.
- `audio doctor` detects microphones, speakers, and loopbacks.
- `devices` and `audio devices` are aliases that list input/output devices and show how to pass `--mic-index` / `--speaker-index` or `--mic` / `--speaker`.
- `audio setup` is a guided audio configuration flow: it lists devices, uses default microphone/speaker unless indices are passed, can show a Windows arrow-key selector with `--select`, runs mic/system/meeting test recordings, reports RMS/silence warnings, and prints the recommended `manola meet` command.
- Report prompts are externalized:
  - Built-in defaults live in `src/manola/prompts/defaults/`.
  - Built-in model/profile prompts live in `src/manola/prompts/defaults/models/<llm_profile>/`.
  - User overrides live in `~/.manola/prompts/`.
  - User model/profile overrides live in `~/.manola/prompts/models/<llm_profile>/`.
  - `manola prompts list` and `manola prompts show <name>` inspect the active templates.
  - Use `manola prompts show <name> --llm-profile <profile>` to inspect model-specific prompt resolution.
  - Generated LLM reports record prompt source and prompt hash.
- `enrich <meeting-id-or-path>` generates `metadata.suggestions.json` from the existing transcript without applying changes to `metadata.json`.
- System loopback was verified with real audio playing:
  - `system` RMS: `0.006546`
  - `meeting` RMS: `0.005141`
- Current test suite passes in the repaired 2026-06-18 `.venv` environment:

```powershell
New-Item -ItemType Directory -Force -Path .tmp-pytest | Out-Null
$env:UV_CACHE_DIR='.uv-cache'
$env:TMP=(Resolve-Path .tmp-pytest).Path
$env:TEMP=$env:TMP
uv run --extra dev python -m pytest --basetemp .tmp-pytest\run
```

Latest observed result on 2026-06-18: `110 passed`.

## 2026-05-12 LLM Profile Update

- `deepseek_fast` remains the default report profile and uses `deepseek/deepseek-v4-flash` through OpenRouter.
- Added `gemini_fast` for cheap/fast report generation using `google/gemini-2.5-flash-lite` through OpenRouter.
- Added `sonnet_4_6` for premium report generation using `anthropic/claude-sonnet-4.6` through OpenRouter.
- `openai_fallback` remains available through the OpenAI API.
- Model-specific default prompts are installed:
  - `deepseek_fast`: RTF-style prompts tuned for direct, concise output from DeepSeek V4 Flash.
  - `gemini_fast`: compact COSTAR prompts tuned for low-cost Flash-Lite summarization.
  - `sonnet_4_6`: RISEN/CREA prompts tuned for richer analysis from Claude Sonnet.
- `deepseek_fast` report generation uses OpenRouter. The generated report records prompt source `src/manola/prompts/defaults/models/deepseek_fast/general.md`.

## 2026-06-09 OpenRouter Default Update

- `deepseek_fast` now uses OpenRouter by default:
  - Base URL: `https://openrouter.ai/api/v1`
  - Model: `deepseek/deepseek-v4-flash`
  - Secret: `OPENROUTER_API_KEY`
- The local user config at `C:/Users/Usuario/.manola/config.toml` was updated to the same provider/model.
- Reprocessed latest meeting `C:/Users/Usuario/Nanola/Meetings/2026-06-09__general__recording-16-03`:
  - Forced local CUDA transcription over 10 chunks.
  - Regenerated `transcript.md`.
  - Regenerated `report.md` with `LLM profile: deepseek_fast` and `LLM model: deepseek/deepseek-v4-flash`.
  - Separate `enrich --force` was not rerun after policy review blocked sending the transcript again to an external LLM service.
- LLM profiles now carry separate temperature controls:
  - `temperature` is used for `report.md` generation.
  - `enrichment_temperature` is used for `metadata.suggestions.json`.
  - Defaults are low and conservative: DeepSeek/Gemini/OpenAI reports use `0.2`, Sonnet reports use `0.3`, and all enrichment uses `0.0`.
- Meeting types now include broader product, client, team, and agile workflows:
  - Existing non-hiring types with dedicated prompts: `sales_discovery`, `sales_demo`, `customer_success`, `internal_sync`, `one_on_one`, `project_review`, `incident_postmortem`, and `brainstorm`.
  - New types: `client_update`, `strategy`, `workshop`, `refinement`, `daily`, `retro`, and `planning`.
  - Each specialized meeting type has dedicated report sections and a built-in default prompt.
  - `customer_success`, `client_update`, `daily`, and `retro` also have model-specific prompts for `deepseek_fast`, `gemini_fast`, and `sonnet_4_6`.
  - `customer_success` focuses on account health, adoption, risks, requests, and renewal/expansion signals; `client_update` focuses on delivery progress, client feedback, commitments, blockers, and next steps.

## 2026-05-12 Validation

- `uv run manola audio test --source meeting --duration 10 --mic-index 5 --speaker-index 3` passed with RMS `0.018237`.
- `uv run manola meet --language es --mic-index 5 --speaker-index 3 --duration 60 --pause-after-silence 10 --silence-timeout 30` completed end-to-end.
- The 60s meeting test wrote `audio/recorded.wav`, `audio/normalized.wav`, `live_transcript.md`, `transcript.md`, `metadata.suggestions.json`, and `report.md`.
- Component RMS for the 60s test confirmed both capture sides:
  - microphone RMS: `0.021497`
  - system RMS: `0.032830`
- Final transcription used `large-v3` on CUDA/float16 and generated report/enrichment through `deepseek_fast`.
- Exporting that test meeting with `--share all` copied `metadata.json`, `report.md`, `transcript.md`, `audio/recorded.wav`, and `audio/normalized.wav` to `G:/Mi unidad/Proyectos/20260502_Legaltech/manola/2026-05-12__general__recording-10-48`.
- Fixed a Windows console encoding failure where live transcript preview could crash recording if Whisper produced characters not encodable by the active console code page. `live_transcript.md` remains UTF-8; only console preview text is degraded when needed.
- `manola meet` now reads persisted `default_language`, `default_llm_profile`, `default_mic_index`, and `default_speaker_index` from `~/.manola/config.toml` when the corresponding flags are omitted.
- `manola audio setup --select --save` provides the current guided setup flow: pick devices interactively when possible, run mic/system/meeting checks, and persist the selected device indices for future `manola meet` runs.

## Important Implementation Notes

- Use `uv run manola ...`; `manola` is not installed globally.
- `record` now writes directly into a meeting archive:

```text
C:/Users/Usuario/Manola/Meetings/YYYY-MM-DD__general__recording-HH-MM/
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

- CUDA transcription is isolated in `manola.transcribe_worker` because CTranslate2 can abort during CUDA cleanup on Windows. The worker writes the transcript then exits immediately with `os._exit(0)`.
- Long audio is transcribed in chunks using `local_whisper_chunk_seconds`.
- Live transcript preview uses `live_transcript_model`, `live_transcript_device`, `live_transcript_compute_type`, `live_transcript_window_seconds`, and `live_transcript_overlap_seconds`. Defaults are CPU/base/int8/20s with 2s overlap so preview transcription does not load CUDA inside the recording process.
- Transcript and report now include the Whisper model/device/compute type used.
- CLI preflight now makes LLM privacy explicit: report generation sends the transcript to the configured remote LLM profile unless `--no-llm` is used.
- `meet` prints the selected defaults before recording: source, microphone, speaker/system audio, stop rule, optional max duration, language, Whisper model, device/compute, report profile, share policy, and local output paths.
- `meet --levels/--no-levels` controls the live audio meter. The meter prints separate `MIC` and `SYS` RMS bars so the user can see whether microphone and meeting output are both being captured before relying on the final partial-capture check.
- `meet --no-enrich` skips automatic `metadata.suggestions.json` generation while still allowing report generation.
- `meet` creates `live_transcript.md` as preview-only output by default. It uses overlap windows and simple duplicate-line suppression, but reports and exports still use final `transcript.md`.
- `meet` uses `default_language`, `default_llm_profile`, `default_mic_index`, and `default_speaker_index` from config unless the user overrides them with CLI flags.
- `meet --duration <seconds>` is optional. Without it, recording runs until `--stop-key` is pressed or `--silence-timeout` seconds of mic/system inactivity are observed.
- `meet --pause-after-silence <seconds>` controls pause/resume behavior. The default pauses after 10s inactive and resumes when mic/system audio returns; use `0` to disable pause/resume.
- `record`, `meet`, and `audio test` accept explicit `--mic-index <n>` / `--speaker-index <n>` selectors, plus name-based `--mic "<name>"` / `--speaker "<name>"`.
- If `meet` is started without an explicit speaker selector or saved speaker default, Manola probes loopback inputs briefly and auto-selects the one with the strongest signal. Explicit `--speaker` / `--speaker-index` take precedence; `--auto-speaker` ignores saved speaker defaults and forces probing.
- `audio setup --save` writes `default_mic_index` and `default_speaker_index` to `~/.manola/config.toml` after the guided checks complete.
- `record` remains for advanced/raw capture; `meet` is the normal user-facing command.
- `record --source meeting` now fails if either microphone or system RMS appears silent, unless `--allow-partial` is supplied. The diagnostic WAV is kept at `audio/recorded.wav` when this happens.
- The noisy Windows `soundcard` warning `data discontinuity in recording` is suppressed during capture. Manola relies on explicit duration, RMS, silence, and partial-capture checks for user-facing audio health.
- `transcribe` and `summarize` protect existing generated outputs by default:
  - `transcribe` skips a non-empty `transcript.md` unless `--force` is used.
  - `summarize` skips an existing generated `report.md` unless `--force` is used.
  - Initial fallback reports with `LLM model: not generated` are still replaced by the first real summary.
  - `--skip-existing/--no-skip-existing` is available for explicit overwrite policy control.

## Known Issues / Product Gaps

- PRD includes a Post-MVP Roadmap for calendar-assisted naming, a terminal meeting browser/TUI, and automatic meeting detection.
- `base` Whisper is too weak for faithful meeting transcripts. Prefer `large-v3` for quality or `turbo` for speed.
- Name-based device selection matches names by exact case-insensitive match or substring; ambiguous matches fail and ask for a more specific name. Prefer indices from `manola devices` when names are duplicated.
- Pause/resume is implemented with simple RMS thresholds. It does not yet use VAD or distinguish intentional silence from very quiet speakers.
- Live transcript is implemented as preview-quality chunk transcription with overlap and simple deduplication. It does not yet do VAD or live diarization.
- Voice enhancement exists as an explicit comparison command, not as a default processing step.
- No diarization yet.
- There may be old meeting folders with the former verbose path layout:

```text
Meetings/General/General/Meetings/...
```

New meetings use the simplified layout directly under `Meetings/` unless a project is set.

## Recommended Next Steps

1. Re-transcribe a known recording with explicit language:

```powershell
uv run manola transcribe <meeting-id> --summarize --export
```

2. Try live meeting capture with pause/resume and preview transcript:

```powershell
uv run manola meet --language es --pause-after-silence 10 --silence-timeout 30
```

3. Compare baseline vs enhanced audio on the noisy sample:

```text
uv run manola audio enhance-test "C:/Users/Usuario/OneDrive/Documentos/Grabaciones de sonido/GrabaciÃƒÂ³n (38).m4a" --language es --mode light
```

4. Improve live transcript quality further:

```text
Potential improvements: VAD, tentative text while a chunk is still in progress, and live diarization.
```


