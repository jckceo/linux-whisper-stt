from pathlib import Path

from linux_whisper_stt.audio.recorder import build_ffmpeg_command


def test_command_includes_format_rate_channels_and_output():
    cmd = build_ffmpeg_command(device="default", samplerate=16000, out_path=Path("/tmp/x.wav"))
    assert cmd[0] == "ffmpeg"
    assert "-f" in cmd and "pulse" in cmd
    assert "-ar" in cmd and "16000" in cmd
    assert "-ac" in cmd and "1" in cmd
    assert cmd[-1] == "/tmp/x.wav"


def test_command_uses_device():
    cmd = build_ffmpeg_command(device="alsa_input.usb", samplerate=16000, out_path=Path("/tmp/x.wav"))
    assert "alsa_input.usb" in cmd
