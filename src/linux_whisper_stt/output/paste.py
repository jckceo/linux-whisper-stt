from __future__ import annotations

import shutil
import subprocess
import time

TYPE_TEXT_COMMAND = ["ydotool", "type", "--file", "-"]
UNICODE_INPUT_START_COMMAND = ["ydotool", "key", "ctrl+shift+u"]
UNICODE_INPUT_FINISH_COMMAND = ["ydotool", "key", "enter"]


def ydotool_available(which=shutil.which) -> bool:
    return which("ydotool") is not None


def paste_via_ydotool(text: str, runner=subprocess.run, sleep_fn=time.sleep) -> None:
    sleep_fn(0.15)
    pending = []
    for char in text:
        if ord(char) < 128:
            pending.append(char)
            continue
        _type_text_chunk("".join(pending), runner)
        pending.clear()
        _type_unicode_character(char, runner)
    _type_text_chunk("".join(pending), runner)


def _type_text_chunk(text: str, runner=subprocess.run) -> None:
    if text:
        runner(TYPE_TEXT_COMMAND, input=text, text=True, check=True)


def _type_unicode_character(char: str, runner=subprocess.run) -> None:
    runner(UNICODE_INPUT_START_COMMAND, check=True)
    runner(TYPE_TEXT_COMMAND, input=f"{ord(char):x}", text=True, check=True)
    runner(UNICODE_INPUT_FINISH_COMMAND, check=True)
