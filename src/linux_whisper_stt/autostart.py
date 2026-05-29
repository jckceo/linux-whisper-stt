from __future__ import annotations

import os
from pathlib import Path

from .cli import entrypoint


def autostart_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "autostart" / "linux-whisper-stt.desktop"


def _desktop_content() -> str:
    return f"""[Desktop Entry]
Type=Application
Name=linux-whisper-stt
Comment=Speech-to-text dictation
Exec={entrypoint()} daemon
Icon=audio-input-microphone
Terminal=false
X-GNOME-Autostart-enabled=true
"""


def install_autostart() -> Path:
    path = autostart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_desktop_content())
    return path


def uninstall_autostart() -> Path:
    path = autostart_path()
    path.unlink(missing_ok=True)
    return path
