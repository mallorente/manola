# Manola GUI Plan

Date: 2026-06-18

## Direction

Build a desktop-class local UI and validate it first as a browser-based local web app:

```powershell
uv run manola ui --host 127.0.0.1 --port 8765
```

The UI should feel like a desktop recorder/archive tool and remain packageable later with a desktop shell. The first implementation deliberately avoids adding a frontend build system.

## GitHub Planning Issues

- Parent PRD: https://github.com/mallorente/manola/issues/9
- Implementation task set: https://github.com/mallorente/manola/issues/10 through https://github.com/mallorente/manola/issues/24
- All issues use the `ready-for-agent` triage label and are written as AFK-ready slices.

## Tasks

### Completed design-completion pass

- Add a local UI server at `src/manola/ui_server.py`.
- Serve static frontend assets from `src/manola/ui_static/`.
- Add `uv run manola ui --host 127.0.0.1 --port 8765`.
- Implement meeting archive/list view using existing meeting metadata:
  - Date-bucketed meeting list.
  - Title/folder fallback, type, share status, language, duration, and selected-row state.
- Implement meeting detail tabs:
  - Overview with pipeline and disabled workflow actions.
  - Transcript with timestamp/speaker rows, raw fallback, model/device/compute/language context, health warnings, and disabled retranscribe action.
  - Report with readable sections, generation context, stale warning, empty state, and disabled regenerate action.
  - Audio with source/normalized artifacts, duration/file/size/sample-rate/channel details, missing-artifact warnings, and disabled repair action.
  - Metadata with core fields, attendees, model/profile details, `metadata.suggestions.json`, confidence/evidence detail, empty-value fallbacks, and disabled apply/save/accept/reject actions.
- Implement health detection for:
  - `audio/normalized.wav` shorter than original/recorded audio.
  - Transcript ending before source audio.
  - Report stale when transcript is newer than report.
- Implement Settings page with:
  - App language selector, stored in browser localStorage.
  - Highlight color picker, stored in browser localStorage.
  - Read-only display of existing Manola config for workspace, transcription, LLM, sharing, prompts, and advanced paths/defaults.
- Implement Devices page using existing `inspect_audio_devices`, with static readiness indicators and CLI alternatives for setup/testing.
- Implement Doctor page using existing `collect_doctor_checks`, with status counts and CLI alternatives for rerunning checks.
- Implement Import and Record pages as designed inert frontend states with explicit backend-gap notices, disabled actions, static meters/placeholders, pipeline previews, folder preview, and current CLI commands.
- Keep disabled enrich/export/repair/retranscribe/regenerate/apply actions visible with specific backend-gap explanations.

### Next backend tasks

- Add a long-running job API for `transcribe`, `summarize`, `enrich`, `export`, and repair flows.
- Add a recording job API with start/stop/progress/live level events.
- Add browser upload or desktop file-picker handoff for `import` and Google Recorder import.
- Add safe write endpoints for supported settings.
- Decide whether app language/highlight color stay browser-local or become Manola config fields.
- Add report-generation privacy confirmation state to the backend job model.

## Backend Gaps Not Implemented

- Recording from the UI: the current CLI flow is blocking and stop-key driven.
- Import/process from the UI: the current CLI accepts local filesystem paths, while browser UI cannot directly access arbitrary local paths.
- Repair audio from the UI: normalization exists, but no job endpoint tracks repair progress and follow-up transcription.
- Regenerate transcript/report from the UI: existing functions work, but the UI needs async job tracking and failure reporting before wiring them.
- Enrich/apply metadata suggestions from the UI: enrichment exists through the CLI, but the UI needs async job tracking and safe metadata write endpoints.
- Export from the UI: export exists through the CLI, but the UI needs a job endpoint and progress/failure reporting before wiring it.
- Google Recorder direct integration: v1 can design the import path, but no backend importer exists for Recorder transcript bundles or Google account access.

## Verification Status

- 2026-06-17: UI/server tests passed with `9 passed`.
- 2026-06-17: Full test suite passed with `98 passed`.
- 2026-06-18: Repaired the default `.venv` with `uv`-managed CPython 3.11.15. The documented full test command passed with `98 passed`, the UI/server subset passed with `9 passed`, and `uv run manola ui --host 127.0.0.1 --port 8765` served `/` and `/api/state` with HTTP 200.
- 2026-06-18: Design-completion UI/server subset passed with `21 passed`.
- 2026-06-18: Full test suite passed with `110 passed`.
- Current UI smoke command:

```powershell
uv run manola ui --host 127.0.0.1 --port 8765
```
