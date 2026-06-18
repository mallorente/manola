# AGENTS.md

## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `mallorente/manola`. See `docs/agents/issue-tracker.md`.

### Triage labels

The repo uses the default triage label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo using the root project docs and ADRs under `docs/`. See `docs/agents/domain.md`.

## Project

Manola is a local-first meeting recorder, transcriber, and report generator.

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
uv run manola doctor
uv run manola --help
```

Do not assume `manola` is installed globally.

## Repo Structure

```text
src/manola/
  cli.py              Typer commands
  pipeline.py         import/process/transcribe/summarize orchestration
  audio.py            FFmpeg normalization and audio import
  audio_recording.py  soundcard-based recording spike and record helpers
  transcription.py    local/remote transcription
  transcribe_worker.py CUDA worker process
  reporting.py        LLM report generation and fallback reports
  exporting.py        shared-folder export policies
  config.py           ~/.manola config/secrets
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
uv run manola audio doctor
uv run manola audio test --source mic --duration 10
uv run manola audio test --source system --duration 10
uv run manola audio test --source meeting --duration 10
```

System loopback and meeting capture have been verified with non-zero RMS.

## Documentation

Update `docs/PRD.md` for product requirements.

Use ADRs for durable technical decisions:

- ADR = Architecture Decision Record.
- PRD says what the product should do.
- ADR says why a technical approach was chosen and what tradeoffs it creates.

Update `docs/STATUS.md` after meaningful implementation milestones so future sessions can resume quickly.

## Roadmap and Batched Delivery

Active product work is planned in two PRDs and delivered in dependency-ordered
batches with human-check gates. Future sessions should follow this workflow
rather than inventing a new plan.

Planning sources:

- `docs/PRD-UI-Functional-Completion.md` — Batches 1–4: make the web UI fully
  usable by a non-technical user with no terminal. Backed by
  `docs/ADR-0003-ui-job-model.md` (in-process job registry + polling, single-GPU
  queue, remote-LLM privacy gate).
- `docs/PRD-Future-Vision.md` — epics F1–F7 (intelligence layer). Not yet
  agent-ready; open questions must be resolved before any becomes
  `ready-for-agent`.
- GitHub Issues in `mallorente/manola` are the live tracker (see
  `docs/agents/issue-tracker.md`). PRDs are #58 (UI completion) and #59 (future
  vision).

How batches and gates work:

- Each batch is a GitHub **Milestone** (`Batch 1 · …` through `Batch 5 · …`)
  with one **tracking issue** (#53–#57) that holds the human-check checklist.
- Only the **active** batch's issues carry `ready-for-agent`. Later batches stay
  `needs-triage` until their gate opens. Tracking issues carry
  `ready-for-human`.

How to proceed in a session:

1. Find the active batch: the milestone whose implementation issues are labeled
   `ready-for-agent`. Work only those issues. (Batch 1 = #26–#29 at publish
   time.)
2. Do not start a later batch's issues, and do not start any `future` epic
   (#46–#52). If the active batch is fully merged, stop and let the human run
   the gate — do not self-promote the next batch.
3. When the human confirms a batch's tracking-issue checklist passes, flip the
   next milestone's implementation issues from `needs-triage` to
   `ready-for-agent` (e.g. `gh issue edit <n> --add-label ready-for-agent
   --remove-label needs-triage`), then comment on its tracking issue that the
   gate is open.
4. Batch 5 (near-term capability, #42–#45) is independent of the UI chain and
   can be scheduled at any time.
5. Keep `docs/STATUS.md` updated as batches land.

Note: `gh issue list --label …` can panic on this Windows host (keyring bug).
Use the REST path instead, e.g.
`gh api "repos/mallorente/manola/issues?labels=ready-for-agent&state=open"`.
