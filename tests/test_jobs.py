from pathlib import Path

from linux_whisper_stt.config import Config
from linux_whisper_stt.history import HistoryStore
from linux_whisper_stt.jobs import JobProgress, TranscriptionJobRunner
from linux_whisper_stt.media.prepare import PreparedMedia


class FakeBackend:
    def __init__(self, text="hello"):
        self.text = text
        self.calls = []

    def transcribe(self, wav_path, language):
        self.calls.append((Path(wav_path), language))
        return self.text


def test_file_job_saves_history_copies_clipboard_and_requests_popup(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")
    prepared_event_dirs = []
    copied = []
    popups = []
    progress = []

    def prepare_fn(path, event_dir):
        assert path == source
        prepared_event_dirs.append(event_dir)
        prepared_audio = event_dir / "audio.wav"
        prepared_audio.write_bytes(b"RIFF")
        return PreparedMedia("audio_file", prepared_audio, 44.0)

    runner = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FakeBackend("transcribed text")},
        prepare_fn=prepare_fn,
        copy_fn=copied.append,
        popup_fn=popups.append,
        progress_fn=progress.append,
    )

    event = runner.run_file_job(source, created_by="tray")

    assert event.status == "completed"
    assert event.source_type == "audio_file"
    assert event.transcript_text == "transcribed text"
    assert prepared_event_dirs == [Path(cfg.history.dir) / event.id]
    assert copied == ["transcribed text"]
    assert popups == [event]
    assert JobProgress("completed", event.id, "Completed") in progress


def test_file_job_failure_marks_event_failed(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "bad.mp4"
    source.write_bytes(b"bad")

    def prepare_fn(path, event_dir):
        raise RuntimeError("ffmpeg failed")

    runner = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FakeBackend()},
        prepare_fn=prepare_fn,
        copy_fn=lambda text: None,
        popup_fn=lambda event: None,
        progress_fn=lambda progress: None,
    )

    event = runner.run_file_job(source, created_by="open_with")

    assert event.status == "failed"
    assert event.error == "ffmpeg failed"
