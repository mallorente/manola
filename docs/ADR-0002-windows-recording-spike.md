# ADR-0002: Windows Meeting Recording Spike

## Status

Accepted

## Context

Nanola should feel like a meeting recorder, not an audio engineering tool. For real remote meetings, the useful default is to record both the user's microphone and the system audio from the call.

However, reliable system-audio capture differs substantially between operating systems:

- Windows uses WASAPI loopback.
- Linux depends on PulseAudio or PipeWire monitor sources.
- macOS often needs an external virtual audio device such as BlackHole or Loopback and varies across OS versions.

The MVP is Windows-first. macOS recording is Phase 2.

## Decision

The primary UX will be:

```text
nanola meet
nanola record
```

This means "record a meeting" and attempts to capture:

- microphone audio;
- system audio;
- timestamps and metadata.

Advanced source-specific modes may exist for diagnostics and fallback:

```text
nanola record --source mic
nanola record --source system
nanola record --source meeting
nanola record --mic "<name>" --speaker "<name>"
nanola devices
nanola audio devices
```

`record meeting` must not silently continue if either microphone or system audio is unavailable. It must ask for explicit confirmation or fail.

The MVP must support importing recordings regardless of whether recording is stable.

Recording made by Nanola will be stored as WAV in MVP.

## Audio Spike

Before marking recording as stable, run a Windows technical spike.

Required commands:

```text
nanola audio doctor
nanola audio test --source mic
nanola audio test --source system
nanola audio test --source meeting --duration 30
```

The spike must:

- Enumerate microphones.
- Enumerate output devices.
- Detect loopback/system-audio capture if available.
- Record 30 seconds from microphone.
- Record 30 seconds from system audio.
- Record 30 seconds from microphone plus system audio.
- Verify generated WAV duration.
- Verify non-zero signal/RMS.
- Verify the meeting recording captures both the user's voice and remote/system audio.

Candidate libraries:

- `soundcard`
- `PyAudioWPatch`
- `sounddevice` / PortAudio
- FFmpeg device capture where appropriate

The implementation should hide the chosen library behind an `AudioRecorder` interface so the user-facing CLI remains stable.

### Spike Implementation Status

Initial implementation uses `soundcard`.

Implemented commands:

```text
nanola audio doctor
nanola devices
nanola audio devices
nanola audio test --source mic --duration 3
nanola audio test --source system --duration 3
nanola audio test --source meeting --duration 3
nanola record --duration 30 --source meeting
nanola record --duration 30 --source meeting --process
```

Current behavior:

- Enumerates microphones.
- Enumerates output devices.
- Enumerates loopback devices.
- Records WAV samples for microphone, system loopback, and mixed meeting audio.
- Records meeting WAV files through the primary `nanola record` command.
- Stores recordings directly inside the meeting archive as `audio/recorded.wav`.
- Optionally processes recorded WAV files after capture with `--process`.
- Reports WAV duration, sample rate, and RMS.
- Reports separate microphone/system RMS for meeting capture when available.
- Supports explicit microphone and speaker selection with `--mic-index <n>` / `--speaker-index <n>` or `--mic "<name>"` / `--speaker "<name>"`.
- Provides `nanola devices` and the equivalent `nanola audio devices` alias for listing input/output devices.
- Provides `nanola meet` as the user-facing default workflow. It records until `q` is pressed or system audio is silent for the configured timeout, then transcribes and summarizes.
- Keeps `nanola record` as an advanced/raw capture command; `nanola meet` is the normal meeting workflow.
- Fails `record --source meeting` when either microphone or system audio appears silent, unless `--allow-partial` is supplied.
- Keeps the diagnostic WAV at `audio/recorded.wav` when partial capture is rejected.

Observed on the first Windows test machine:

- Default microphone was detected.
- Default speaker was detected.
- Loopback devices were detected.
- Microphone recording produced non-zero RMS.
- System loopback produced a valid WAV and non-zero RMS when known audio was playing through the default output.
- Meeting recording produced a valid WAV and non-zero RMS while combining microphone and system loopback capture.

Recorded validation samples:

- `nanola audio test --source mic --duration 3`: RMS `0.005352`.
- `nanola audio test --source system --duration 10`: RMS `0.006546`.
- `nanola audio test --source meeting --duration 10`: RMS `0.005141`.

Remaining before recording can be called stable:

- Validate explicit device selection on real Teams/Meet/Zoom calls, not only unit tests.
- Replace the current simple silence hard-stop with a pause/resume design if real meeting use shows long pauses are common.
- Consider whether `audio test --source meeting` should also report component-level RMS like `record`.

## Fallback Behavior

If system audio is unavailable or appears silent:

```text
System audio capture is unavailable on this machine.
Continue microphone-only? [y/N]
```

Default: no.

If microphone audio is unavailable or appears silent:

```text
Microphone is unavailable.
Continue system-audio-only? [y/N]
```

Default: no.

Advanced override:

```text
nanola record --allow-partial
```

## Rationale

The user wants to record meetings like Granola. Exposing microphone and system audio as the main decision would push platform details into the product UX. The product should make the right default choice and reserve source selection for diagnostics.

At the same time, silently recording only one side of a remote meeting would create bad transcripts and false confidence. Blocking or confirming partial capture is safer.

## Consequences

Positive:

- Product UX matches the real user goal.
- Partial recordings are not created by accident.
- Technical uncertainty is isolated in a spike.
- Importing existing `.m4a` files remains the stable MVP path.

Tradeoffs:

- Windows recording cannot be promised until tested on a real machine.
- Additional audio diagnostics are required before user-facing recording is considered stable.
- macOS recording is intentionally postponed to Phase 2.
