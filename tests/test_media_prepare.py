from pathlib import Path

from linux_whisper_stt.media.prepare import (
    PreparedMedia,
    build_extract_audio_command,
    build_ffprobe_duration_command,
    classify_source,
    prepare_media,
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
