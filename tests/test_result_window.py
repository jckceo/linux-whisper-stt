from linux_whisper_stt.history import HistoryEvent
from linux_whisper_stt.ui.result_window import (
    gtk_major_version_for_result_window,
    popup_title_for_event,
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


def test_result_window_uses_gtk3_when_already_loaded():
    assert gtk_major_version_for_result_window("3.0") == 3


def test_result_window_defaults_to_gtk4():
    assert gtk_major_version_for_result_window(None) == 4
