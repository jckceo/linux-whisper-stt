from pathlib import Path

from linux_whisper_stt.media.chunking import (
    OPENAI_HARD_UPLOAD_LIMIT_BYTES,
    ChunkPlan,
    build_export_chunk_command,
    estimate_mp3_bytes,
    export_chunks,
    merge_transcripts,
    plan_chunks,
)


class Proc:
    def __init__(self, returncode: int, stderr: str = ""):
        self.returncode = returncode
        self.stderr = stderr


def test_estimate_mp3_bytes_uses_duration_and_bitrate():
    assert estimate_mp3_bytes(10, bitrate_kbps=64) == 80_000


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


def test_plan_chunks_uses_remaining_duration_for_final_chunk():
    chunks = plan_chunks(duration_seconds=1.0, estimated_bytes=3, target_bytes=1)
    assert chunks == [
        ChunkPlan(index=0, start_seconds=0.0, duration_seconds=0.333),
        ChunkPlan(index=1, start_seconds=0.333, duration_seconds=0.333),
        ChunkPlan(index=2, start_seconds=0.667, duration_seconds=0.333),
    ]


def test_plan_chunks_rejects_invalid_target_bytes():
    for target_bytes in (0, -1, OPENAI_HARD_UPLOAD_LIMIT_BYTES + 1):
        try:
            plan_chunks(duration_seconds=120, estimated_bytes=10_000, target_bytes=target_bytes)
        except ValueError as exc:
            assert str(exc) == "target_bytes must be between 1 and OpenAI hard upload limit"
        else:
            raise AssertionError("expected ValueError")


def test_plan_chunks_rejects_too_small_positive_chunk_duration():
    try:
        plan_chunks(duration_seconds=0.001, estimated_bytes=10_000, target_bytes=1)
    except ValueError as exc:
        assert str(exc) == "chunk duration too small"
    else:
        raise AssertionError("expected ValueError")


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


def test_export_chunks_returns_paths_and_calls_runner_with_output_options(tmp_path):
    calls = []

    def runner(cmd, capture_output, text):
        calls.append((cmd, capture_output, text))
        destination = Path(cmd[-1])
        destination.write_text("mp3")
        return Proc(returncode=0)

    chunks = [
        ChunkPlan(index=0, start_seconds=0.0, duration_seconds=5.0),
        ChunkPlan(index=1, start_seconds=5.0, duration_seconds=5.0),
    ]
    paths = export_chunks(tmp_path / "audio.wav", tmp_path / "chunks", chunks, runner=runner)

    assert paths == [
        tmp_path / "chunks" / "chunk-000.mp3",
        tmp_path / "chunks" / "chunk-001.mp3",
    ]
    assert calls == [
        (
            build_export_chunk_command(tmp_path / "audio.wav", paths[0], chunks[0]),
            True,
            True,
        ),
        (
            build_export_chunk_command(tmp_path / "audio.wav", paths[1], chunks[1]),
            True,
            True,
        ),
    ]


def test_export_chunks_failure_raises_stderr_and_removes_chunk_outputs(tmp_path):
    chunk_dir = tmp_path / "chunks"
    unrelated = chunk_dir / "keep.txt"
    calls = []

    def runner(cmd, capture_output, text):
        calls.append(cmd)
        destination = Path(cmd[-1])
        destination.write_text("partial")
        if len(calls) == 1:
            return Proc(returncode=0)
        return Proc(returncode=1, stderr="encoder failed")

    chunk_dir.mkdir()
    unrelated.write_text("keep")
    chunks = [
        ChunkPlan(index=0, start_seconds=0.0, duration_seconds=5.0),
        ChunkPlan(index=1, start_seconds=5.0, duration_seconds=5.0),
    ]

    try:
        export_chunks(tmp_path / "audio.wav", chunk_dir, chunks, runner=runner)
    except RuntimeError as exc:
        assert str(exc) == "encoder failed"
    else:
        raise AssertionError("expected RuntimeError")

    assert not (chunk_dir / "chunk-000.mp3").exists()
    assert not (chunk_dir / "chunk-001.mp3").exists()
    assert unrelated.read_text() == "keep"


def test_export_chunks_failure_uses_fallback_message_and_removes_outputs(tmp_path):
    def runner(cmd, capture_output, text):
        Path(cmd[-1]).write_text("partial")
        return Proc(returncode=1)

    try:
        export_chunks(
            tmp_path / "audio.wav",
            tmp_path / "chunks",
            [ChunkPlan(index=0, start_seconds=0.0, duration_seconds=5.0)],
            runner=runner,
        )
    except RuntimeError as exc:
        assert str(exc) == "ffmpeg chunk export failed"
    else:
        raise AssertionError("expected RuntimeError")

    assert not (tmp_path / "chunks" / "chunk-000.mp3").exists()


def test_merge_transcripts_keeps_order_and_spacing():
    assert merge_transcripts([" uno ", "", "due\n", "tre"]) == "uno\n\ndue\n\ntre"
