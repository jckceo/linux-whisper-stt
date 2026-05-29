from __future__ import annotations

import subprocess
import time


def copy_to_clipboard(text: str, runner=subprocess.run) -> None:
    runner(["wl-copy"], input=text, text=True, check=True)


def read_clipboard(runner=subprocess.run) -> str:
    proc = runner(["wl-paste", "-n"], capture_output=True, text=True)
    return proc.stdout


def wait_for_clipboard(
    text: str,
    timeout: float = 1.0,
    interval: float = 0.05,
    read_fn=read_clipboard,
    sleep_fn=time.sleep,
    monotonic_fn=time.monotonic,
) -> bool:
    deadline = monotonic_fn() + timeout
    while True:
        try:
            if read_fn() == text:
                return True
        except Exception:
            pass
        if monotonic_fn() >= deadline:
            return False
        sleep_fn(interval)
