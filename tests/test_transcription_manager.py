from pathlib import Path

import pytest

from linux_whisper_stt.config import Config
from linux_whisper_stt.transcribe.manager import TranscriptionManager


class FakeBackend:
    def __init__(self, text):
        self.text = text

    def transcribe(self, wav_path, language):
        return self.text


def test_selects_configured_engine():
    cfg = Config()
    cfg.general.engine = "local"
    mgr = TranscriptionManager(cfg, {"openai": FakeBackend("O"), "local": FakeBackend("L")})
    assert mgr.transcribe(Path("/tmp/a.wav"), "auto") == "L"


def test_unknown_engine_raises():
    cfg = Config()
    cfg.general.engine = "nope"
    mgr = TranscriptionManager(cfg, {"openai": FakeBackend("O")})
    with pytest.raises(RuntimeError) as exc:
        mgr.transcribe(Path("/tmp/a.wav"), "auto")
    assert "engine" in str(exc.value).lower()
