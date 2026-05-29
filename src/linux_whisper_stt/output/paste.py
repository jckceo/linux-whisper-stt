from __future__ import annotations

import shutil
import subprocess
import time

RELEASE_SHORTCUT_MODIFIERS = [
    "29:0",
    "56:0",
    "97:0",
    "100:0",
    "42:0",
    "54:0",
    "125:0",
    "126:0",
]
CTRL_V_SEQUENCE = ["29:1", "47:1", "47:0", "29:0"]


def ydotool_available(which=shutil.which) -> bool:
    return which("ydotool") is not None


def paste_via_ydotool(text: str, runner=subprocess.run, sleep_fn=time.sleep) -> None:
    _ = text
    sleep_fn(0.15)
    runner(["ydotool", "key", *RELEASE_SHORTCUT_MODIFIERS], check=False)
    runner(["ydotool", "key", *CTRL_V_SEQUENCE], check=True)
