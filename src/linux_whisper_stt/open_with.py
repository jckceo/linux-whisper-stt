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
        "audio/wav",
        "audio/webm",
        "audio/x-flac",
        "audio/x-m4a",
        "audio/x-wav",
        "video/mp2t",
        "video/mp4",
        "video/mpeg",
        "video/ogg",
        "video/quicktime",
        "video/webm",
        "video/x-flv",
        "video/x-matroska",
        "video/x-msvideo",
        "video/x-ms-wmv",
    )


def desktop_entry_text(entrypoint: str) -> str:
    mime_line = "".join(f"{mime_type};" for mime_type in mime_types())
    return f"""[Desktop Entry]
Type=Application
Name=Transcribe with linux-whisper-stt
Comment=Transcribe audio and video files with linux-whisper-stt
Exec={entrypoint} transcribe-file %f
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
        applications_dir = Path(os.path.expanduser("~/.local/share/applications"))
    path = applications_dir / DESKTOP_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desktop_entry_text(entrypoint))
    path.chmod(0o644)
    return path
