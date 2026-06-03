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


def test_openai_long_recording_uses_chunked_path():
    cfg = Config()  # engine defaults to "openai"
    captured = {}

    def chunked_fn(backend, wav, language, duration):
        captured["duration"] = duration
        return "chunked"

    mgr = TranscriptionManager(
        cfg,
        {"openai": FakeBackend("single")},
        duration_fn=lambda p: 200.0,
        chunked_fn=chunked_fn,
    )
    assert mgr.transcribe(Path("/tmp/a.wav"), "auto") == "chunked"
    assert captured["duration"] == 200.0


def test_openai_short_recording_uses_single_request():
    cfg = Config()
    mgr = TranscriptionManager(
        cfg,
        {"openai": FakeBackend("single")},
        duration_fn=lambda p: 30.0,
        chunked_fn=lambda *a, **k: pytest.fail("short recording must not chunk"),
    )
    assert mgr.transcribe(Path("/tmp/a.wav"), "auto") == "single"


def test_openai_unknown_duration_uses_single_request():
    cfg = Config()
    mgr = TranscriptionManager(
        cfg,
        {"openai": FakeBackend("single")},
        duration_fn=lambda p: None,
        chunked_fn=lambda *a, **k: pytest.fail("unknown duration must not chunk"),
    )
    assert mgr.transcribe(Path("/tmp/a.wav"), "auto") == "single"


def test_chunked_failure_falls_back_to_single_request():
    cfg = Config()

    def boom(*a, **k):
        raise RuntimeError("chunk pipeline failed")

    mgr = TranscriptionManager(
        cfg,
        {"openai": FakeBackend("single")},
        duration_fn=lambda p: 200.0,
        chunked_fn=boom,
    )
    assert mgr.transcribe(Path("/tmp/a.wav"), "auto") == "single"


def test_parallel_long_recordings_toggle_off_uses_single_request():
    cfg = Config()
    cfg.openai.parallel_long_recordings = False
    mgr = TranscriptionManager(
        cfg,
        {"openai": FakeBackend("single")},
        duration_fn=lambda p: 200.0,
        chunked_fn=lambda *a, **k: pytest.fail("toggle off must not chunk"),
    )
    assert mgr.transcribe(Path("/tmp/a.wav"), "auto") == "single"


def test_local_engine_never_chunks():
    cfg = Config()
    cfg.general.engine = "local"
    mgr = TranscriptionManager(
        cfg,
        {"openai": FakeBackend("O"), "local": FakeBackend("L")},
        duration_fn=lambda p: 9999.0,
        chunked_fn=lambda *a, **k: pytest.fail("local engine must not chunk"),
    )
    assert mgr.transcribe(Path("/tmp/a.wav"), "auto") == "L"
