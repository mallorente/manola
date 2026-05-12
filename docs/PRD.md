# Manola PRD

## Summary

Manola is a local-first meeting recorder, transcriber, and report generator inspired by Granola. It starts as a CLI-first product that can process existing recordings, especially mobile `.m4a` files, and later grows into a cross-platform desktop app.

The first useful workflow is:

```text
audio recording -> normalized audio -> transcript -> meeting report -> local archive -> optional shared folder export
```

## Goals

- Import existing recordings from mobile or other tools.
- Record meetings locally on Windows as a beta capability after a technical spike.
- Transcribe with local Whisper by default, using GPU when available.
- Support remote transcription from the beginning through a configurable Whisper-compatible endpoint.
- Generate structured meeting reports with a remote LLM.
- Name meetings, capture attendees, and propose folders automatically.
- Archive privately by default and optionally export reports to a synced team folder.
- Keep the core workflow cross-platform-ready for Windows, Linux, and macOS.

## Non-Goals For MVP

- Full desktop UI.
- Native macOS system-audio recording.
- Perfect speaker identification.
- Gmail as a document repository.
- Dropbox support.
- Local LLM summarization.
- Hosted SaaS workspace.
- Voice enhancement / denoising as a default processing step.

## Target Platforms

### Phase 1

- Windows first.
- Import `.m4a`, `.mp3`, `.wav`, and `.mp4`.
- CLI-first implementation.
- Windows meeting recording as beta after an audio spike.
- Linux architecture supported, with import/transcription prioritized before full capture.

### Phase 2

- macOS support.
- macOS import/transcription first.
- macOS system-audio capture with setup instructions for external audio routing where needed.
- Desktop UI on top of the existing CLI/backend services.

## Core Workflows

### Process Existing Recording

```text
manola process recording.m4a
```

If only an audio path is provided and the terminal is interactive, Manola enters compact interactive mode.

Prompts:

```text
Meeting type [general]:
Project [none]:
Language [auto/es/en]:
Title [auto]:
Attendees, comma-separated [none]:
Transcription backend [local/remote]:
LLM profile [deepseek_fast]:
Share policy [private/report/report_transcript/all]:
```

When running in a non-interactive context, Manola uses defaults.

### Process With Flags

```text
manola process recording.m4a \
  --type job_interview \
  --project hiring-2026 \
  --language en \
  --attendee "Ana Garcia" \
  --attendee "Carlos Perez" \
  --share report
```

The command:

1. Copies the original audio into the local workspace.
2. Normalizes audio with FFmpeg.
3. Transcribes.
4. Optionally diarizes.
5. Generates metadata.
6. Generates `report.md`.
7. Creates or proposes the archive folder.
8. Exports according to the share policy.

### Record Meeting

The user-facing recording workflow is "record a meeting", not "record a source".

```text
manola meet
manola record
```

`manola meet` is the simple default command for non-technical usage. It should:

- Use the default microphone and default system output/loopback.
- Record meeting audio.
- Normalize the recording.
- Transcribe with the configured default local Whisper model/device.
- Generate a report with the configured default LLM profile unless disabled, clearly warning that the transcript will be sent to the remote LLM.
- Generate metadata suggestions from the transcript with the configured default LLM profile unless enrichment or LLM usage is disabled.
- Export only when a non-private share policy is supplied.
- Print the defaults it is about to use, the local output paths, and the flags for changing them.
- Continue until the stop key is pressed or system audio has been silent for the configured timeout.
- Prefer device indices from `manola devices` when multiple devices share the same display name.

Default behavior:

- Capture microphone.
- Capture system audio.
- Save recording directly inside the local meeting archive as `audio/recorded.wav`.
- Normalize recording to `audio/normalized.wav`.
- Show a live transcript preview while recording by default, with an option to disable it.
- For `meet`, process immediately after recording stops.

Advanced/debug options can expose individual sources:

```text
manola record --source mic
manola record --source system
manola record --source meeting
manola meet --mic-index 1 --speaker-index 3
manola record --mic "<name>" --speaker "<name>"
manola meet --stop-key q --pause-after-silence 10 --silence-timeout 30
manola meet --duration 3600
manola meet --no-enrich
manola record --live-transcript
manola record --duration 30 --source meeting --process
```

`record --no-process` creates a local meeting archive with recorded audio, normalized audio, metadata, and placeholder report/transcript files. `record --process` additionally transcribes and optionally summarizes/exports according to the supplied flags.

For meeting capture, Manola should report separate microphone and system RMS when available. If system audio appears silent during meeting capture, Manola should warn clearly because the resulting transcript may miss the remote side of the call.

If meeting recording cannot capture both microphone and system audio, it must not continue silently. It should ask for explicit confirmation or fail.

Auto-stop behavior should support pause/resume rather than only a hard stop: pause after X seconds of mic/system inactivity, resume recording when microphone or system audio becomes active again, and stop after Y seconds of continued inactivity.

### Live Transcript While Recording

Manola should support a live transcript mode for recorded meetings:

```text
manola record --live-transcript
```

Live transcript behavior:

- Capture meeting audio and write the canonical recording locally as usual.
- Transcribe short audio windows during recording, for example 10-30 seconds at a time.
- Use a small overlap between windows and suppress duplicate preview lines around chunk boundaries.
- Show incremental transcript text in the terminal while the meeting is happening.
- Persist the live preview to the meeting folder as `live_transcript.md`.
- Mark live transcript output as preview quality.
- Continue recording even if live transcription fails, unless recording itself fails.
- After recording stops, run the normal final transcription pipeline over the complete recording.
- Treat final `transcript.md` as canonical for reports, exports, and metadata.

Live transcript is a user-facing convenience, not the source of truth. It may contain imperfect timestamps or partial sentences. The final transcription pass is responsible for producing the clean transcript used by report generation.

## Audio Handling

Supported imports for MVP:

- `.m4a`
- `.mp3`
- `.wav`
- `.mp4`

FFmpeg is a required dependency.

Imported recordings are stored as:

```text
audio/
  original.m4a
  normalized.wav
```

Recordings made by Manola are stored as WAV in MVP:

```text
audio/
  recorded.wav
  normalized.wav
```

Future versions may add compressed archive formats such as `.m4a` or `.opus`.

## Voice Enhancement V2

Manola should support optional voice enhancement for noisy recordings in a future version. The goal is to improve transcript fidelity when the input contains room noise, fan noise, low voice volume, echo, compression artifacts, or mixed meeting audio where speech is not prominent enough.

Voice enhancement should never overwrite the original recording. It should create an additional audio artifact:

```text
audio/
  original.m4a
  normalized.wav
  enhanced.wav
```

For recordings made by Manola:

```text
audio/
  recorded.wav
  normalized.wav
  enhanced.wav
```

Potential CLI:

```text
manola process recording.m4a --enhance-voice
manola process recording.m4a --enhance-voice light
manola process recording.m4a --enhance-voice denoise
manola record --process --enhance-voice
manola audio enhance-test <meeting-id-or-audio-path>
```

Enhancement modes:

- `off`: default behavior for MVP.
- `light`: conservative filtering and loudness normalization.
- `denoise`: stronger noise reduction for noisy audio.
- `speech`: speech-focused enhancement, potentially using ML models.

Initial implementation candidates:

- FFmpeg filters such as `highpass`, `lowpass`, `afftdn`, `loudnorm`, and `dynaudnorm`.
- RNNoise-style denoising.
- DeepFilterNet.
- Demucs or other source-separation models when speech isolation is needed.

Evaluation workflow:

```text
baseline normalized audio -> baseline transcript
enhanced audio -> enhanced transcript
compare transcript fidelity, artifacts, processing time, and report quality
```

Manola should keep both transcripts during evaluation:

```text
transcript.baseline.md
transcript.enhanced.md
```

The first evaluation sample should be the existing recording:

```text
C:\Users\Usuario\OneDrive\Documentos\Grabaciones de sonido\GrabaciÃ³n (38).m4a
```

Acceptance criteria for enabling voice enhancement outside experiments:

- Enhancement improves or preserves transcript fidelity on representative noisy samples.
- Enhancement does not remove quiet speech.
- Enhancement does not introduce artifacts that make Whisper hallucinate more.
- The user can compare baseline and enhanced outputs before making enhancement the default for a workflow.
- Original audio is always preserved.

## Transcription

Local transcription backend:

- `faster-whisper`.
- Selectable model.
- Use GPU/CUDA if available.
- Fall back to CPU when needed.
- Support pre-downloaded local model folders to avoid repeated model downloads.
- Support chunked transcription for long recordings.
- Store the Whisper model, device, and compute type used for each transcript in `metadata.json`, `transcript.md`, and `report.md`.

Quality guidance:

- `base` is suitable only for fast smoke tests and rough drafts.
- `large-v3` is the preferred quality model for faithful transcripts.
- `turbo` may be used when speed matters more than maximum accuracy.
- For short or mixed-language recordings, explicit `--language es` or `--language en` is preferred over `auto` when the language is known.

Remote transcription backend:

- Configurable Whisper-compatible endpoint from the beginning.

Supported language modes:

- `auto`
- `es`
- `en`

Example:

```text
manola process meeting.m4a --language en
```

For recorded meetings with live transcript enabled:

- `live_transcript.md` is updated incrementally during recording.
- `transcript.md` is generated after recording from the complete normalized audio.
- Reports are generated from `transcript.md`, not from `live_transcript.md`.

## Speaker Diarization

Diarization is optional and best-effort.

MVP behavior:

- Transcript works without diarization.
- If enabled and configured, segments can be labeled as `Speaker 1`, `Speaker 2`, etc.
- Speakers can be renamed manually later.
- Attendee names provided by the user help metadata and reporting but are not treated as guaranteed automatic speaker matches.

Potential backend:

- Optional `pyannote.audio` extra, subject to dependency and model-access constraints.

## Meeting Types

Manola uses meeting types to choose report templates.

Initial types:

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

`general` is the fallback.

### Job Interview Report

Sections:

- Recommendation
- Candidate profile
- Motivation
- Relevant experience
- Strong signals
- Weak signals
- Risks / doubts
- Fit with role
- Follow-up questions
- Next steps

### Case Interview Report

Sections:

- Recommendation
- Case context
- Reasoning structure
- Analysis quality
- Use of data and assumptions
- Communication
- Response to questions
- Strong signals
- Weak signals
- Risks / doubts
- Next steps

### Operational And Product Reports

Manola should provide specialized report sections and prompts for common non-hiring meeting workflows:

- Sales discovery: customer context, pain points, decision criteria, stakeholders, objections, next steps.
- Sales demo: customer goals, features covered, reactions, questions, fit assessment, follow-up.
- Customer success: account health, goals, risks, requests, renewal or expansion signals, next steps.
- Client update: progress, decisions, risks, client feedback, commitments, next steps.
- Internal sync: team updates, decisions, blockers, dependencies, actions.
- One-on-one: topics, feedback, support needed, growth, follow-up.
- Project review: status, milestones, scope/timeline/budget, risks, decisions, actions.
- Incident postmortem: impact, timeline, root cause, what worked, what failed, corrective actions.
- Brainstorm: goal, ideas, themes, promising directions, constraints, next experiments.
- Strategy: context, options, tradeoffs, decisions, risks, open questions.
- Workshop: goal, activities, outputs, decisions, action items.
- Refinement: reviewed items, clarifications, acceptance criteria, dependencies, risks.
- Daily: progress, today, blockers, dependencies, risks, action items.
- Retro: what went well, what did not, learnings, improvement actions.
- Planning: goal, scope, priorities, capacity, risks, decisions, next steps.

## Reports

Markdown is the canonical MVP output format.

Example:

```markdown
# Meeting title

Date: 2026-05-07
Type: job_interview
Project: hiring-2026
Attendees: Ana Garcia, Carlos Perez
Language: en
Audio: audio/original.m4a
Transcript: transcript.md

## Summary

## Key Points

## Decisions

## Action Items

## Open Questions

## Notes by Topic
```

Each meeting folder contains:

```text
metadata.json
report.md
transcript.md
audio/
  original.m4a
  normalized.wav
```

If live transcript was enabled during recording, the folder also contains:

```text
live_transcript.md
```

## Naming And Folder Suggestions

Meeting folders use a stable human-readable format:

```text
YYYY-MM-DD__meeting-type__main-person-or-company-or-topic
YYYY-MM-DD__meeting-type__main-person-or-company__short-topic
```

Examples:

```text
2026-05-07__job-interview__ana-garcia__backend-role
2026-05-07__case-interview__luis-perez__pricing-case
2026-05-07__sales-discovery__acme__expansion
2026-05-08__general__recording-22-10
```

`project` is an explicit optional metadata field.

If a project is set:

```text
Meetings/
  Projects/
    manola/
      2026-05-07__job-interview__ana-garcia__backend-role/
```

If no project is set:

```text
Meetings/
  2026-05-08__general__recording-22-10/
```

The user can override proposed names and folders.

## Sharing

Manola shares through a configurable local synced folder, not through Gmail.

The local meeting archive is always complete by default. At minimum, each processed meeting keeps metadata, audio, transcript, and report inside the private local workspace. The share policy only controls what is copied to the configured synced folder.

Supported folder sync targets:

- Google Drive for Desktop.
- OneDrive.
- iCloud Drive in macOS Phase 2.
- Any local company-shared folder.

Share policies:

- `private`: nothing exported.
- `report`: only `report.md`.
- `report_transcript`: `report.md` and `transcript.md`.
- `all`: report, transcript, and audio.

Default share policy:

- `private` unless explicitly configured otherwise or passed as a flag.

## LLM Summary Backend

Report generation uses a remote LLM through an OpenAI-compatible abstraction.

Default profile:

- `deepseek_fast`
- Base URL: `https://opencode.ai/zen/go/v1`
- Model: `deepseek-v4-flash`
- Thinking: disabled
- Report temperature: `0.2`
- Enrichment temperature: `0.0`

Optional profiles:

- `gemini_fast` using `google/gemini-2.5-flash-lite` through OpenRouter for a cheap, fast alternate summarizer.
- `sonnet_4_6` using `anthropic/claude-sonnet-4.6` through OpenRouter for high-quality reports.
- OpenAI fallback using `gpt-4.1-mini`.

LLM temperature policy:

- `temperature` controls narrative report generation in `report.md`.
- `enrichment_temperature` controls structured metadata extraction for `metadata.suggestions.json`.
- Enrichment should default to `0.0` because Manola wants conservative, repeatable JSON extraction rather than creative guesses.
- Report generation should stay low-temperature by default because meeting reports should prioritize fidelity, consistency, and evidence over stylistic variety.
- `sonnet_4_6` may use a slightly higher report temperature than smaller/cheaper profiles to allow more polished synthesis while remaining grounded.

## Configuration

Configuration lives in the user profile, not in synced meeting folders.

```text
~/.manola/config.toml
~/.manola/secrets.toml
```

Secret resolution priority:

1. Environment variables.
2. `~/.manola/secrets.toml`.
3. Clear error message with setup instructions.

Secrets must never be stored in meeting metadata or shared folders.

## Post-MVP Roadmap

These features are not required for the MVP, but they describe the direction Manola should grow after the core local-first workflow is reliable.

### Customizable Prompts

Manola should move report-generation prompts out of hard-coded Python strings so the user can tune prompts per model, language, and meeting type without changing application code.

Default prompts should ship with the application, for example:

```text
src/manola/prompts/defaults/
  system.md
  general.md
  job_interview.md
  case_interview.md
  models/
    deepseek_fast/
      system.md
      general.md
      enrich.md
    gemini_fast/
      system.md
      general.md
      enrich.md
    sonnet_4_6/
      system.md
      general.md
      enrich.md
```

User overrides should live in the Manola profile:

```text
~/.manola/prompts/
  system.md
  general.md
  job_interview.md
  case_interview.md
  models/
    sonnet_4_6/
      general.md
```

Potential CLI:

```text
manola prompts list
manola prompts show general
manola prompts show general --llm-profile sonnet_4_6
manola prompts edit general
manola prompts reset general
```

Requirements:

- Built-in defaults must keep working when no user prompt files exist.
- User prompts may override specific meeting types without copying every default prompt.
- Profile-specific prompts should resolve before global prompts using this order: user profile prompt, user global prompt, built-in profile prompt, built-in global prompt.
- Default prompt frameworks should be tuned to each profile: RTF for `deepseek_fast`, compact COSTAR for `gemini_fast`, and RISEN/CREA for `sonnet_4_6`.
- Prompt rendering should receive structured metadata, transcript text, report sections, language, model/profile name, and transcription details.
- Prompt files must not contain secrets.
- Prompt changes should be reflected in new report generation without requiring reinstalling Manola.
- Generated reports should record the prompt profile or prompt file version/hash when practical, so output can be traced later.

### Transcript Enrichment Pass

Manola should support a second LLM-assisted pass over the canonical transcript to improve meeting metadata and suggest corrections.

The first Whisper transcript remains the source of truth:

```text
transcript.md
```

The enrichment pass may create additional artifacts:

```text
transcript.enriched.md
metadata.suggestions.json
```

Potential CLI:

```text
manola enrich <meeting-id>
manola enrich <meeting-id> --apply
manola process recording.m4a --enrich
manola meet --enrich
```

The enrichment pass should propose:

- Attendee names inferred from introductions, greetings, or calendar context.
- Corrections for recurring misrecognized names, companies, products, and domain terms.
- A better meeting title.
- A likely meeting type.
- A short topic slug for folder naming.
- Ambiguous or low-confidence items for user review.

Requirements:

- The raw `transcript.md` must not be silently overwritten.
- Suggestions must distinguish evidence-backed corrections from guesses.
- Applying suggestions should update `metadata.json` only with confirmed or high-confidence values.
- If an enriched transcript is generated, reports may optionally use it, but the report should state whether it used raw or enriched transcript input.
- The user should be able to review suggestions before applying them.

### Calendar-Assisted Naming

Manola should optionally connect to calendar data to improve meeting names, attendees, projects, and metadata.

Initial calendar support should be read-only and should never be required for recording or processing.

Potential CLI:

```text
manola calendar connect
manola calendar status
manola calendar suggest <meeting-id>
manola process recording.m4a --calendar
manola meet --calendar
```

Matching logic should consider:

- Recording start/end time.
- Nearby calendar events.
- Event title.
- Attendee list.
- Meeting URL/provider when available.
- User-provided project or meeting type flags.

Requirements:

- Calendar access must be optional and explicit.
- Calendar credentials must live in the Manola profile/secrets area, never in meeting folders.
- Manola should work fully offline when calendar data is unavailable.
- Calendar-derived metadata should be treated as suggestions unless confidence is high.
- Calendar event titles and attendees should help naming, but should not force folder names without user override options.
- Future desktop UI and TUI should be able to surface calendar suggestions before applying them.

### Terminal Meeting Browser

Manola should provide a terminal user interface (TUI) so the user can browse and manage meetings without a desktop GUI or file explorer.

Potential CLI:

```text
manola browse
manola tui
```

The TUI should support:

- Listing meetings by date, project, type, title, and share status.
- Opening a meeting detail view.
- Previewing `report.md`, `transcript.md`, and metadata.
- Searching meeting titles, metadata, transcript text, and report text.
- Re-running actions such as summarize, transcribe with `--force`, enrich, and export.
- Editing safe metadata fields such as title, attendees, project, meeting type, and share policy.
- Showing local artifact paths without requiring the user to open a GUI file browser.

Implementation candidates:

- `textual` for a richer TUI.
- `rich` for simpler terminal tables and menus.

Requirements:

- The TUI must operate over the same local archive and pipeline APIs as the CLI.
- It should not create a second source of truth.
- Destructive or overwriting actions should require confirmation.
- It should remain usable on Windows terminals.
- It should be possible to exit cleanly without leaving background tasks running.

### Automatic Meeting Detection

Manola should eventually support a Granola-like background mode that detects likely meetings and creates meeting archives automatically.

Potential CLI:

```text
manola daemon start
manola daemon status
manola daemon stop
manola daemon logs
manola daemon run
```

Detection signals may include:

- Microphone activity.
- System-audio activity.
- Sustained two-sided meeting capture.
- Known meeting applications or browser tabs.
- Calendar event currently in progress.
- Minimum duration threshold to avoid creating archives for incidental audio.

Requirements:

- This feature must be privacy-explicit. The user should always know when Manola is monitoring for meetings and when it is recording.
- Local-first behavior remains mandatory: recordings and transcripts stay local unless the configured report/export flow explicitly sends data elsewhere.
- Automatic recording should have clear start/stop controls.
- False positives must be minimized. Manola should prefer not creating a meeting over recording unrelated audio silently.
- The daemon should expose status, logs, and current recording state.
- It should recover cleanly after crashes or restarts.
- It should not depend on calendar integration, but calendar data may improve detection and naming.

Open technical questions:

- Whether the daemon should be a long-running foreground CLI process, a Windows startup task, a tray app, or later part of the desktop app.
- How to persist daemon state.
- How to coordinate with manual `manola meet` runs.
- How to represent auto-created meetings that are later discarded or merged.

## CLI Commands

Primary:

```text
manola meet
manola process <audio-path>
manola record
manola record --live-transcript
manola enrich <meeting-id>
```

Supporting:

```text
manola import <audio-path>
manola transcribe <meeting-id>
manola summarize <meeting-id>
manola enrich <meeting-id>
manola export <meeting-id>
manola devices
manola list
manola config
manola doctor
manola audio doctor
manola audio devices
manola audio setup
manola audio setup --select
manola audio test --source meeting --duration 30
manola models download <model>
manola models list
manola prompts list
manola prompts show <name>
```

## CLI Feedback

Long-running commands must print status feedback before and during expensive steps.

Minimum feedback:

- `meet`: selected audio defaults, stop rule, optional max duration, language, transcription model/device, enrichment status, report profile, explicit LLM privacy notice, share policy, local output path, transcription, metadata suggestions, report generation, optional export.
- `devices`: default microphone/speaker, numbered available microphones, numbered available speakers, loopbacks, and examples for `--mic-index` / `--speaker-index` plus `--mic` / `--speaker`. `manola audio devices` is an equivalent alias under the audio namespace.
- `audio setup`: guided setup that lists devices, uses default microphone/speaker unless indices are passed, can show an arrow-key selector with `--select`, records microphone/system/meeting test samples, reports RMS/silence warnings, and prints the recommended `manola meet` command.
- `audio enhance-test`: selected input, enhancement mode, enhanced WAV path, optional baseline/enhanced transcript paths.
- `process`: import start, audio copy, normalization, transcription start/progress, report generation, export.
- `import`: import start, audio copy, normalization, metadata write.
- `transcribe`: meeting resolution, transcription start/progress, transcript write, optional summarize/export.
- `summarize`: meeting resolution, LLM report generation, report write, optional export.
- `enrich`: meeting resolution, LLM metadata suggestion generation, `metadata.suggestions.json` write.
- `export`: meeting resolution and selected share policy.
- `models download`: selected model and destination.
- `audio test`: recording source, requested duration, output WAV path, duration, RMS, silence warning.
- `prompts list/show`: active default or user-overridden prompt templates and their source paths.

Progress should be honest. If a backend does not expose granular progress, Manola should print step-level status rather than a fake percentage. Chunked transcription may report chunk counts.

## Acceptance Criteria For MVP

- A user can process an existing `.m4a` recording end-to-end.
- Manola creates normalized audio, transcript, metadata, and a Markdown report.
- Manola always keeps the original audio, normalized audio, transcript, report, and metadata in the local meeting archive, regardless of share policy.
- The user can force `en`, force `es`, or use auto language detection.
- The default LLM profile uses DeepSeek.
- The user can choose a meeting type, including `job_interview` and `case_interview`.
- The user can set attendees, title, project, and share policy.
- Manola proposes a folder based on project and meeting type.
- Manola can export a report to a configured Google Drive or OneDrive local folder.
- `manola doctor` clearly reports missing FFmpeg, missing API keys, and unavailable local transcription capabilities.
- Windows meeting recording is only considered MVP-stable if the audio spike passes its criteria.
- Live transcript mode can display and persist preview text during recording, while final `transcript.md` remains the canonical transcript for reports.

