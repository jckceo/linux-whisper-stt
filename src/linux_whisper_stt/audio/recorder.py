from __future__ import annotations

import signal
import subprocess
import tempfile
from pathlib import Path


def build_ffmpeg_command(device: str, samplerate: int, out_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-f", "pulse",
        "-i", device,
        "-ac", "1",
        "-ar", str(samplerate),
        str(out_path),
    ]


class Recorder:
    """Records the microphone to a temp WAV using ffmpeg (PipeWire/Pulse).

    start() spawns ffmpeg; stop() asks it to finalize the file gracefully and
    returns the WAV path.
    """

    def __init__(self, device: str = "default", samplerate: int = 16000):
        self.device = device
        self.samplerate = samplerate
        self._proc: subprocess.Popen | None = None
        self._out_path: Path | None = None

    def start(self) -> None:
        fd, name = tempfile.mkstemp(suffix=".wav", prefix="lws-")
        Path(name).unlink(missing_ok=True)  # ffmpeg will create it
        import os

        os.close(fd)
        self._out_path = Path(name)
        cmd = build_ffmpeg_command(self.device, self.samplerate, self._out_path)
        # ffmpeg reads 'q' on stdin to stop and finalize the file cleanly.
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> Path:
        if self._proc is None or self._out_path is None:
            raise RuntimeError("Recorder.stop() called before start()")
        proc, out = self._proc, self._out_path
        try:
            proc.communicate(input=b"q", timeout=5)
        except subprocess.TimeoutExpired:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=5)
        self._proc = None
        self._out_path = None
        return out
