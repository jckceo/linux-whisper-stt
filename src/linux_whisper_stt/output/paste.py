from __future__ import annotations

import shutil
import subprocess


def ydotool_available(which=shutil.which) -> bool:
    return which("ydotool") is not None


def paste_via_ydotool(text: str, runner=subprocess.run) -> None:
    runner(["ydotool", "type", "--file", "-"], input=text, text=True, check=True)
