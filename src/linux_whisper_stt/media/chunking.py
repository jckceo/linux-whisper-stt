from __future__ import annotations

import math
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


def merge_transcripts(parts: list[str]) -> str:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return "\n\n".join(cleaned)
