from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path


class HistoryStore:
    """Persists each dictation (audio + transcribed text) to a folder the user
    can browse. Files are named by timestamp: <stamp>.wav and <stamp>.txt."""

    def __init__(self, config):
        self.config = config

    def save(self, wav_path: Path, text: str, stamp: str | None = None) -> Path | None:
        if not self.config.history.enabled:
            return None
        directory = Path(os.path.expanduser(self.config.history.dir))
        directory.mkdir(parents=True, exist_ok=True)
        if stamp is None:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        wav_dest: Path | None = directory / f"{stamp}.wav"
        txt_dest = directory / f"{stamp}.txt"
        try:
            shutil.copyfile(wav_path, wav_dest)
        except OSError:
            wav_dest = None
        txt_dest.write_text(text or "", encoding="utf-8")
        return wav_dest
