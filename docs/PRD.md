# Nanola PRD

## Summary

Nanola is a local-first meeting recorder, transcriber, and report generator inspired by Granola. It starts as a CLI-first product that can process existing recordings, especially mobile `.m4a` files, and later grows into a cross-platform desktop app.

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
nanola process recording.m4a
```

If only an audio path is provided and the terminal is interactive, Nanola enters compact interactive mode.

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

When running in a non-interactive context, Nanola uses defaults.

### Process With Flags

```text
nanola process recording.m4a \
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
nanola meet
nanola record
```

`nanola meet` is the simple default command for non-technical usage. It should:

- Use the default microphone and default system output/loopback.
- Record meeting audio.
- Normalize the recording.
- Transcribe with the configured default local Whisper model/device.
- Generate a report with the configured default LLM profile unless disabled, clearly warning that the transcript will be sent to the remote LLM.
- Export only when a non-private share policy is supplied.
- Print the defaults it is about to use, the local output paths, and the flags for changing them.
- Continue until the stop key is pressed or system audio has been silent for the configured timeout.
- Prefer device indices from `nanola devices` when multiple devices share the same display name.

Default behavior:

- Capture microphone.
- Capture system audio.
- Save recording directly inside the local meeting archive as `audio/recorded.wav`.
- Normalize recording to `audio/normalized.wav`.
- Optionally show a live transcript preview while recording.
- For `meet`, process immediately after recording stops.

Advanced/debug options can expose individual sources:

```text
nanola record --source mic
nanola record --source system
nanola record --source meeting
nanola meet --mic-index 1 --speaker-index 3
nanola record --mic "<name>" --speaker "<name>"
nanola meet --stop-key q --silence-timeout 30
nanola meet --duration 3600
nanola record --live-transcript
nanola record --duration 30 --source meeting --process
```

`record --no-process` creates a local meeting archive with recorded audio, normalized audio, metadata, and placeholder report/transcript files. `record --process` additionally transcribes and optionally summarizes/exports according to the supplied flags.

For meeting capture, Nanola should report separate microphone and system RMS when available. If system audio appears silent during meeting capture, Nanola should warn clearly because the resulting transcript may miss the remote side of the call.

If meeting recording cannot capture both microphone and system audio, it must not continue silently. It should ask for explicit confirmation or fail.

Future auto-stop behavior should support pause/resume rather than only a hard stop: pause after X seconds of silence, resume recording when microphone or system audio becomes active again or the user presses a key, and stop after Y seconds of continued inactivity.

### Live Transcript While Recording

Nanola should support a live transcript mode for recorded meetings:

```text
nanola record --live-transcript
```

Live transcript behavior:

- Capture meeting audio and write the canonical recording locally as usual.
- Transcribe short audio windows during recording, for example 10-30 seconds at a time.
- Show incremental transcript text in the terminal while the meeting is happening.
- Persist the live preview to the meeting folder as `live_transcript.md`.
- Mark live transcript output as preview quality.
- Continue recording even if live transcription fails, unless recording itself fails.
- After recording stops, run the normal final transcription pipeline over the complete recording.
- Treat final `transcript.md` as canonical for reports, exports, and metadata.

Live transcript is a user-facing convenience, not the source of truth. It may contain duplicated words around chunk boundaries, imperfect timestamps, or partial sentences. The final transcription pass is responsible for producing the clean transcript used by report generation.

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

Recordings made by Nanola are stored as WAV in MVP:

```text
audio/
  recorded.wav
  normalized.wav
```

Future versions may add compressed archive formats such as `.m4a` or `.opus`.

## Voice Enhancement V2

Nanola should support optional voice enhancement for noisy recordings in a future version. The goal is to improve transcript fidelity when the input contains room noise, fan noise, low voice volume, echo, compression artifacts, or mixed meeting audio where speech is not prominent enough.

Voice enhancement should never overwrite the original recording. It should create an additional audio artifact:

```text
audio/
  original.m4a
  normalized.wav
  enhanced.wav
```

For recordings made by Nanola:

```text
audio/
  recorded.wav
  normalized.wav
  enhanced.wav
```

Potential CLI:

```text
nanola process recording.m4a --enhance-voice
nanola process recording.m4a --enhance-voice light
nanola process recording.m4a --enhance-voice denoise
nanola record --process --enhance-voice
nanola audio enhance-test <meeting-id-or-audio-path>
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

Nanola should keep both transcripts during evaluation:

```text
transcript.baseline.md
transcript.enhanced.md
```

The first evaluation sample should be the existing recording:

```text
C:\Users\Usuario\OneDrive\Documentos\Grabaciones de sonido\Grabación (38).m4a
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
nanola process meeting.m4a --language en
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

Nanola uses meeting types to choose report templates.

Initial types:

- `general`
- `sales_discovery`
- `sales_demo`
- `customer_success`
- `internal_sync`
- `one_on_one`
- `job_interview`
- `case_interview`
- `project_review`
- `incident_postmortem`
- `brainstorm`

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
    nanola/
      2026-05-07__job-interview__ana-garcia__backend-role/
```

If no project is set:

```text
Meetings/
  2026-05-08__general__recording-22-10/
```

The user can override proposed names and folders.

## Sharing

Nanola shares through a configurable local synced folder, not through Gmail.

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
- Base URL: `https://api.deepseek.com`
- Model: `deepseek-v4-flash`
- Thinking: disabled

Optional profiles:

- DeepSeek reasoning profile.
- OpenAI fallback using `gpt-4.1-mini`.
- Qwen low-cost profile.

## Configuration

Configuration lives in the user profile, not in synced meeting folders.

```text
~/.nanola/config.toml
~/.nanola/secrets.toml
```

Secret resolution priority:

1. Environment variables.
2. `~/.nanola/secrets.toml`.
3. Clear error message with setup instructions.

Secrets must never be stored in meeting metadata or shared folders.

## CLI Commands

Primary:

```text
nanola meet
nanola process <audio-path>
nanola record
nanola record --live-transcript
```

Supporting:

```text
nanola import <audio-path>
nanola transcribe <meeting-id>
nanola summarize <meeting-id>
nanola export <meeting-id>
nanola devices
nanola list
nanola config
nanola doctor
nanola audio doctor
nanola audio devices
nanola audio setup
nanola audio setup --select
nanola audio test --source meeting --duration 30
nanola models download <model>
nanola models list
```

## CLI Feedback

Long-running commands must print status feedback before and during expensive steps.

Minimum feedback:

- `meet`: selected audio defaults, stop rule, optional max duration, language, transcription model/device, report profile, explicit LLM privacy notice, share policy, local output paths, recording path, transcription, report generation, optional export.
- `devices`: default microphone/speaker, numbered available microphones, numbered available speakers, loopbacks, and examples for `--mic-index` / `--speaker-index` plus `--mic` / `--speaker`. `nanola audio devices` is an equivalent alias under the audio namespace.
- `audio setup`: guided setup that lists devices, uses default microphone/speaker unless indices are passed, can show an arrow-key selector with `--select`, records microphone/system/meeting test samples, reports RMS/silence warnings, and prints the recommended `nanola meet` command.
- `process`: import start, audio copy, normalization, transcription start/progress, report generation, export.
- `import`: import start, audio copy, normalization, metadata write.
- `transcribe`: meeting resolution, transcription start/progress, transcript write, optional summarize/export.
- `summarize`: meeting resolution, LLM report generation, report write, optional export.
- `export`: meeting resolution and selected share policy.
- `models download`: selected model and destination.
- `audio test`: recording source, requested duration, output WAV path, duration, RMS, silence warning.

Progress should be honest. If a backend does not expose granular progress, Nanola should print step-level status rather than a fake percentage. Chunked transcription may report chunk counts.

## Acceptance Criteria For MVP

- A user can process an existing `.m4a` recording end-to-end.
- Nanola creates normalized audio, transcript, metadata, and a Markdown report.
- Nanola always keeps the original audio, normalized audio, transcript, report, and metadata in the local meeting archive, regardless of share policy.
- The user can force `en`, force `es`, or use auto language detection.
- The default LLM profile uses DeepSeek.
- The user can choose a meeting type, including `job_interview` and `case_interview`.
- The user can set attendees, title, project, and share policy.
- Nanola proposes a folder based on project and meeting type.
- Nanola can export a report to a configured Google Drive or OneDrive local folder.
- `nanola doctor` clearly reports missing FFmpeg, missing API keys, and unavailable local transcription capabilities.
- Windows meeting recording is only considered MVP-stable if the audio spike passes its criteria.
- Live transcript mode can display and persist preview text during recording, while final `transcript.md` remains the canonical transcript for reports.
