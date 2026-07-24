from __future__ import annotations

import os
import shutil
import subprocess
import time


def copy_to_clipboard(
    text: str,
    runner=subprocess.run,
    env: dict[str, str] | None = None,
    which=shutil.which,
) -> None:
    runner(_copy_command(env or os.environ, which), input=text, text=True, check=True)


def read_clipboard(
    runner=subprocess.run,
    env: dict[str, str] | None = None,
    which=shutil.which,
) -> str:
    proc = runner(_read_command(env or os.environ, which), capture_output=True, text=True)
    return proc.stdout


def _copy_command(env, which) -> list[str]:
    if env.get("WAYLAND_DISPLAY"):
        return ["wl-copy"]
    if env.get("DISPLAY"):
        if which("xclip"):
            return ["xclip", "-selection", "clipboard"]
        if which("xsel"):
            return ["xsel", "--clipboard", "--input"]
    return ["wl-copy"]


def _read_command(env, which) -> list[str]:
    if env.get("WAYLAND_DISPLAY"):
        return ["wl-paste", "-n"]
    if env.get("DISPLAY"):
        if which("xclip"):
            return ["xclip", "-selection", "clipboard", "-out"]
        if which("xsel"):
            return ["xsel", "--clipboard", "--output"]
    return ["wl-paste", "-n"]


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
