from __future__ import annotations

import shutil
import subprocess

# Linux input event keycodes: 29 = LEFTCTRL, 47 = V. ':1' press, ':0' release.
CTRL_V_SEQUENCE = ["29:1", "47:1", "47:0", "29:0"]


def ydotool_available(which=shutil.which) -> bool:
    return which("ydotool") is not None


def paste_via_ydotool(runner=subprocess.run) -> None:
    runner(["ydotool", "key", *CTRL_V_SEQUENCE], check=True)
