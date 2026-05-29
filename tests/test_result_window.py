from linux_whisper_stt.history import HistoryEvent
from linux_whisper_stt.ui.result_window import (
    popup_title_for_event,
    result_window_subprocess_command,
    show_result_window_in_subprocess,
)


def test_popup_title_for_completed_event_uses_original_name():
    event = HistoryEvent(
        id="1",
        created_at="2026-05-29T10:00:00",
        source_type="audio_file",
        status="completed",
        created_by="tray",
        original_name="meeting.mp3",
        transcript_text="hello",
    )
    assert popup_title_for_event(event) == "Transcription complete: meeting.mp3"


def test_popup_title_for_failed_event():
    event = HistoryEvent(
        id="1",
        created_at="2026-05-29T10:00:00",
        source_type="video_file",
        status="failed",
        created_by="open_with",
        original_name="movie.mp4",
        error="ffmpeg failed",
    )
    assert popup_title_for_event(event) == "Transcription failed: movie.mp4"


def test_result_window_subprocess_command_runs_module():
    command = result_window_subprocess_command(python_executable="/abs/python")

    assert command == [
        "/abs/python",
        "-m",
        "linux_whisper_stt.ui.result_window",
        "--show",
    ]


def test_show_result_window_in_subprocess_serializes_event():
    event = HistoryEvent(
        id="1",
        created_at="2026-05-29T10:00:00",
        source_type="audio_file",
        status="completed",
        created_by="tray",
        original_name="meeting.mp3",
        transcript_text="hello",
    )
    launched = {}

    class FakeStdin:
        def __init__(self):
            self.text = ""
            self.closed = False

        def write(self, text):
            self.text += text

        def close(self):
            self.closed = True

    class FakeProcess:
        def __init__(self):
            self.stdin = FakeStdin()

    fake_process = FakeProcess()

    def popen_fn(command, *, stdin, text):
        launched["command"] = command
        launched["stdin"] = stdin
        launched["text"] = text
        return fake_process

    result = show_result_window_in_subprocess(
        event,
        popen_fn=popen_fn,
        command_fn=lambda: ["/abs/python", "-m", "linux_whisper_stt.ui.result_window"],
    )

    assert result is fake_process
    assert launched == {
        "command": ["/abs/python", "-m", "linux_whisper_stt.ui.result_window"],
        "stdin": -1,
        "text": True,
    }
    assert '"original_name": "meeting.mp3"' in fake_process.stdin.text
    assert '"transcript_text": "hello"' in fake_process.stdin.text
    assert fake_process.stdin.closed
