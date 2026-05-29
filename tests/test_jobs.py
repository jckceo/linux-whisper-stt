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


def _unchunked_paths(audio_path, duration_seconds, event_dir):
    return [Path(audio_path)]


def test_file_job_saves_history_copies_clipboard_and_requests_popup(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")
    backend = FakeBackend("transcribed text")
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
        backends={"openai": backend},
        prepare_fn=prepare_fn,
        copy_fn=copied.append,
        popup_fn=popups.append,
        progress_fn=progress.append,
        chunk_paths_fn=_unchunked_paths,
    )

    event = runner.run_file_job(source, created_by="tray")

    assert event.status == "completed"
    assert event.source_type == "audio_file"
    assert event.transcript_text == "transcribed text"
    history_event_dir = Path(cfg.history.dir) / event.id
    assert len(prepared_event_dirs) == 1
    assert prepared_event_dirs[0] != history_event_dir
    assert not prepared_event_dirs[0].exists()
    assert backend.calls == [(prepared_event_dirs[0] / "audio.wav", "auto")]
    assert (history_event_dir / "audio.wav").read_bytes() == b"RIFF"
    assert event.audio_path == str(history_event_dir / "audio.wav")
    assert copied == ["transcribed text"]
    assert popups == [event]
    assert [item.state for item in progress] == [
        "preparing",
        "transcribing",
        "merging",
        "completed",
    ]
    assert JobProgress("completed", event.id, "Completed") in progress
    assert (
        Path(cfg.history.dir) / event.id / "transcript.txt"
    ).read_text(encoding="utf-8") == "transcribed text"
    assert HistoryStore(cfg).load_event(event.id).transcript_text == "transcribed text"


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


def test_failed_file_job_does_not_leave_prepared_media_in_history(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    cfg.general.engine = "openai"
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")

    def prepare_fn(path, event_dir):
        prepared_audio = event_dir / "audio.wav"
        prepared_audio.write_bytes(b"RIFF")
        return PreparedMedia("audio_file", prepared_audio, 8.0)

    def chunk_paths_fn(audio_path, duration_seconds, event_dir):
        chunk_path = event_dir / "chunks" / "chunk-000.mp3"
        chunk_path.parent.mkdir(parents=True)
        chunk_path.write_bytes(b"chunk")
        return [chunk_path]

    class FailingBackend:
        def transcribe(self, wav_path, language):
            raise RuntimeError("transcription failed")

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FailingBackend()},
        prepare_fn=prepare_fn,
        copy_fn=lambda text: None,
        popup_fn=lambda event: None,
        progress_fn=lambda progress: None,
        chunk_paths_fn=chunk_paths_fn,
    ).run_file_job(source, created_by="tray")

    event_dir = Path(cfg.history.dir) / event.id
    assert event.status == "failed"
    assert event.error == "transcription failed"
    assert (event_dir / "event.json").exists()
    assert not (event_dir / "audio.wav").exists()
    assert not (event_dir / "chunks").exists()


def test_file_job_completion_failure_removes_copied_history_outputs(
    tmp_path, monkeypatch
):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")
    original_write_text = Path.write_text

    def prepare_fn(path, event_dir):
        prepared_audio = event_dir / "audio.wav"
        prepared_audio.write_bytes(b"RIFF")
        return PreparedMedia("audio_file", prepared_audio, 8.0)

    def fail_transcript_write(path, data, *args, **kwargs):
        if path.name == "transcript.txt":
            original_write_text(path, "partial transcript", *args, **kwargs)
            raise RuntimeError("transcript write failed")
        return original_write_text(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_transcript_write)

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FakeBackend("completed text")},
        prepare_fn=prepare_fn,
        copy_fn=lambda text: None,
        popup_fn=lambda event: None,
        progress_fn=lambda progress: None,
        chunk_paths_fn=_unchunked_paths,
    ).run_file_job(source, created_by="tray")

    event_dir = Path(cfg.history.dir) / event.id
    assert event.status == "failed"
    assert event.error == "transcript write failed"
    assert (event_dir / "event.json").exists()
    assert not (event_dir / "audio.wav").exists()
    assert not (event_dir / "transcript.txt").exists()


def test_file_job_copy_failure_keeps_completed_event(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")

    def prepare_fn(path, event_dir):
        prepared_audio = event_dir / "audio.wav"
        prepared_audio.write_bytes(b"RIFF")
        return PreparedMedia("audio_file", prepared_audio, 8.0)

    def copy_fn(text):
        raise RuntimeError("clipboard failed")

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FakeBackend("copied text")},
        prepare_fn=prepare_fn,
        copy_fn=copy_fn,
        chunk_paths_fn=_unchunked_paths,
    ).run_file_job(source, created_by="tray")

    assert event.status == "completed"
    assert event.error == ""
    assert event.transcript_text == "copied text"


def test_file_job_popup_failure_keeps_completed_event(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")
    copied = []

    def prepare_fn(path, event_dir):
        prepared_audio = event_dir / "audio.wav"
        prepared_audio.write_bytes(b"RIFF")
        return PreparedMedia("audio_file", prepared_audio, 8.0)

    def popup_fn(event):
        raise RuntimeError("popup failed")

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FakeBackend("popup text")},
        prepare_fn=prepare_fn,
        copy_fn=copied.append,
        popup_fn=popup_fn,
        chunk_paths_fn=_unchunked_paths,
    ).run_file_job(source, created_by="tray")

    assert event.status == "completed"
    assert event.transcript_text == "popup text"
    assert copied == ["popup text"]


def test_file_job_progress_failure_keeps_completed_event(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")
    copied = []

    def prepare_fn(path, event_dir):
        prepared_audio = event_dir / "audio.wav"
        prepared_audio.write_bytes(b"RIFF")
        return PreparedMedia("audio_file", prepared_audio, 8.0)

    def progress_fn(progress):
        raise RuntimeError("progress failed")

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FakeBackend("progress text")},
        prepare_fn=prepare_fn,
        copy_fn=copied.append,
        progress_fn=progress_fn,
        chunk_paths_fn=_unchunked_paths,
    ).run_file_job(source, created_by="tray")

    assert event.status == "completed"
    assert event.transcript_text == "progress text"
    assert copied == ["progress text"]


def test_file_job_failure_survives_progress_and_popup_failures(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "bad.mp4"
    source.write_bytes(b"bad")

    def prepare_fn(path, event_dir):
        raise RuntimeError("ffmpeg failed")

    def raise_callback_error(value):
        raise RuntimeError("callback failed")

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FakeBackend()},
        prepare_fn=prepare_fn,
        popup_fn=raise_callback_error,
        progress_fn=raise_callback_error,
    ).run_file_job(source, created_by="open_with")

    assert event.status == "failed"
    assert event.error == "ffmpeg failed"


def test_file_job_missing_backend_records_clear_error(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")

    def prepare_fn(path, event_dir):
        prepared_audio = event_dir / "audio.wav"
        prepared_audio.write_bytes(b"RIFF")
        return PreparedMedia("audio_file", prepared_audio, 8.0)

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={},
        prepare_fn=prepare_fn,
        chunk_paths_fn=_unchunked_paths,
    ).run_file_job(source, created_by="tray")

    assert event.status == "failed"
    assert event.error == "No transcription backend configured for engine: openai"


def test_file_job_empty_transcript_is_not_copied(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")
    copied = []
    popups = []

    def prepare_fn(path, event_dir):
        prepared_audio = event_dir / "audio.wav"
        prepared_audio.write_bytes(b"RIFF")
        return PreparedMedia("audio_file", prepared_audio, 8.0)

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FakeBackend("   \n")},
        prepare_fn=prepare_fn,
        copy_fn=copied.append,
        popup_fn=popups.append,
        chunk_paths_fn=_unchunked_paths,
    ).run_file_job(source, created_by="tray")

    assert event.status == "completed"
    assert event.transcript_text == ""
    assert copied == []
    assert popups == [event]


def test_disabled_history_file_job_transcribes_without_history_files(tmp_path):
    cfg = Config()
    cfg.history.enabled = False
    cfg.history.dir = str(tmp_path / "hist")
    cfg.general.language = "it"
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")
    copied = []
    popups = []

    def prepare_fn(path, event_dir):
        assert event_dir != Path(cfg.history.dir) / "disabled"
        prepared_audio = event_dir / "audio.wav"
        prepared_audio.write_bytes(b"RIFF")
        return PreparedMedia("audio_file", prepared_audio, 8.0)

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FakeBackend("disabled text")},
        prepare_fn=prepare_fn,
        copy_fn=copied.append,
        popup_fn=popups.append,
        chunk_paths_fn=_unchunked_paths,
    ).run_file_job(source, created_by="tray")

    assert event.status == "completed"
    assert event.transcript_text == "disabled text"
    assert event.source_type == "audio_file"
    assert event.original_path is None
    assert event.original_name == "meeting.mp3"
    assert event.created_by == "tray"
    assert event.engine == "openai"
    assert event.model == "gpt-4o-mini-transcribe"
    assert event.language == "it"
    assert copied == ["disabled text"]
    assert popups == [event]
    assert not Path(cfg.history.dir).exists()


def test_openai_file_job_chunks_large_audio_and_merges_in_order(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    cfg.general.engine = "openai"
    source = tmp_path / "long.mp3"
    source.write_bytes(b"source")
    prepared_audio = tmp_path / "prepared.wav"
    prepared_audio.write_bytes(b"RIFF")
    chunk_dir = tmp_path / "chunks"
    chunk_paths = [chunk_dir / "chunk-000.mp3", chunk_dir / "chunk-001.mp3"]
    for chunk_path in chunk_paths:
        chunk_path.parent.mkdir(parents=True, exist_ok=True)
        chunk_path.write_bytes(b"chunk")

    class ChunkBackend:
        def __init__(self):
            self.calls = []

        def transcribe(self, path, language):
            self.calls.append(Path(path).name)
            return {"chunk-000.mp3": "first", "chunk-001.mp3": "second"}[
                Path(path).name
            ]

    backend = ChunkBackend()

    runner = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": backend},
        prepare_fn=lambda path, event_dir: PreparedMedia(
            "audio_file", prepared_audio, 600.0
        ),
        copy_fn=lambda text: None,
        popup_fn=lambda event: None,
        progress_fn=lambda progress: None,
        chunk_paths_fn=lambda audio_path, duration_seconds, event_dir: chunk_paths,
    )

    event = runner.run_file_job(source, created_by="cli")

    assert sorted(backend.calls) == ["chunk-000.mp3", "chunk-001.mp3"]
    assert event.transcript_text == "first\n\nsecond"


def test_non_openai_file_job_does_not_invoke_chunking(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    cfg.general.engine = "local"
    source = tmp_path / "meeting.mp3"
    source.write_bytes(b"source")
    prepared_audio = tmp_path / "prepared.wav"
    prepared_audio.write_bytes(b"RIFF")
    backend = FakeBackend("local text")

    def chunk_paths_fn(audio_path, duration_seconds, event_dir):
        raise AssertionError("local backend should not chunk")

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"local": backend},
        prepare_fn=lambda path, event_dir: PreparedMedia(
            "audio_file", prepared_audio, 600.0
        ),
        copy_fn=lambda text: None,
        popup_fn=lambda event: None,
        progress_fn=lambda progress: None,
        chunk_paths_fn=chunk_paths_fn,
    ).run_file_job(source, created_by="cli")

    assert event.status == "completed"
    assert event.transcript_text == "local text"
    assert backend.calls == [(prepared_audio, "auto")]


def test_openai_file_job_chunk_failure_marks_event_failed_without_copying(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    cfg.general.engine = "openai"
    source = tmp_path / "long.mp3"
    source.write_bytes(b"source")
    prepared_audio = tmp_path / "prepared.wav"
    prepared_audio.write_bytes(b"RIFF")
    chunk_path = tmp_path / "chunks" / "chunk-000.mp3"
    chunk_path.parent.mkdir(parents=True)
    chunk_path.write_bytes(b"chunk")
    copied = []
    popups = []

    class FailingBackend:
        def transcribe(self, path, language):
            raise RuntimeError("chunk failed")

    event = TranscriptionJobRunner(
        config=cfg,
        history=HistoryStore(cfg),
        backends={"openai": FailingBackend()},
        prepare_fn=lambda path, event_dir: PreparedMedia(
            "audio_file", prepared_audio, 600.0
        ),
        copy_fn=copied.append,
        popup_fn=popups.append,
        progress_fn=lambda progress: None,
        chunk_paths_fn=lambda audio_path, duration_seconds, event_dir: [chunk_path],
    ).run_file_job(source, created_by="cli")

    assert event.status == "failed"
    assert event.error == "chunk failed"
    assert copied == []
    assert popups == [event]


def test_transcribe_chunks_uses_limited_executor():
    from linux_whisper_stt.jobs import transcribe_chunks

    class Future:
        def __init__(self, value):
            self.value = value

        def result(self):
            return self.value

    class FakeExecutor:
        seen_max_workers = None

        def __init__(self, max_workers):
            FakeExecutor.seen_max_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, path):
            return Future(fn(path))

    class Backend:
        def transcribe(self, path, language):
            return f"{Path(path).name}:{language}"

    parts = transcribe_chunks(
        Backend(),
        [Path("a.mp3"), Path("b.mp3")],
        "it",
        max_workers=2,
        executor_cls=FakeExecutor,
    )

    assert FakeExecutor.seen_max_workers == 2
    assert parts == ["a.mp3:it", "b.mp3:it"]


def test_transcribe_chunks_does_not_submit_later_batches_after_failure():
    from linux_whisper_stt.jobs import transcribe_chunks

    class Future:
        def __init__(self, fn, path):
            self.fn = fn
            self.path = path

        def result(self):
            return self.fn(self.path)

    class FakeExecutor:
        submitted = []

        def __init__(self, max_workers):
            self.max_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, path):
            FakeExecutor.submitted.append(Path(path).name)
            return Future(fn, path)

    class Backend:
        def transcribe(self, path, language):
            if Path(path).name == "a.mp3":
                raise RuntimeError("first batch failed")
            return f"{Path(path).name}:{language}"

    try:
        transcribe_chunks(
            Backend(),
            [Path("a.mp3"), Path("b.mp3"), Path("c.mp3"), Path("d.mp3")],
            "it",
            max_workers=2,
            executor_cls=FakeExecutor,
        )
    except RuntimeError as exc:
        assert str(exc) == "first batch failed"
    else:
        raise AssertionError("expected RuntimeError")

    assert FakeExecutor.submitted == ["a.mp3", "b.mp3"]


def test_build_openai_chunk_paths_uses_estimated_mp3_bytes_for_split(
    tmp_path, monkeypatch
):
    from linux_whisper_stt import jobs

    audio_path = tmp_path / "tiny-input.mp3"
    audio_path.write_bytes(b"x")
    exported = [
        tmp_path / "event" / "chunks" / "chunk-000.mp3",
        tmp_path / "event" / "chunks" / "chunk-001.mp3",
    ]
    captured = {}

    def fake_export_chunks(source, chunk_dir, chunks):
        captured["source"] = source
        captured["chunk_dir"] = chunk_dir
        captured["chunks"] = chunks
        return exported

    monkeypatch.setattr(jobs, "export_chunks", fake_export_chunks)

    chunk_paths = jobs.build_openai_chunk_paths(
        audio_path,
        duration_seconds=7200,
        event_dir=tmp_path / "event",
    )

    assert chunk_paths == exported
    assert captured["source"] == audio_path
    assert captured["chunk_dir"] == tmp_path / "event" / "chunks"
    assert len(captured["chunks"]) > 1


def test_build_openai_chunk_paths_exports_single_mp3_for_short_known_duration(
    tmp_path, monkeypatch
):
    from linux_whisper_stt import jobs

    audio_path = tmp_path / "event" / "audio.wav"
    audio_path.parent.mkdir()
    audio_path.write_bytes(b"RIFF")
    exported = [tmp_path / "event" / "chunks" / "chunk-000.mp3"]
    captured = {}

    def fake_export_chunks(source, chunk_dir, chunks):
        captured["source"] = source
        captured["chunk_dir"] = chunk_dir
        captured["chunks"] = chunks
        return exported

    monkeypatch.setattr(jobs, "export_chunks", fake_export_chunks)

    chunk_paths = jobs.build_openai_chunk_paths(
        audio_path,
        duration_seconds=120,
        event_dir=tmp_path / "event",
    )

    assert chunk_paths == exported
    assert chunk_paths != [audio_path]
    assert captured["source"] == audio_path
    assert captured["chunk_dir"] == tmp_path / "event" / "chunks"
    assert len(captured["chunks"]) == 1
    assert captured["chunks"][0].duration_seconds == 120.0


def test_build_openai_chunk_paths_exports_single_mp3_for_zero_duration(
    tmp_path, monkeypatch
):
    from linux_whisper_stt import jobs

    audio_path = tmp_path / "event" / "audio.wav"
    audio_path.parent.mkdir()
    audio_path.write_bytes(b"RIFF")
    exported = [tmp_path / "event" / "chunks" / "chunk-000.mp3"]
    captured = {}

    def fake_export_chunks(source, chunk_dir, chunks):
        captured["source"] = source
        captured["chunk_dir"] = chunk_dir
        captured["chunks"] = chunks
        return exported

    monkeypatch.setattr(jobs, "export_chunks", fake_export_chunks)

    chunk_paths = jobs.build_openai_chunk_paths(
        audio_path,
        duration_seconds=0.0,
        event_dir=tmp_path / "event",
    )

    assert chunk_paths == exported
    assert chunk_paths != [audio_path]
    assert captured["source"] == audio_path
    assert captured["chunk_dir"] == tmp_path / "event" / "chunks"
    assert len(captured["chunks"]) == 1
    assert captured["chunks"][0].duration_seconds == 0.0
