from __future__ import annotations

from pathlib import Path


class TranscriptionManager:
    """Routes transcription to the backend named by config.general.engine."""

    def __init__(self, config, backends: dict):
        self.config = config
        self.backends = backends

    def transcribe(self, wav_path: Path, language: str) -> str:
        engine = self.config.general.engine
        backend = self.backends.get(engine)
        if backend is None:
            raise RuntimeError(f"Unknown transcription engine: {engine!r}")
        return backend.transcribe(wav_path, language)
