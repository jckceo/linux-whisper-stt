from __future__ import annotations

import mimetypes
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PreparedMedia:
    source_type: str
    audio_path: Path
    duration_seconds: float | None


def default_mime(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or ""


def classify_source(path: Path, mime_fn=default_mime) -> str:
    mime = mime_fn(path)
    if mime.startswith("audio/"):
        return "audio_file"
    if mime.startswith("video/"):
        return "video_file"
    return "unsupported"


def build_extract_audio_command(source: Path, destination: Path) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(destination),
    ]


def build_ffprobe_duration_command(path: Path) -> list[str]:
    return [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]


def read_duration(path: Path, runner=subprocess.run) -> float | None:
    proc = runner(build_ffprobe_duration_command(path), capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


def prepare_media(
    source: Path,
    event_dir: Path,
    runner=subprocess.run,
    mime_fn=default_mime,
) -> PreparedMedia:
    source = Path(source)
    if not source.exists():
        raise RuntimeError(f"File does not exist: {source}")
    source_type = classify_source(source, mime_fn=mime_fn)
    if source_type == "unsupported":
        raise RuntimeError(f"Unsupported file type: {source}")
    event_dir.mkdir(parents=True, exist_ok=True)
    audio_path = event_dir / "audio.wav"
    proc = runner(build_extract_audio_command(source, audio_path), capture_output=True, text=True)
    if proc.returncode != 0:
        message = (proc.stderr or "ffmpeg failed").strip()
        raise RuntimeError(message)
    return PreparedMedia(
        source_type=source_type,
        audio_path=audio_path,
        duration_seconds=read_duration(audio_path, runner=runner),
    )
