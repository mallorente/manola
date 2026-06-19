# Manola PRD: UI Functional Completion for Non-Technical Users

## Status

Proposed — 2026-06-18

## Summary

The Manola local web UI (`uv run manola ui`) currently renders a complete,
desktop-class shell, but most of it is **inert**: archive, transcript, report,
audio, metadata, devices, doctor, and settings screens read real backend data,
while every action button (retranscribe, regenerate report, enrich/apply,
export, repair, settings writes, record, import) is disabled and falls back to a
"run this CLI command" notice.

This PRD covers the work to make the UI **fully usable by a non-technical user
with no terminal access**. The guiding constraint is simple:

> Every "use `uv run manola ...`" notice in the UI is a bug, not a gap.

A non-technical user must be able to get audio in, produce a transcript and a
report, fix problems, adjust settings, and manage devices — without ever
opening a terminal.

## Goals

- Make every visible UI action actually work, backed by a real endpoint.
- Add an async job model so long-running actions (transcribe, summarize,
  enrich, export, repair, record) report progress and failure honestly.
- Let the user record a meeting and import an audio file from the UI.
- Let the user change settings and configure devices from the UI.
- Generate meaningful meeting titles instead of `Recording HH:MM`.
- Keep the implementation simple: no new web framework, no frontend build
  system, no streaming transport until live meters require it.

## Non-Goals

- Replacing the CLI. The CLI remains a first-class surface and the source of
  truth for scripted/advanced use.
- Migrating to FastAPI/uvicorn or a SPA build pipeline.
- Intelligence features (chat with a meeting, auto-detection, context
  ingestion). Those live in `docs/PRD-Future-Vision.md`.
- Diarization, VAD pause/resume, and production voice enhancement. Those are
  near-term capability work tracked separately (Batch 5 milestone) and already
  described in `docs/PRD.md`.

## Architecture

The async job model is specified in `docs/ADR-0003-ui-job-model.md`:

- An in-process `JobRegistry` inside the existing `ThreadingHTTPServer`.
- `POST /api/jobs/<action>` starts a job on a worker thread that calls existing
  pipeline functions; `GET /api/jobs/<id>` returns status/progress/result.
- A single-worker queue serializes GPU-bound jobs (transcription) so concurrent
  CUDA runs cannot fight over VRAM. Lightweight jobs (export, remote-LLM
  enrich/summarize) may run concurrently.
- The job model carries a privacy-confirmation flag: jobs that send the
  transcript to a remote LLM (summarize, enrich, regenerate) do not start until
  the UI confirms, mirroring the CLI's explicit LLM privacy notice.
- The frontend polls job status (~1s) and renders running/progress/done/failed
  states. No SSE until Batch 4 live meters.

## Batches and Human-Check Gates

Work is released in dependency-ordered batches. Each batch is a GitHub
Milestone with a tracking issue that holds the human-check checklist. Only the
active batch's issues carry `ready-for-agent`; later batches stay parked until
the human gate opens.

Every gate verifies: (a) `uv run manola ui --host 127.0.0.1 --port 8765` serves
cleanly, (b) the batch-specific things to click/eyeball below, (c) the full
test suite is green.

### Batch 1 — Cosmetic and read-only correctness

No backend dependencies. Trivially verifiable by eye.

1. **Dark-mode audit and fixes.** Review every screen in dark mode and fix
   contrast/color failures.
   - Acceptance: each screen (archive, overview, transcript, report, audio,
     metadata, settings, devices, doctor, record, import) is legible in dark
     mode with no light-on-light or dark-on-dark regions; a short list of fixed
     spots is recorded in the PR.
2. **Settings icon alignment.** The settings (gear) icon's center circle is
   misaligned.
   - Acceptance: the gear renders pixel-centered at the sizes used in the nav.
3. **Selectable meeting-list sorting.** The archive list sort is currently
   fixed.
   - Acceptance: the user can sort the archive by date, title, type, and
     duration, ascending or descending; the choice persists in localStorage.
4. **Meaningful LLM titles for new meetings.** New meetings fall back to
   `Recording HH:MM`. Enrichment already produces `suggested_title`.
   - Acceptance: when enrichment runs for a new meeting, a high-confidence
     `suggested_title` is used as the meeting title (and folder topic) instead
     of the generic fallback; the generic fallback remains when enrichment is
     disabled or confidence is low. No extra LLM call beyond the existing
     enrichment pass. Retroactive re-titling of existing meetings is Batch 3.

### Batch 2 — Job-API keystone

Depends on Batch 1 merged. This is the foundation every later action sits on.

1. **ADR-0003 job model + JobRegistry + endpoints.** Implement the in-process
   registry, `POST /api/jobs/<action>`, `GET /api/jobs/<id>`, the single-GPU
   worker queue, and the privacy-confirmation flag.
   - Acceptance: jobs can be started, polled, and report
     `queued/running/done/failed` with a human-readable step and error; GPU
     jobs serialize; tests cover the registry state machine and the privacy
     gate.
2. **Retranscribe wired end-to-end (tracer bullet) + reusable frontend job
   component.** Wire the disabled "Retranscribe" action through the full new
   stack and build the reusable polling/progress UI component the later actions
   will reuse.
   - Acceptance: from the UI, a user clicks Retranscribe, sees live progress,
     and the transcript updates on completion; failure surfaces a clear error;
     the same frontend component is reused by Batch 3 actions.

### Batch 3 — Wire the remaining actions

Depends on Batch 2. Each reuses the job API and frontend component.

1. **Regenerate report** (with privacy confirmation).
2. **Enrich + apply metadata suggestions.** Safe write endpoints for confirmed
   suggestions, including retroactive re-title with folder rename. Raw
   `transcript.md` and existing metadata are never silently overwritten;
   applying updates `metadata.json` only with confirmed/high-confidence values.
3. **Export from UI** with a share-policy picker
   (`private/report/report_transcript/all`).
4. **Settings writes.** Whitelisted fields only, via the existing
   `update_config_value`: workspace dir, shared dir, default language, default
   LLM profile, default share policy, Whisper model/device/compute, mic/speaker
   index. Secrets are never written from the UI.
5. **Device selection + save.** Reuse `audio setup` logic to pick and persist
   `default_mic_index` / `default_speaker_index`.
6. **Repair-audio action.** Re-normalize and re-transcribe from a health
   warning, tracked as a job.
   - Gate acceptance: every previously disabled archive/detail/settings/devices
     action is now clickable and works; no CLI-fallback notice remains for these
     actions.

### Batch 4 — Get audio in without a terminal

Depends on Batch 3. Removes the last reasons a non-technical user needs a
terminal.

1. **Recording job API + Record screen.** Start/stop/progress for meeting
   capture driven from the UI rather than the blocking stop-key CLI flow.
2. **Live level meters + live transcript in the UI.** Real mic/system RMS meters
   and incremental preview transcript while recording. This is where SSE (or
   chunked polling) for level events is introduced, scoped to recording
   endpoints only.
3. **Import via browser upload / desktop file-picker handoff.** Let the user
   bring in an `.m4a`/`.mp3`/`.wav`/`.mp4` file from the UI and run the import
   pipeline.
4. **Remove CLI escape-hatch notices.** Delete the now-obsolete "run this CLI
   command" fallbacks and `backend_gaps()` entries that have been closed.
   - Gate acceptance: a non-technical user completes record → transcript →
     report and import → transcript → report entirely in the browser; the UI no
     longer instructs the user to open a terminal.

## Acceptance Criteria for the PRD

- The UI has no disabled action that lacks a working backend.
- No screen instructs the user to run a CLI command to complete a core task.
- Long-running actions report honest progress and failures via the job model.
- A non-technical user can record, import, transcribe, summarize, enrich,
  export, repair, change settings, and configure devices from the browser.
- The CLI continues to work unchanged.
- The full test suite remains green at every gate.

## Related

- `docs/ADR-0003-ui-job-model.md` — the async job model.
- `docs/UI_PLAN.md` — the original UI direction and the backend gaps this PRD
  closes.
- `docs/PRD.md` — base product requirements and near-term capability work.
- `docs/PRD-Future-Vision.md` — intelligence features beyond UI completion.
