# ADR-0003: UI Async Job Model

## Status

Proposed

## Context

The Manola web UI (`uv run manola ui`) is served by a stdlib
`http.server.ThreadingHTTPServer` in `src/manola/ui_server.py`. Today it only
handles `GET` requests and renders read-only state. Every long-running action
the UI needs — retranscribe, regenerate report, enrich, apply suggestions,
export, repair, and eventually record and import — is disabled and falls back to
a CLI command.

To make the UI usable by non-technical users (see
`docs/PRD-UI-Functional-Completion.md`), these actions must run from the browser
and report progress and failure honestly. Several constraints shape the
decision:

- The UI deliberately avoids a frontend build system and extra runtime
  dependencies (`docs/UI_PLAN.md`).
- The CLI, not the UI, is the source of truth (ADR-0001). The UI is a second
  surface over the same backend functions.
- CUDA transcription is GPU-bound and already isolated in a subprocess worker
  (`transcribe_worker.py`) because CTranslate2 can abort on CUDA cleanup on
  Windows. Concurrent GPU transcriptions would contend for VRAM.
- Report generation and enrichment send the transcript to a remote LLM. The CLI
  makes this privacy cost explicit; the UI must do the same.

Options considered:

1. **In-process job registry + polling.** A thread-backed registry inside the
   existing server; the frontend polls job status.
2. **In-process registry + Server-Sent Events.** Same registry, but progress is
   pushed over SSE.
3. **Adopt FastAPI/uvicorn (+ background tasks or a task queue).**

## Decision

Adopt **option 1: an in-process job registry with polling**, with a seam to add
streaming later only where it pays off.

- A `JobRegistry` holds `job_id -> Job` records guarded by a lock. A `Job`
  carries `action`, `status` (`queued`/`running`/`done`/`failed`), `progress`,
  a human-readable `step`, `result`, and `error`.
- `POST /api/jobs/<action>` validates input, creates a job, and dispatches it to
  a worker thread that calls the existing pipeline functions
  (`transcribe_meeting`, `summarize`, `enrich_meeting`, `export`, repair). CUDA
  transcription continues to run through the existing subprocess worker; the job
  thread waits on it.
- `GET /api/jobs/<id>` returns the current job record. The frontend polls
  (~1s) and renders running/progress/done/failed states with a single reusable
  component.
- **Concurrency policy:** a single-worker queue serializes GPU-bound jobs
  (transcription) so only one CUDA run happens at a time. Lightweight jobs
  (export, remote-LLM summarize/enrich) may run concurrently.
- **Privacy gate:** jobs that send transcript content to a remote LLM
  (`summarize`, `enrich`, `regenerate`) do not start until the request carries
  an explicit confirmation flag. This mirrors the CLI's LLM privacy notice.
- **Streaming seam:** live audio meters and live transcript during recording
  (PRD Batch 4) are the only cases that benefit from push. SSE (or chunked
  polling) is introduced then, scoped to recording endpoints only — not as a
  general transport.

## Rationale

Polling fits the work that exists now: fire-and-forget jobs whose UX is
"running → progress → done/failed." It adds no dependencies, keeps the stdlib
server, and respects the no-build-system direction.

SSE only pays off for live recording meters, which arrive in a later, larger
batch (the CLI recording flow is blocking and stop-key driven today). Paying the
streaming-complexity tax in the foundation would buy nothing until then.

FastAPI is the right choice only if the UI becomes the primary product surface,
which contradicts ADR-0001's CLI-first stance. That is a strategic bet not yet
made; if it is made later, it warrants its own ADR and migration epic. It is not
a prerequisite for making the current buttons work.

Serializing GPU jobs avoids VRAM contention and respects the existing
single-subprocess CUDA design.

## Consequences

Positive:

- No new runtime dependencies; the stdlib server stays.
- Reuses existing pipeline functions and the CUDA subprocess worker unchanged.
- Honest, testable progress/failure states.
- Clear upgrade path: add SSE for recording, or migrate to a framework later,
  without rewriting the job semantics.

Tradeoffs:

- Polling has ~1s latency granularity; acceptable for batch jobs, not ideal for
  smooth live meters (hence the Batch 4 streaming seam).
- The registry is in-process and non-persistent: jobs do not survive a server
  restart. Acceptable for a local single-user tool; revisit if the UI gains a
  daemon mode.
- Single-GPU-worker queue means a second transcription waits behind the first.

## Related Decisions

- ADR-0001 — local-first CLI; the UI is a second surface over the same backend.
- ADR-0002 — Windows recording spike; the recording job API builds on it.
- `docs/PRD-UI-Functional-Completion.md` — the product work this enables.
