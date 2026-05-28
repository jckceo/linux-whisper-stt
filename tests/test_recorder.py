from pathlib import Path

from linux_whisper_stt.audio.recorder import build_record_command


def test_command_uses_pw_record_with_rate_channels_and_output():
    cmd = build_record_command(samplerate=16000, channels=1, out_path=Path("/tmp/x.wav"))
    assert cmd[0] == "pw-record"
    assert "--rate" in cmd and "16000" in cmd
    assert "--channels" in cmd and "1" in cmd
    assert cmd[-1] == "/tmp/x.wav"


def test_command_targets_explicit_device():
    cmd = build_record_command(16000, 1, Path("/tmp/x.wav"), device="alsa_input.usb")
    assert "--target" in cmd
    assert "alsa_input.usb" in cmd


def test_command_default_device_has_no_target():
    cmd = build_record_command(16000, 1, Path("/tmp/x.wav"), device="default")
    assert "--target" not in cmd


def test_command_caps_duration_with_timeout_when_set():
    cmd = build_record_command(16000, 1, Path("/tmp/x.wav"), max_seconds=300)
    assert cmd[0] == "timeout"
    assert cmd[1] == "300"
    assert "pw-record" in cmd
    assert cmd[-1] == "/tmp/x.wav"


def test_command_omits_timeout_when_no_cap():
    cmd = build_record_command(16000, 1, Path("/tmp/x.wav"))
    assert cmd[0] == "pw-record"
    assert "timeout" not in cmd
