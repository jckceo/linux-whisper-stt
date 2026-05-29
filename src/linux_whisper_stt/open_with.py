from __future__ import annotations

import os
from pathlib import Path

DESKTOP_FILENAME = "linux-whisper-stt-transcribe.desktop"


def mime_types() -> tuple[str, ...]:
    return (
        "audio/aac",
        "audio/flac",
        "audio/m4a",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/opus",
        "audio/vnd.wave",
        "audio/wav",
        "audio/webm",
        "audio/x-flac",
        "audio/x-m4a",
        "audio/x-matroska",
        "audio/x-ms-wma",
        "audio/x-wav",
        "video/mp2t",
        "video/mp4",
        "video/mpeg",
        "video/ogg",
        "video/quicktime",
        "video/vnd.avi",
        "video/webm",
        "video/x-flv",
        "video/x-matroska",
        "video/x-msvideo",
        "video/x-ms-wmv",
    )


def _applications_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / "applications"
    return Path(os.path.expanduser("~/.local/share/applications"))


def _quote_exec_arg(arg: str) -> str:
    escaped = (
        arg.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("$", "\\$")
        .replace("`", "\\`")
        .replace("%", "%%")
    )
    reserved = set(' \t\n"\'\\><~|&;$*?#()`')
    if any(char in reserved for char in arg):
        return f'"{escaped}"'
    return escaped


def desktop_entry_text(entrypoint: str) -> str:
    mime_line = "".join(f"{mime_type};" for mime_type in mime_types())
    exec_line = (
        f"{_quote_exec_arg(entrypoint)} transcribe-file %f --created-by open_with"
    )
    return f"""[Desktop Entry]
Type=Application
Name=Transcribe with linux-whisper-stt
Comment=Transcribe audio and video files with linux-whisper-stt
Exec={exec_line}
MimeType={mime_line}
NoDisplay=true
Terminal=false
Categories=AudioVideo;Audio;Video;
"""


def install_open_with(
    entrypoint: str,
    applications_dir: Path | None = None,
) -> Path:
    if applications_dir is None:
        applications_dir = _applications_dir()
    path = applications_dir / DESKTOP_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desktop_entry_text(entrypoint))
    path.chmod(0o644)
    return path
