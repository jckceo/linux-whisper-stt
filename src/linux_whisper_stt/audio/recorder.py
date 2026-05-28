from __future__ import annotations

import os
import signal
import subprocess
import tempfile
from pathlib import Path


def build_record_command(
    samplerate: int,
    channels: int,
    out_path: Path,
    max_seconds: int | None = None,
    device: str = "default",
) -> list[str]:
    cmd = ["pw-record", "--rate", str(samplerate), "--channels", str(channels)]
    if device and device != "default":
        cmd += ["--target", device]
    cmd.append(str(out_path))
    if max_seconds:
        # Cap the capture length. `timeout` sends SIGTERM at the limit and
        # pw-record finalizes the WAV; a SIGINT sent for an early stop is
        # forwarded to pw-record too.
        cmd = ["timeout", str(max_seconds), *cmd]
    return cmd


class Recorder:
    """Records the microphone to a temp WAV using pw-record (PipeWire-native).

    pw-record is used instead of ffmpeg because the common Ubuntu ffmpeg build
    lacks the PulseAudio input device ("Unknown input format: 'pulse'"), while
    pw-record talks to PipeWire directly and finalizes a valid 16-bit WAV when
    stopped with a signal.
    """

    def __init__(
        self,
        device: str = "default",
        samplerate: int = 16000,
        channels: int = 1,
        max_seconds: int | None = None,
    ):
        self.device = device
        self.samplerate = samplerate
        self.channels = channels
        self.max_seconds = max_seconds
        self._proc: subprocess.Popen | None = None
        self._out_path: Path | None = None

    def start(self) -> None:
        fd, name = tempfile.mkstemp(suffix=".wav", prefix="lws-")
        os.close(fd)
        Path(name).unlink(missing_ok=True)  # pw-record will create it
        self._out_path = Path(name)
        cmd = build_record_command(
            self.samplerate, self.channels, self._out_path, self.max_seconds, self.device
        )
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def stop(self) -> Path:
        if self._proc is None or self._out_path is None:
            raise RuntimeError("Recorder.stop() called before start()")
        proc, out = self._proc, self._out_path
        proc.send_signal(signal.SIGINT)  # pw-record finalizes the WAV on SIGINT
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        finally:
            self._proc = None
            self._out_path = None
        return out
