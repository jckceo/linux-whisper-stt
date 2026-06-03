from __future__ import annotations

from pathlib import Path

from ..media.prepare import read_duration
from .long import chunked_transcribe

LONG_THRESHOLD_SECONDS = 90.0


class TranscriptionManager:
    """Routes transcription to the backend named by config.general.engine.

    For the OpenAI backend, recordings longer than the threshold are split on silences
    and transcribed in parallel (chunked_transcribe); any failure falls back to a single
    request. The local backend and short recordings always use a single request.
    """

    def __init__(
        self,
        config,
        backends: dict,
        duration_fn=read_duration,
        chunked_fn=chunked_transcribe,
        long_threshold_seconds: float = LONG_THRESHOLD_SECONDS,
    ):
        self.config = config
        self.backends = backends
        self.duration_fn = duration_fn
        self.chunked_fn = chunked_fn
        self.long_threshold_seconds = long_threshold_seconds

    def transcribe(self, wav_path: Path, language: str) -> str:
        engine = self.config.general.engine
        backend = self.backends.get(engine)
        if backend is None:
            raise RuntimeError(f"Unknown transcription engine: {engine!r}")
        if engine == "openai" and self.config.openai.parallel_long_recordings:
            duration = self.duration_fn(wav_path)
            if duration is not None and duration > self.long_threshold_seconds:
                try:
                    return self.chunked_fn(backend, wav_path, language, duration)
                except Exception as exc:
                    # Never fail a dictation because the optimizer tripped; fall back
                    # to a single request, but leave a trace (e.g. ffmpeg missing).
                    print(f"[transcribe] chunked path failed, using single request: {exc}")
        return backend.transcribe(wav_path, language)
