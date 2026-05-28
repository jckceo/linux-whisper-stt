from __future__ import annotations

import subprocess


def copy_to_clipboard(text: str, runner=subprocess.run) -> None:
    runner(["wl-copy"], input=text, text=True, check=True)


def read_clipboard(runner=subprocess.run) -> str:
    proc = runner(["wl-paste", "-n"], capture_output=True, text=True)
    return proc.stdout
