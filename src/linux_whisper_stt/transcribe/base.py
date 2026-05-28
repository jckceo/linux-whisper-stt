from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Transcriber(Protocol):
    def transcribe(self, wav_path: Path, language: str) -> str:
        ...
