from pathlib import Path

import pytest

from linux_whisper_stt.config import Config
from linux_whisper_stt.controller import Controller
from linux_whisper_stt.history import HistoryEvent, HistoryStore


def test_save_writes_v2_microphone_event(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    wav = tmp_path / "rec.wav"
    wav.write_bytes(b"RIFFDATA")
    dest = HistoryStore(cfg).save(wav, "ciao mondo", stamp="20260529-120000")
    assert dest.parent.name.startswith("20260529-120000-")
    assert len(dest.parent.name.removeprefix("20260529-120000-")) == 8
    assert dest == tmp_path / "hist" / dest.parent.name / "audio.wav"
    assert dest.read_bytes() == b"RIFFDATA"
    assert (dest.parent / "transcript.txt").read_text() == "ciao mondo"


def test_disabled_does_nothing(tmp_path):
    cfg = Config()
    cfg.history.enabled = False
    cfg.history.dir = str(tmp_path / "hist")
    wav = tmp_path / "rec.wav"
    wav.write_bytes(b"x")
    assert HistoryStore(cfg).save(wav, "x", stamp="s") is None
    assert not (tmp_path / "hist").exists()


class _Rec:
    def __init__(self, wav):
        self._wav = wav

    def start(self):
        pass

    def stop(self):
        return self._wav


class _Trans:
    def transcribe(self, wav_path, language):
        return "ciao"


class _Result:
    pasted = True
    message = "Pasted"


class _Out:
    def deliver(self, text):
        return _Result()


class _Ind:
    def set_state(self, state, detail=""):
        pass


class _Snd:
    def play_start(self):
        pass

    def play_stop(self):
        pass


def test_controller_calls_history(tmp_path):
    wav = tmp_path / "rec.wav"
    wav.write_bytes(b"data")
    saved = []

    class FakeHistory:
        def save(self, wav_path, text):
            saved.append((wav_path, text))

    c = Controller(_Rec(wav), _Trans(), _Out(), _Ind(), _Snd(), Config(), history=FakeHistory())
    c.toggle()
    c.toggle()
    assert saved == [(wav, "ciao")]


def test_save_event_writes_event_directory(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    source_audio = tmp_path / "source.wav"
    source_audio.write_bytes(b"RIFFDATA")

    store = HistoryStore(cfg)
    event = store.create_event(
        source_type="audio_file",
        created_by="tray",
        original_path=Path("/home/me/meeting.mp4"),
        engine="openai",
        model="gpt-4o-mini-transcribe",
        language="it",
    )
    completed = store.complete_event(
        event.id, source_audio, "ciao mondo", duration_seconds=12.5
    )

    event_dir = tmp_path / "hist" / event.id
    assert isinstance(completed, HistoryEvent)
    assert completed.status == "completed"
    assert (event_dir / "event.json").exists()
    assert (event_dir / "audio.wav").read_bytes() == b"RIFFDATA"
    assert (event_dir / "transcript.txt").read_text(encoding="utf-8") == "ciao mondo"
    assert completed.original_name == "meeting.mp4"
    assert completed.duration_seconds == 12.5


def test_list_events_includes_v2_and_legacy_pairs(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    store = HistoryStore(cfg)

    legacy_wav = tmp_path / "hist" / "20260529-120000.wav"
    legacy_wav.parent.mkdir(parents=True)
    legacy_wav.write_bytes(b"legacy")
    (tmp_path / "hist" / "20260529-120000.txt").write_text(
        "legacy text", encoding="utf-8"
    )

    source_audio = tmp_path / "source.wav"
    source_audio.write_bytes(b"new")
    event = store.create_event(
        source_type="microphone",
        created_by="dictation",
        original_path=None,
        engine="openai",
        model="gpt-4o-mini-transcribe",
        language="auto",
    )
    store.complete_event(event.id, source_audio, "new text")

    events = store.list_events()
    assert [e.transcript_text for e in events] == ["new text", "legacy text"]
    assert events[0].source_type == "microphone"
    assert events[1].legacy is True


def test_delete_event_removes_v2_directory_but_not_original_file(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    original = tmp_path / "original.wav"
    original.write_bytes(b"original")
    prepared = tmp_path / "prepared.wav"
    prepared.write_bytes(b"prepared")
    store = HistoryStore(cfg)
    event = store.create_event(
        source_type="audio_file",
        created_by="cli",
        original_path=original,
        engine="openai",
        model="gpt-4o-mini-transcribe",
        language="auto",
    )
    store.complete_event(event.id, prepared, "text")

    store.delete_event(event.id)

    assert original.exists()
    assert not (tmp_path / "hist" / event.id).exists()


def test_update_event_rejects_legacy_events(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    store = HistoryStore(cfg)
    legacy_wav = tmp_path / "hist" / "20260529-120000.wav"
    legacy_wav.parent.mkdir(parents=True)
    legacy_wav.write_bytes(b"legacy")
    (tmp_path / "hist" / "20260529-120000.txt").write_text(
        "legacy text", encoding="utf-8"
    )

    legacy_event = store.list_events()[0]

    with pytest.raises(ValueError, match="legacy history events are read-only"):
        store.update_event(legacy_event)
    assert not (tmp_path / "hist" / "20260529-120000" / "event.json").exists()


def test_list_events_sorts_by_created_at_not_metadata_mtime(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    store = HistoryStore(cfg)

    older = store.create_event(
        source_type="microphone",
        created_by="dictation",
        original_path=None,
        engine="openai",
        model="gpt-4o-mini-transcribe",
        language="auto",
    )
    newer = store.create_event(
        source_type="audio_file",
        created_by="tray",
        original_path=Path("/home/me/newer.wav"),
        engine="openai",
        model="gpt-4o-mini-transcribe",
        language="auto",
    )
    newer.created_at = "2026-05-29T12:00:00"
    store.update_event(newer)
    older.created_at = "2026-05-29T11:00:00"
    store.update_event(older)

    events = store.list_events()

    assert [event.id for event in events[:2]] == [newer.id, older.id]
