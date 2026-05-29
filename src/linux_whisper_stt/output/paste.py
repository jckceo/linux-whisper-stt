from __future__ import annotations

import shutil
import subprocess
import time

CTRL_V_SEQUENCE = ["ctrl+v"]


def ydotool_available(which=shutil.which) -> bool:
    return which("ydotool") is not None


def paste_via_ydotool(text: str, runner=subprocess.run, sleep_fn=time.sleep) -> None:
    _ = text
    sleep_fn(0.15)
    runner(["ydotool", "key", *CTRL_V_SEQUENCE], check=True)
