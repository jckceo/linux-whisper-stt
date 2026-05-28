from __future__ import annotations

import subprocess

CUSTOM_PATH = (
    "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/linux-whisper-stt/"
)
_MEDIA_KEYS = "org.gnome.settings-daemon.plugins.media-keys"
_SCHEMA = f"{_MEDIA_KEYS}.custom-keybinding:{CUSTOM_PATH}"


def build_gsettings_commands(
    binding: str, command: str = "linux-whisper-stt toggle"
) -> list[list[str]]:
    return [
        ["gsettings", "set", _MEDIA_KEYS, "custom-keybindings", f"['{CUSTOM_PATH}']"],
        ["gsettings", "set", _SCHEMA, "name", "linux-whisper-stt toggle"],
        ["gsettings", "set", _SCHEMA, "command", command],
        ["gsettings", "set", _SCHEMA, "binding", binding],
    ]


def register_shortcut(binding: str, runner=subprocess.run) -> None:
    for cmd in build_gsettings_commands(binding):
        runner(cmd, check=True)
