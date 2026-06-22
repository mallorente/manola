from __future__ import annotations

import math
import sys
import warnings
import wave
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np

from .errors import DependencyMissingError, ManolaError
from .status import noop_status
from .vad import build_speech_detector


DEFAULT_SAMPLE_RATE = 48000
SILENCE_RMS_THRESHOLD = 0.0001


@dataclass(frozen=True)
class AudioDeviceReport:
    default_microphone: str | None
    default_speaker: str | None
    microphones: list[str]
    speakers: list[str]
    loopbacks: list[str]

    @property
    def has_meeting_capture(self) -> bool:
        return self.default_microphone is not None and bool(self.loopbacks)


@dataclass(frozen=True)
class AudioTestResult:
    path: Path
    duration_seconds: float
    rms: float
    sample_rate: int
    silent: bool
    component_rms: dict[str, float] | None = None


def inspect_audio_devices() -> AudioDeviceReport:
    sc = _soundcard()
    microphones = sc.all_microphones(include_loopback=False)
    speakers = sc.all_speakers()
    loopbacks = _loopback_microphones(sc)
    default_microphone = _device_name(sc.default_microphone())
    default_speaker = _device_name(sc.default_speaker())
    return AudioDeviceReport(
        default_microphone=default_microphone,
        default_speaker=default_speaker,
        microphones=[_device_name(device) for device in microphones],
        speakers=[_device_name(device) for device in speakers],
        loopbacks=[_device_name(device) for device in loopbacks],
    )


def record_audio_test(
    *,
    source: str,
    duration_seconds: int,
    output_dir: Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    mic_name: str | None = None,
    mic_index: int | None = None,
    speaker_name: str | None = None,
    speaker_index: int | None = None,
) -> AudioTestResult:
    if duration_seconds <= 0:
        raise ManolaError("Audio test duration must be greater than zero.")

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"audio-test-{source}-{datetime.now():%Y%m%d-%H%M%S}.wav"
    audio = _record_source(
        source,
        duration_seconds,
        sample_rate,
        mic_name=mic_name,
        mic_index=mic_index,
        speaker_name=speaker_name,
        speaker_index=speaker_index,
    )
    write_wav(target, audio, sample_rate)
    duration = _wav_duration(target)
    rms = rms_float(audio)
    if duration <= 0:
        raise ManolaError(f"Recorded WAV has invalid duration: {target}")
    return AudioTestResult(
        path=target,
        duration_seconds=duration,
        rms=rms,
        sample_rate=sample_rate,
        silent=rms <= SILENCE_RMS_THRESHOLD,
        component_rms=None,
    )


def record_wav(
    *,
    source: str,
    duration_seconds: int,
    target: Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    mic_name: str | None = None,
    mic_index: int | None = None,
    speaker_name: str | None = None,
    speaker_index: int | None = None,
    allow_partial: bool = False,
) -> AudioTestResult:
    if duration_seconds <= 0:
        raise ManolaError("Recording duration must be greater than zero.")
    target.parent.mkdir(parents=True, exist_ok=True)
    audio, component_rms = _record_source_with_components(
        source,
        duration_seconds,
        sample_rate,
        mic_name=mic_name,
        mic_index=mic_index,
        speaker_name=speaker_name,
        speaker_index=speaker_index,
    )
    write_wav(target, audio, sample_rate)
    _raise_for_partial_meeting_capture(source, component_rms, allow_partial, target)
    duration = _wav_duration(target)
    rms = rms_float(audio)
    if duration <= 0:
        raise ManolaError(f"Recorded WAV has invalid duration: {target}")
    return AudioTestResult(
        path=target,
        duration_seconds=duration,
        rms=rms,
        sample_rate=sample_rate,
        silent=rms <= SILENCE_RMS_THRESHOLD,
        component_rms=component_rms,
    )


def record_meeting_until_stopped(
    *,
    target: Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    mic_name: str | None = None,
    mic_index: int | None = None,
    speaker_name: str | None = None,
    speaker_index: int | None = None,
    allow_partial: bool = False,
    duration_seconds: int | None = None,
    silence_timeout_seconds: int = 30,
    pause_after_silence_seconds: int = 10,
    stop_key: str = "q",
    chunk_seconds: float = 1.0,
    use_vad: bool = True,
    vad_aggressiveness: int = 2,
    status: Callable[[str], None] | None = None,
    on_audio_chunk: Callable[[np.ndarray, int], None] | None = None,
    on_audio_level: Callable[[dict[str, float]], None] | None = None,
) -> AudioTestResult:
    if duration_seconds is not None and duration_seconds <= 0:
        raise ManolaError("Recording duration must be greater than zero.")
    if silence_timeout_seconds < 0:
        raise ManolaError("Silence timeout must be zero or greater.")
    if pause_after_silence_seconds < 0:
        raise ManolaError("Pause-after-silence must be zero or greater.")
    if chunk_seconds <= 0:
        raise ManolaError("Recording chunk duration must be greater than zero.")

    target.parent.mkdir(parents=True, exist_ok=True)
    speech_detector = (
        build_speech_detector(vad_aggressiveness, status=status or noop_status) if use_vad else None
    )
    sc = _soundcard()
    microphone = _microphone(sc, mic_name, mic_index)
    loopback = _select_loopback(sc, speaker_name, speaker_index, sample_rate, status)
    chunk_frames = max(1, int(sample_rate * chunk_seconds))
    max_frames = None if duration_seconds is None else duration_seconds * sample_rate
    stop_key = stop_key.casefold()

    elapsed_frames = 0
    total_frames = 0
    mixed_square_sum = 0.0
    mic_square_sum = 0.0
    system_square_sum = 0.0
    inactive_seconds = 0.0
    paused = False
    stop_reason = ""

    with wave.open(str(target), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        with microphone.recorder(samplerate=sample_rate) as mic_recorder, loopback.recorder(
            samplerate=sample_rate
        ) as system_recorder:
            with ThreadPoolExecutor(max_workers=2) as executor:
                while True:
                    frames = chunk_frames if max_frames is None else min(chunk_frames, max_frames - elapsed_frames)
                    if frames <= 0:
                        stop_reason = "duration reached"
                        break

                    mic_future = executor.submit(_record_frames, mic_recorder, frames)
                    system_future = executor.submit(_record_frames, system_recorder, frames)
                    mic_audio = mic_future.result()
                    system_audio = system_future.result()
                    mixed = _mix_audio([mic_audio, system_audio])
                    mic_mono = _to_mono(mic_audio)
                    system_mono = _to_mono(system_audio)
                    mixed_mono = _to_mono(mixed)
                    current_frames = mixed_mono.shape[0]
                    elapsed_frames += current_frames

                    mic_rms = rms_float(mic_mono)
                    system_rms = rms_float(system_mono)
                    if on_audio_level is not None:
                        on_audio_level({"mic": mic_rms, "system": system_rms})
                    # VAD only adds activity: it rescues quiet-but-present speech
                    # that falls below the RMS floor, and never introduces a pause
                    # the RMS rule would not already allow.
                    speech_detected = speech_detector is not None and (
                        speech_detector.has_speech(mic_mono, sample_rate)
                        or speech_detector.has_speech(system_mono, sample_rate)
                    )
                    active_audio = (
                        speech_detected
                        or mic_rms > SILENCE_RMS_THRESHOLD
                        or system_rms > SILENCE_RMS_THRESHOLD
                    )
                    pressed_keys = _pressed_keys()
                    stop_pressed = stop_key in pressed_keys
                    resume_pressed = bool(pressed_keys - {stop_key})

                    if active_audio:
                        inactive_seconds = 0.0
                        if paused and status:
                            status("Resumed recording: audio activity detected.")
                        paused = False
                    else:
                        inactive_seconds += current_frames / float(sample_rate)

                    if stop_pressed:
                        stop_reason = f"'{stop_key}' pressed"
                        break

                    if paused and resume_pressed:
                        inactive_seconds = 0.0
                        paused = False
                        if status:
                            status("Resumed recording: key pressed.")

                    if silence_timeout_seconds and inactive_seconds >= silence_timeout_seconds:
                        stop_reason = f"inactive for {silence_timeout_seconds}s"
                        break

                    pause_enabled = (
                        pause_after_silence_seconds
                        and silence_timeout_seconds
                        and pause_after_silence_seconds < silence_timeout_seconds
                    )
                    if (
                        pause_enabled
                        and not paused
                        and inactive_seconds >= pause_after_silence_seconds
                    ):
                        paused = True
                        if status:
                            status(
                                f"Paused recording after {pause_after_silence_seconds}s of silence; "
                                "waiting for mic/system audio to resume."
                            )

                    if paused:
                        continue

                    handle.writeframes(_pcm_bytes(mixed))
                    if on_audio_chunk is not None:
                        on_audio_chunk(mixed_mono, sample_rate)
                    total_frames += current_frames
                    mixed_square_sum += _square_sum(mixed_mono)
                    mic_square_sum += _square_sum(mic_mono[:current_frames])
                    system_square_sum += _square_sum(system_mono[:current_frames])

    if total_frames <= 0:
        raise ManolaError("No audio samples captured.")

    duration = _wav_duration(target)
    component_rms = {
        "mic": _rms_from_square_sum(mic_square_sum, total_frames),
        "system": _rms_from_square_sum(system_square_sum, total_frames),
    }
    _raise_for_partial_meeting_capture("meeting", component_rms, allow_partial, target)
    if status and stop_reason:
        status(f"Stopped recording: {stop_reason}.")

    rms = _rms_from_square_sum(mixed_square_sum, total_frames)
    return AudioTestResult(
        path=target,
        duration_seconds=duration,
        rms=rms,
        sample_rate=sample_rate,
        silent=rms <= SILENCE_RMS_THRESHOLD,
        component_rms=component_rms,
    )


def write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    mono = _to_mono(audio)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(_pcm_bytes(mono))


def rms_float(audio: np.ndarray) -> float:
    mono = _to_mono(audio)
    if mono.size == 0:
        return 0.0
    return float(math.sqrt(float(np.mean(np.square(mono)))))


def _pcm_bytes(audio: np.ndarray) -> bytes:
    mono = _to_mono(audio)
    clipped = np.clip(mono, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16).tobytes()


def _square_sum(audio: np.ndarray) -> float:
    mono = _to_mono(audio)
    if mono.size == 0:
        return 0.0
    return float(np.sum(np.square(mono)))


def _rms_from_square_sum(square_sum: float, count: int) -> float:
    if count <= 0:
        return 0.0
    return float(math.sqrt(square_sum / count))


def _record_source(
    source: str,
    duration_seconds: int,
    sample_rate: int,
    *,
    mic_name: str | None = None,
    mic_index: int | None = None,
    speaker_name: str | None = None,
    speaker_index: int | None = None,
) -> np.ndarray:
    audio, _components = _record_source_with_components(
        source,
        duration_seconds,
        sample_rate,
        mic_name=mic_name,
        mic_index=mic_index,
        speaker_name=speaker_name,
        speaker_index=speaker_index,
    )
    return audio


def _record_source_with_components(
    source: str,
    duration_seconds: int,
    sample_rate: int,
    *,
    mic_name: str | None = None,
    mic_index: int | None = None,
    speaker_name: str | None = None,
    speaker_index: int | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    sc = _soundcard()
    frames = duration_seconds * sample_rate
    if source == "mic":
        audio = _record_device(_microphone(sc, mic_name, mic_index), frames, sample_rate)
        return audio, {"mic": rms_float(audio)}
    if source == "system":
        audio = _record_device(_loopback(sc, speaker_name, speaker_index), frames, sample_rate)
        return audio, {"system": rms_float(audio)}
    if source == "meeting":
        microphone = _microphone(sc, mic_name, mic_index)
        loopback = _loopback(sc, speaker_name, speaker_index)
        with ThreadPoolExecutor(max_workers=2) as executor:
            mic_future = executor.submit(_record_device, microphone, frames, sample_rate)
            system_future = executor.submit(_record_device, loopback, frames, sample_rate)
            mic_audio = mic_future.result()
            system_audio = system_future.result()
            return _mix_audio([mic_audio, system_audio]), {
                "mic": rms_float(mic_audio),
                "system": rms_float(system_audio),
            }
    raise ManolaError("Audio test source must be one of: mic, system, meeting.")


def _record_device(device, frames: int, sample_rate: int) -> np.ndarray:
    if device is None:
        raise ManolaError("Requested audio device is unavailable.")
    with device.recorder(samplerate=sample_rate) as recorder:
        return _record_frames(recorder, frames)


def _record_frames(recorder, frames: int) -> np.ndarray:
    with _ignore_soundcard_discontinuity_warnings():
        return recorder.record(numframes=frames)


@contextmanager
def _ignore_soundcard_discontinuity_warnings():
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="data discontinuity in recording",
            category=RuntimeWarning,
            module=r"soundcard\.mediafoundation",
        )
        yield


def _microphone(sc, name: str | None, index: int | None):
    if name is not None and index is not None:
        raise ManolaError("Use either --mic or --mic-index, not both.")
    microphones = sc.all_microphones(include_loopback=False)
    if index is not None:
        return _device_by_index(microphones, index, "microphone")
    if name is None:
        return sc.default_microphone()
    return _match_device(microphones, name, "microphone")


def _loopback(sc, speaker_name: str | None, speaker_index: int | None):
    if speaker_name is not None and speaker_index is not None:
        raise ManolaError("Use either --speaker or --speaker-index, not both.")
    explicit_speaker = speaker_name is not None or speaker_index is not None
    speakers = sc.all_speakers()
    if speaker_index is not None:
        speaker = _device_by_index(speakers, speaker_index, "speaker")
    else:
        speaker = sc.default_speaker() if speaker_name is None else _match_device(speakers, speaker_name, "speaker")
    selected_speaker_name = _device_name(speaker)
    normalized_speaker_name = _normalize_device_name(selected_speaker_name or "")
    loopbacks = _loopback_microphones(sc)
    if not loopbacks:
        raise ManolaError("System audio loopback capture is unavailable.")
    for loopback in loopbacks:
        name = _device_name(loopback)
        normalized_loopback_name = _normalize_device_name(name or "")
        if normalized_speaker_name and (
            normalized_speaker_name in normalized_loopback_name or normalized_loopback_name in normalized_speaker_name
        ):
            return loopback
    if explicit_speaker:
        available = ", ".join(filter(None, (_device_name(device) for device in loopbacks)))
        raise ManolaError(
            f"No loopback microphone found for speaker '{selected_speaker_name}'. Available loopbacks: {available}"
        )
    return loopbacks[0]


def _select_loopback(
    sc,
    speaker_name: str | None,
    speaker_index: int | None,
    sample_rate: int,
    status: Callable[[str], None] | None = None,
):
    if speaker_name is not None or speaker_index is not None:
        return _loopback(sc, speaker_name, speaker_index)

    active = _active_loopback(sc, sample_rate=sample_rate, probe_seconds=0.5)
    if active is None:
        return _loopback(sc, speaker_name, speaker_index)

    loopback, rms = active
    if status:
        status(f"Auto-selected system audio loopback: {_device_name(loopback)} (RMS {rms:0.6f}).")
    return loopback


def _active_loopback(sc, *, sample_rate: int, probe_seconds: float):
    loopbacks = _loopback_microphones(sc)
    if not loopbacks:
        return None
    frames = max(1, int(sample_rate * probe_seconds))
    results = []
    with ThreadPoolExecutor(max_workers=min(len(loopbacks), 4)) as executor:
        futures = [(device, executor.submit(_record_device, device, frames, sample_rate)) for device in loopbacks]
        for device, future in futures:
            try:
                rms = rms_float(future.result())
            except Exception:
                continue
            results.append((device, rms))
    if not results:
        return None
    device, rms = max(results, key=lambda result: result[1])
    if rms <= SILENCE_RMS_THRESHOLD:
        return None
    return device, rms


def _loopback_microphones(sc) -> list:
    microphones = sc.all_microphones(include_loopback=True)
    return [device for device in microphones if getattr(device, "isloopback", False)]


def _mix_audio(audios: list[np.ndarray]) -> np.ndarray:
    mono_tracks = [_to_mono(audio) for audio in audios]
    min_length = min(track.shape[0] for track in mono_tracks)
    if min_length == 0:
        raise ManolaError("No audio samples captured.")
    stacked = np.vstack([track[:min_length] for track in mono_tracks])
    mixed = np.mean(stacked, axis=0)
    peak = float(np.max(np.abs(mixed)))
    if peak > 1.0:
        mixed = mixed / peak
    return mixed


def _raise_for_partial_meeting_capture(
    source: str,
    component_rms: dict[str, float],
    allow_partial: bool,
    target: Path,
) -> None:
    if source != "meeting" or allow_partial:
        return
    silent_components = [name for name, rms in component_rms.items() if rms <= SILENCE_RMS_THRESHOLD]
    if not silent_components:
        return
    components = ", ".join(silent_components)
    raise ManolaError(
        f"Meeting capture appears partial; silent component(s): {components}. "
        f"Recorded diagnostic WAV was kept at {target}. "
        "Re-run with --allow-partial to accept this recording."
    )


def _to_mono(audio: np.ndarray) -> np.ndarray:
    array = np.asarray(audio, dtype=np.float32)
    if array.ndim == 1:
        return array
    if array.ndim == 2:
        return np.mean(array, axis=1)
    raise ManolaError(f"Unsupported audio array shape: {array.shape}")


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def _device_name(device) -> str | None:
    if device is None:
        return None
    return str(getattr(device, "name", device))


def _match_device(devices: list, requested_name: str, kind: str):
    requested = _normalize_device_name(requested_name)
    matches = [
        device
        for device in devices
        if requested == _normalize_device_name(_device_name(device) or "")
        or requested in _normalize_device_name(_device_name(device) or "")
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        available = ", ".join(filter(None, (_device_name(device) for device in devices)))
        raise ManolaError(f"Unknown {kind}: '{requested_name}'. Available {kind}s: {available}")
    names = ", ".join(filter(None, (_device_name(device) for device in matches)))
    raise ManolaError(f"Ambiguous {kind}: '{requested_name}'. Matching {kind}s: {names}")


def _device_by_index(devices: list, index: int, kind: str):
    if index <= 0:
        raise ManolaError(f"{kind.capitalize()} index must be 1 or greater.")
    try:
        return devices[index - 1]
    except IndexError as exc:
        raise ManolaError(f"Unknown {kind} index: {index}. Available {kind}s: 1-{len(devices)}") from exc


def _normalize_device_name(name: str) -> str:
    return " ".join(name.casefold().split())


def _stop_key_pressed(stop_key: str) -> bool:
    return bool(stop_key and stop_key in _pressed_keys())


def _pressed_keys() -> set[str]:
    if sys.platform == "win32":
        try:
            import msvcrt
        except ImportError:
            return set()
        pressed = set()
        while msvcrt.kbhit():
            pressed.add(msvcrt.getwch().casefold())
        return pressed
    if not sys.stdin.isatty():
        return set()
    try:
        import select

        ready, _write, _error = select.select([sys.stdin], [], [], 0)
    except (OSError, ValueError):
        return set()
    if not ready:
        return set()
    return {sys.stdin.read(1).casefold()}


def _soundcard():
    try:
        import soundcard as sc
    except ImportError as exc:
        raise DependencyMissingError("Audio recording requires soundcard. Install project dependencies with uv sync.") from exc
    return sc
