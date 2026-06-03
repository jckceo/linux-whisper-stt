from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

OPENAI_HARD_UPLOAD_LIMIT_BYTES = 25 * 1024 * 1024
OPENAI_TARGET_UPLOAD_BYTES = 22 * 1024 * 1024


@dataclass(frozen=True)
class ChunkPlan:
    index: int
    start_seconds: float
    duration_seconds: float


def estimate_mp3_bytes(duration_seconds: float, bitrate_kbps: int = 64) -> int:
    return math.ceil(duration_seconds * bitrate_kbps * 1000 / 8)


def plan_chunks(
    duration_seconds: float,
    estimated_bytes: int,
    target_bytes: int = OPENAI_TARGET_UPLOAD_BYTES,
) -> list[ChunkPlan]:
    if target_bytes <= 0 or target_bytes > OPENAI_HARD_UPLOAD_LIMIT_BYTES:
        raise ValueError("target_bytes must be between 1 and OpenAI hard upload limit")
    if duration_seconds <= 0:
        return [ChunkPlan(index=0, start_seconds=0.0, duration_seconds=0.0)]
    count = max(1, math.ceil(estimated_bytes / target_bytes))
    chunk_duration = duration_seconds / count
    rounded_chunk_duration = round(chunk_duration, 3)
    if rounded_chunk_duration <= 0:
        raise ValueError("chunk duration too small")

    chunks: list[ChunkPlan] = []
    for i in range(count):
        start_seconds = round(i * chunk_duration, 3)
        duration = (
            round(duration_seconds - start_seconds, 3)
            if i == count - 1
            else rounded_chunk_duration
        )
        if duration <= 0:
            raise ValueError("chunk duration too small")
        chunks.append(
            ChunkPlan(
                index=i,
                start_seconds=start_seconds,
                duration_seconds=duration,
            )
        )
    return chunks


_SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)")


def parse_silencedetect(stderr: str) -> list[tuple[float, float]]:
    """Pair ffmpeg silencedetect start/end markers into (start, end) intervals."""
    silences: list[tuple[float, float]] = []
    pending: float | None = None
    for line in stderr.splitlines():
        start = _SILENCE_START.search(line)
        if start:
            pending = float(start.group(1))
            continue
        end = _SILENCE_END.search(line)
        if end and pending is not None:
            silences.append((pending, float(end.group(1))))
            pending = None
    return silences


def plan_silence_chunks(
    duration_seconds: float,
    silences: list[tuple[float, float]],
    target_seconds: float = 55.0,
    min_seconds: float = 20.0,
) -> list[ChunkPlan]:
    """Plan chunks cut only at silence midpoints, never mid-speech.

    Cuts at the midpoint of the first silence at/after each running target. If no
    qualifying silence exists, no cut is made (the chunk just runs longer), so a word
    is never split. A too-short trailing chunk is merged into the previous one.
    """
    if duration_seconds <= 0:
        return [ChunkPlan(index=0, start_seconds=0.0, duration_seconds=0.0)]

    midpoints = [
        (start + end) / 2
        for start, end in silences
        if 0.0 < (start + end) / 2 < duration_seconds
    ]
    cuts: list[float] = []
    last = 0.0
    for midpoint in midpoints:
        if midpoint - last >= target_seconds:
            cuts.append(round(midpoint, 3))
            last = midpoint

    boundaries = [0.0, *cuts, round(duration_seconds, 3)]
    spans = [(boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)]
    if len(spans) >= 2 and (spans[-1][1] - spans[-1][0]) < min_seconds:
        spans = spans[:-2] + [(spans[-2][0], spans[-1][1])]

    return [
        ChunkPlan(
            index=i,
            start_seconds=round(start, 3),
            duration_seconds=round(end - start, 3),
        )
        for i, (start, end) in enumerate(spans)
    ]


def build_export_chunk_command(source: Path, destination: Path, chunk: ChunkPlan) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-ss",
        f"{chunk.start_seconds:.3f}",
        "-t",
        f"{chunk.duration_seconds:.3f}",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "64k",
        str(destination),
    ]


def export_chunks(
    source: Path,
    chunk_dir: Path,
    chunks: list[ChunkPlan],
    runner=subprocess.run,
) -> list[Path]:
    chunk_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for chunk in chunks:
        destination = chunk_dir / f"chunk-{chunk.index:03d}.mp3"
        proc = runner(
            build_export_chunk_command(source, destination, chunk),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            for path in [*paths, destination]:
                path.unlink(missing_ok=True)
            raise RuntimeError((proc.stderr or "ffmpeg chunk export failed").strip())
        paths.append(destination)
    return paths


def merge_transcripts(parts: list[str], separator: str = "\n\n") -> str:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return separator.join(cleaned)


def build_silencedetect_command(
    source: Path, noise_db: int = 30, min_silence: float = 0.4
) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(source),
        "-af",
        f"silencedetect=noise=-{noise_db}dB:d={min_silence}",
        "-f",
        "null",
        "-",
    ]


def detect_silences(
    source: Path,
    runner=subprocess.run,
    noise_db: int = 30,
    min_silence: float = 0.4,
) -> list[tuple[float, float]]:
    """Run ffmpeg silencedetect and return (start, end) silence intervals. [] on failure.

    Failure includes a non-zero exit and the runner raising (e.g. ffmpeg not installed).
    """
    try:
        proc = runner(
            build_silencedetect_command(source, noise_db, min_silence),
            capture_output=True,
            text=True,
        )
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    return parse_silencedetect(proc.stderr or "")
