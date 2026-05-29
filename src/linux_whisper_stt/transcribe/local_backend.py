from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def build_whispercpp_command(
    binary: str, model_path: Path, wav_path: Path, language: str
) -> list[str]:
    lang = language if (language and language != "auto") else "auto"
    return [
        binary,
        "-m", str(model_path),
        "-f", str(wav_path),
        "-l", lang,
        "-nt",
    ]


def parse_whispercpp_output(stdout: str) -> str:
    return stdout.strip()


class LocalWhisperCppTranscriber:
    def __init__(self, binary: str, model_path: Path, runner=subprocess.run):
        self.binary = binary
        self.model_path = model_path
        self.runner = runner

    @classmethod
    def from_config(cls, config) -> LocalWhisperCppTranscriber:
        binary = config.local.binary_path or (shutil.which("whisper-cli") or "whisper-cli")
        models_dir = Path(os.path.expanduser(config.local.models_dir))
        model_path = models_dir / f"ggml-{config.local.model}.bin"
        return cls(binary, model_path, subprocess.run)

    def transcribe(self, wav_path: Path, language: str) -> str:
        cmd = build_whispercpp_command(self.binary, self.model_path, wav_path, language)
        proc = self.runner(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"whisper.cpp failed: {proc.stderr.strip()}")
        return parse_whispercpp_output(proc.stdout)
