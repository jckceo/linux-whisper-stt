from __future__ import annotations

import shutil
import subprocess
import time

TYPE_TEXT_COMMAND = ["ydotool", "type", "--file", "-"]


def ydotool_available(which=shutil.which) -> bool:
    return which("ydotool") is not None


def paste_via_ydotool(text: str, runner=subprocess.run, sleep_fn=time.sleep) -> None:
    sleep_fn(0.15)
    runner(TYPE_TEXT_COMMAND, input=text, text=True, check=True)
