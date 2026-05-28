from __future__ import annotations

import os
from pathlib import Path

_DESKTOP = """[Desktop Entry]
Type=Application
Name=linux-whisper-stt
Comment=Speech-to-text dictation
Exec=linux-whisper-stt daemon
Icon=audio-input-microphone
Terminal=false
X-GNOME-Autostart-enabled=true
"""


def autostart_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "autostart" / "linux-whisper-stt.desktop"


def install_autostart() -> Path:
    path = autostart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_DESKTOP)
    return path
