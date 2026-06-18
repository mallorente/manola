# Manola PRD: Intelligence and Future Vision

## Status

Proposed — 2026-06-18 — direction, not committed scope

## Summary

This PRD describes where Manola grows **after** the core local-first workflow
and the functional UI (`docs/PRD-UI-Functional-Completion.md`) are reliable. It
captures the intelligence layer: detecting meetings automatically, conversing
with meeting content, identifying speakers, taking notes live, ingesting
surrounding context, and helping the user stay organized across many meetings.

These are written as **epics**, not AFK-ready slices. Each states the problem,
a sketch, and the open questions that must be resolved before it becomes
implementation issues. They are tracked as `future` issues and are deliberately
**not** scheduled or labeled `ready-for-agent`.

## Cross-Cutting Principle: Local-First Privacy

Manola's defining promise is local-first handling of sensitive meeting data
(ADR-0001). Every epic below must preserve it:

- Recordings, transcripts, and ingested context stay on the local machine
  unless the user explicitly sends them out.
- Any feature that sends content to a remote LLM (chat, enrichment, context
  reasoning) must make that explicit, the same way report generation does.
- Local embedding/index/chat options should be preferred where feasible, and
  remote use must be opt-in and visible.

## Epics

### Epic F1 — Automatic meeting detection

A Granola-like background mode that watches for likely meetings and offers to
open one, rather than requiring the user to start recording manually.

- Sketch: a background watcher monitors mic/system activity (and later known
  meeting apps / calendar events); on a sustained two-sided audio pattern past a
  minimum duration, it prompts the user "This looks like a meeting — start
  recording?" The user confirms; Manola never records silently.
- Builds on: the recording job API (PRD Batch 4), the daemon design already
  sketched in `docs/PRD.md` (Automatic Meeting Detection).
- Open questions: foreground CLI vs. Windows startup task vs. tray app vs.
  desktop shell; how to persist watcher state; how to coordinate with manual
  `manola meet`; false-positive suppression; how the prompt surfaces when the UI
  is closed.

### Epic F2 — Chat with a meeting

Ask questions against a single meeting's transcript and report and get grounded
answers with citations back to transcript segments.

- Sketch: index a meeting's transcript (chunk + embed), retrieve relevant
  segments for a question, answer with a remote (or local) LLM, and cite the
  timestamped lines used.
- Open questions: local vs. remote embeddings and chat model; where the index
  lives (per-meeting artifact vs. a workspace store); citation format; how this
  reuses the LLM profile/prompt system; privacy disclosure UX.

### Epic F3 — Cross-meeting chat

Chat across a set of meetings — the last N meetings, a project, or the last N
days — to answer questions that span conversations ("what did we decide about
pricing this month?").

- Sketch: a workspace-level retrieval index over many meetings with scoping
  filters (project, date range, count); answers cite which meeting and segment
  each fact came from.
- Builds on: F2's per-meeting indexing generalized to a workspace store.
- Open questions: index storage and incremental update strategy; scoping UX;
  ranking across meetings; keeping the index local; cost controls for remote
  models.

### Epic F4 — Speaker identification

Move beyond anonymous diarization (`Speaker 1/2`, near-term Batch 5) to naming
speakers using attendee lists, voice profiles, and introductions.

- Sketch: diarization produces segments; identification maps segments to known
  attendees using user-provided names, recurring voice enrollment, and
  in-transcript self-introductions, always as suggestions the user confirms.
- Builds on: diarization (Batch 5), enrichment's attendee inference.
- Open questions: voice-enrollment storage and privacy; accuracy/confidence
  thresholds; how renames propagate to transcript/report; dependency and
  model-access constraints (e.g. `pyannote`).

### Epic F5 — Live note-taking during recording

Let the user jot notes while a meeting records, anchored to the timeline and
woven into the final report.

- Sketch: a notes pane in the Record screen captures timestamped user notes;
  notes persist alongside `live_transcript.md` and are passed to report
  generation as first-class user input ("user notes" section / steering).
- Builds on: the recording job API and live transcript (PRD Batch 4).
- Open questions: note storage format and timeline anchoring; how notes
  influence the report prompt; conflict handling if notes contradict the
  transcript; editing notes after the meeting.

### Epic F6 — Context ingestion

Attach surrounding context — documents, emails, Slack/Teams messages — to a
meeting so reports and chat can reason over more than the transcript.

- Sketch: a meeting can hold attached context artifacts; the user adds files or
  connects sources; context feeds enrichment, report generation, and chat.
- Open questions (privacy-heavy): which sources first and how connectors
  authenticate; where attached context is stored (local artifact vs. linked);
  strict local-first boundaries when sending context to remote LLMs; redaction;
  how context is scoped per meeting vs. per project.

### Epic F7 — Organizational assistant

Help the user stay organized across conversations: detect documents mentioned in
meetings and ask the user to provide them, maintain a global TODO derived from
action items across meetings, and propose organization based on what was
discussed.

- Sketch: a workspace-level assistant aggregates action items and references
  across meetings; surfaces "you mentioned a spec that isn't attached — add it?",
  a consolidated cross-meeting TODO list, and organization suggestions
  (projects, follow-ups).
- Builds on: enrichment, cross-meeting retrieval (F3), context ingestion (F6).
- Open questions: how action items are normalized and deduplicated across
  meetings; TODO state/ownership model; how aggressive the proactive prompts
  should be; surfacing in UI vs. notifications.

## Sequencing Notes

These epics are not independent. A pragmatic dependency order, once near-term
work lands:

1. F1 (auto-detection) — extends the recording work directly.
2. F2 → F3 (single-meeting chat, then cross-meeting) — shared retrieval
   infrastructure.
3. F4 (speaker identification) — after diarization.
4. F5 (live notes) — extends recording.
5. F6 → F7 (context ingestion, then the organizational assistant) — the
   assistant depends on both cross-meeting retrieval and context.

None should start before the functional-UI PRD is complete, because they all
assume a UI a non-technical user can actually operate.

## Related

- `docs/PRD.md` — base product requirements; existing Post-MVP Roadmap.
- `docs/PRD-UI-Functional-Completion.md` — the prerequisite functional UI.
- `docs/ADR-0001-local-first-cli.md` — the local-first privacy stance these
  epics must preserve.
