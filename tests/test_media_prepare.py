from pathlib import Path
from types import SimpleNamespace

import pytest

from linux_whisper_stt.media.prepare import (
    PreparedMedia,
    build_extract_audio_command,
    build_ffprobe_duration_command,
    classify_source,
    prepare_media,
    read_duration,
)


def test_classify_source_uses_mime_prefix():
    assert classify_source(Path("clip.mp3"), mime_fn=lambda _: "audio/mpeg") == "audio_file"
    assert classify_source(Path("movie.mp4"), mime_fn=lambda _: "video/mp4") == "video_file"
    assert classify_source(Path("notes.txt"), mime_fn=lambda _: "text/plain") == "unsupported"


def test_build_extract_audio_command_outputs_normalized_wav():
    cmd = build_extract_audio_command(Path("input.mp4"), Path("event/audio.wav"))
    assert cmd == [
        "ffmpeg",
        "-y",
        "-i",
        "input.mp4",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "event/audio.wav",
    ]


def test_build_ffprobe_duration_command():
    assert build_ffprobe_duration_command(Path("audio.wav")) == [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        "audio.wav",
    ]


def test_prepare_media_runs_ffmpeg_and_returns_duration(tmp_path):
    calls = []
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")
    event_dir = tmp_path / "event"

    def fake_runner(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class Result:
            returncode = 0
            stderr = ""
            stdout = "123.45\n" if cmd[0] == "ffprobe" else ""

        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"RIFF")
        return Result()

    prepared = prepare_media(
        source,
        event_dir,
        runner=fake_runner,
        mime_fn=lambda _: "video/mp4",
    )

    assert prepared == PreparedMedia(
        source_type="video_file",
        audio_path=event_dir / "audio.wav",
        duration_seconds=123.45,
    )
    assert calls[0][0][0] == "ffmpeg"
    assert calls[1][0][0] == "ffprobe"


def test_prepare_media_rejects_missing_source(tmp_path):
    with pytest.raises(RuntimeError, match="File does not exist"):
        prepare_media(tmp_path / "missing.mp4", tmp_path / "event")


def test_prepare_media_rejects_non_regular_source(tmp_path):
    source = tmp_path / "media_dir.mp4"
    source.mkdir()

    with pytest.raises(RuntimeError, match="Not a regular file"):
        prepare_media(source, tmp_path / "event", mime_fn=lambda _: "video/mp4")


def test_prepare_media_rejects_unsupported_mime(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("not media")

    with pytest.raises(RuntimeError, match="Unsupported file type"):
        prepare_media(source, tmp_path / "event", mime_fn=lambda _: "text/plain")


def test_prepare_media_raises_ffmpeg_stderr_on_failure(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")

    def fake_runner(cmd, **kwargs):
        class Result:
            returncode = 1
            stderr = "decode failed"
            stdout = ""

        return Result()

    with pytest.raises(RuntimeError, match="decode failed"):
        prepare_media(source, tmp_path / "event", runner=fake_runner, mime_fn=lambda _: "video/mp4")


def test_prepare_media_raises_default_message_on_ffmpeg_failure_without_stderr(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")

    def fake_runner(cmd, **kwargs):
        class Result:
            returncode = 1
            stderr = ""
            stdout = ""

        return Result()

    with pytest.raises(RuntimeError, match="ffmpeg failed"):
        prepare_media(source, tmp_path / "event", runner=fake_runner, mime_fn=lambda _: "video/mp4")


def test_prepare_media_removes_partial_audio_on_ffmpeg_failure(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")
    event_dir = tmp_path / "event"
    audio_path = event_dir / "audio.wav"

    def fake_runner(cmd, **kwargs):
        Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[-1]).write_bytes(b"partial")

        class Result:
            returncode = 1
            stderr = "decode failed"
            stdout = ""

        return Result()

    with pytest.raises(RuntimeError, match="decode failed"):
        prepare_media(source, str(event_dir), runner=fake_runner, mime_fn=lambda _: "video/mp4")

    assert not audio_path.exists()


def test_read_duration_returns_none_on_nonzero_ffprobe():
    def fake_runner(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="123.45\n")

    assert read_duration(Path("audio.wav"), runner=fake_runner) is None


def test_read_duration_returns_none_on_unparsable_output():
    def fake_runner(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="not a duration\n")

    assert read_duration(Path("audio.wav"), runner=fake_runner) is None


@pytest.mark.parametrize("stdout", ["nan\n", "inf\n", "-1\n"])
def test_read_duration_returns_none_for_non_finite_or_negative_output(stdout):
    def fake_runner(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout=stdout)

    assert read_duration(Path("audio.wav"), runner=fake_runner) is None
