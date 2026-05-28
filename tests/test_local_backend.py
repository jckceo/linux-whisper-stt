from pathlib import Path

import pytest

from linux_whisper_stt.config import Config
from linux_whisper_stt.transcribe.local_backend import (
    LocalWhisperCppTranscriber,
    build_whispercpp_command,
    parse_whispercpp_output,
)


def test_command_basic():
    cmd = build_whispercpp_command("whisper-cli", Path("/m/small.bin"), Path("/a.wav"), "auto")
    assert cmd[0] == "whisper-cli"
    assert "-m" in cmd and "/m/small.bin" in cmd
    assert "-f" in cmd and "/a.wav" in cmd
    assert "-nt" in cmd               # no timestamps
    assert "-l" in cmd and "auto" in cmd


def test_command_explicit_language():
    cmd = build_whispercpp_command("whisper-cli", Path("/m/small.bin"), Path("/a.wav"), "it")
    assert "it" in cmd


def test_parse_strips_whitespace():
    assert parse_whispercpp_output("  ciao mondo \n") == "ciao mondo"


def test_transcribe_success():
    def fake_runner(cmd, **kwargs):
        class R:
            returncode = 0
            stdout = " hello \n"
            stderr = ""
        return R()

    t = LocalWhisperCppTranscriber("whisper-cli", Path("/m/small.bin"), runner=fake_runner)
    assert t.transcribe(Path("/a.wav"), "auto") == "hello"


def test_transcribe_error_raises():
    def fake_runner(cmd, **kwargs):
        class R:
            returncode = 1
            stdout = ""
            stderr = "model not found"
        return R()

    t = LocalWhisperCppTranscriber("whisper-cli", Path("/m/small.bin"), runner=fake_runner)
    with pytest.raises(RuntimeError) as exc:
        t.transcribe(Path("/a.wav"), "auto")
    assert "model not found" in str(exc.value)


def test_from_config_builds_model_path(tmp_path):
    cfg = Config()
    cfg.local.model = "small"
    cfg.local.models_dir = str(tmp_path)
    cfg.local.binary_path = "whisper-cli"
    t = LocalWhisperCppTranscriber.from_config(cfg)
    assert t.model_path == tmp_path / "ggml-small.bin"
    assert t.binary == "whisper-cli"
