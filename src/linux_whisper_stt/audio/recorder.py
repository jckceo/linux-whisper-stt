from __future__ import annotations

import os
import signal
import subprocess
import tempfile
from pathlib import Path


def build_ffmpeg_command(
    device: str, samplerate: int, out_path: Path, max_seconds: int | None = None
) -> list[str]:
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "pulse",
        "-i", device,
        "-ac", "1",
        "-ar", str(samplerate),
    ]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    cmd.append(str(out_path))
    return cmd


class Recorder:
    """Records the microphone to a temp WAV using ffmpeg (PipeWire/Pulse).

    start() spawns ffmpeg; stop() asks it to finalize the file gracefully and
    returns the WAV path. max_seconds (if set) caps the captured duration via
    ffmpeg's -t flag so a forgotten recording cannot grow without bound.
    """

    def __init__(
        self,
        device: str = "default",
        samplerate: int = 16000,
        max_seconds: int | None = None,
    ):
        self.device = device
        self.samplerate = samplerate
        self.max_seconds = max_seconds
        self._proc: subprocess.Popen | None = None
        self._out_path: Path | None = None

    def start(self) -> None:
        fd, name = tempfile.mkstemp(suffix=".wav", prefix="lws-")
        os.close(fd)
        Path(name).unlink(missing_ok=True)  # ffmpeg will create it
        self._out_path = Path(name)
        cmd = build_ffmpeg_command(
            self.device, self.samplerate, self._out_path, self.max_seconds
        )
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
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        finally:
            self._proc = None
            self._out_path = None
        return out
