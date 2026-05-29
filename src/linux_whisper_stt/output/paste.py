from __future__ import annotations

import shutil
import subprocess
import time

PASTE_PLAIN_TEXT_COMMAND = ["ydotool", "key", "ctrl+shift+v"]


def ydotool_available(which=shutil.which) -> bool:
    return which("ydotool") is not None


def paste_via_ydotool(text: str, runner=subprocess.run, sleep_fn=time.sleep) -> None:
    _ = text
    sleep_fn(0.15)
    runner(PASTE_PLAIN_TEXT_COMMAND, check=True)
