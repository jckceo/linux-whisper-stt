from pathlib import Path

from linux_whisper_stt.media.chunking import (
    ChunkPlan,
    build_export_chunk_command,
    merge_transcripts,
    plan_chunks,
)


def test_plan_chunks_returns_single_chunk_when_under_limit():
    chunks = plan_chunks(
        duration_seconds=120,
        estimated_bytes=10_000_000,
        target_bytes=22_000_000,
    )
    assert chunks == [ChunkPlan(index=0, start_seconds=0.0, duration_seconds=120.0)]


def test_plan_chunks_allows_positional_duration_and_estimated_bytes():
    chunks = plan_chunks(120, 10_000_000, target_bytes=22_000_000)
    assert chunks == [ChunkPlan(index=0, start_seconds=0.0, duration_seconds=120.0)]


def test_plan_chunks_splits_by_estimated_size():
    chunks = plan_chunks(
        duration_seconds=600,
        estimated_bytes=60_000_000,
        target_bytes=20_000_000,
    )
    assert chunks == [
        ChunkPlan(index=0, start_seconds=0.0, duration_seconds=200.0),
        ChunkPlan(index=1, start_seconds=200.0, duration_seconds=200.0),
        ChunkPlan(index=2, start_seconds=400.0, duration_seconds=200.0),
    ]


def test_build_export_chunk_command_uses_mp3():
    cmd = build_export_chunk_command(
        Path("audio.wav"),
        Path("chunks/chunk-000.mp3"),
        ChunkPlan(index=0, start_seconds=10.0, duration_seconds=20.0),
    )
    assert cmd == [
        "ffmpeg",
        "-y",
        "-ss",
        "10.000",
        "-t",
        "20.000",
        "-i",
        "audio.wav",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "64k",
        "chunks/chunk-000.mp3",
    ]


def test_merge_transcripts_keeps_order_and_spacing():
    assert merge_transcripts([" uno ", "", "due\n", "tre"]) == "uno\n\ndue\n\ntre"
