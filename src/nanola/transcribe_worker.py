from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .cuda import add_packaged_cuda_dll_directories
from .config import AppConfig
from .models import Language
from .transcription import _transcribe_with_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path")
    parser.add_argument("output_path")
    parser.add_argument("--language", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    os.environ["NANOLA_TRANSCRIBE_WORKER"] = "1"
    config = AppConfig.model_validate_json(Path(args.config).read_text(encoding="utf-8"))
    add_packaged_cuda_dll_directories()

    from faster_whisper import WhisperModel

    model = WhisperModel(
        config.local_whisper_model,
        device=config.local_whisper_device,
        compute_type=config.local_whisper_compute_type,
    )
    language = Language(args.language)
    language_arg = None if language == Language.auto else language.value
    transcript = _transcribe_with_model(
        model,
        Path(args.audio_path),
        language_arg,
        config,
        status=lambda message: print(message, file=sys.stderr, flush=True),
    )
    Path(args.output_path).write_text(transcript + "\n", encoding="utf-8")

    # CTranslate2 can abort while destroying CUDA resources on some Windows
    # setups. At this point the transcript is persisted and the parent process
    # owns the rest of the pipeline.
    os._exit(0)


if __name__ == "__main__":
    main()
