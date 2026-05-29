from __future__ import annotations

import ast
import subprocess

from .cli import entrypoint

CUSTOM_PATH = (
    "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"
    "linux-whisper-stt/"
)
_MEDIA_KEYS = "org.gnome.settings-daemon.plugins.media-keys"
_SCHEMA = f"{_MEDIA_KEYS}.custom-keybinding:{CUSTOM_PATH}"


def merge_custom_keybinding_paths(existing: list[str]) -> list[str]:
    paths = list(existing)
    if CUSTOM_PATH not in paths:
        paths.append(CUSTOM_PATH)
    return paths


def read_custom_keybinding_paths(runner=subprocess.run) -> list[str]:
    result = runner(
        ["gsettings", "get", _MEDIA_KEYS, "custom-keybindings"],
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if output.startswith("@as "):
        output = output.removeprefix("@as ").strip()
    try:
        parsed = ast.literal_eval(output)
    except (ValueError, SyntaxError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(path) for path in parsed]


def _format_gsettings_list(paths: list[str]) -> str:
    return f"[{', '.join(repr(path) for path in paths)}]"


def build_gsettings_commands(
    binding: str, command: str | None = None, existing_paths: list[str] | None = None
) -> list[list[str]]:
    if command is None:
        command = f"{entrypoint()} toggle"
    paths = merge_custom_keybinding_paths(existing_paths or [])
    return [
        [
            "gsettings",
            "set",
            _MEDIA_KEYS,
            "custom-keybindings",
            _format_gsettings_list(paths),
        ],
        ["gsettings", "set", _SCHEMA, "name", "linux-whisper-stt toggle"],
        ["gsettings", "set", _SCHEMA, "command", command],
        ["gsettings", "set", _SCHEMA, "binding", binding],
    ]


def register_shortcut(binding: str, runner=subprocess.run) -> None:
    existing_paths = read_custom_keybinding_paths(runner=runner)
    for cmd in build_gsettings_commands(binding, existing_paths=existing_paths):
        runner(cmd, check=True)
