from dataclasses import dataclass
from pathlib import Path

from linux_whisper_stt.config import Config
from linux_whisper_stt.controller import Controller, State


@dataclass
class FakeDeliveryResult:
    pasted: bool
    message: str


class FakeRecorder:
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self) -> Path:
        self.stopped = True
        return Path("/tmp/rec.wav")


class FakeTranscription:
    def __init__(self, text="hello world", error=None):
        self.text = text
        self.error = error
        self.calls = []

    def transcribe(self, wav_path, language):
        self.calls.append((wav_path, language))
        if self.error:
            raise self.error
        return self.text


class FakeOutput:
    def __init__(self):
        self.delivered = []

    def deliver(self, text):
        self.delivered.append(text)
        return FakeDeliveryResult(pasted=True, message="Pasted")


class FakeIndicator:
    def __init__(self):
        self.states = []

    def set_state(self, state, detail=""):
        self.states.append((state, detail))


class FakeSounds:
    def __init__(self):
        self.events = []

    def play_start(self):
        self.events.append("start")

    def play_stop(self):
        self.events.append("stop")


def make_controller(**overrides):
    recorder = overrides.get("recorder", FakeRecorder())
    transcription = overrides.get("transcription", FakeTranscription())
    output = overrides.get("output", FakeOutput())
    indicator = overrides.get("indicator", FakeIndicator())
    sounds = overrides.get("sounds", FakeSounds())
    config = overrides.get("config", Config())
    c = Controller(recorder, transcription, output, indicator, sounds, config)
    return c, recorder, transcription, output, indicator, sounds


def test_starts_idle():
    c, *_ = make_controller()
    assert c.state == State.IDLE


def test_toggle_from_idle_starts_recording():
    c, recorder, _, _, indicator, sounds = make_controller()
    c.toggle()
    assert c.state == State.RECORDING
    assert recorder.started is True
    assert sounds.events == ["start"]
    assert indicator.states[-1][0] == State.RECORDING


def test_toggle_again_transcribes_and_delivers_then_idle():
    c, recorder, transcription, output, _, sounds = make_controller()
    c.toggle()  # start
    c.toggle()  # stop -> transcribe -> deliver -> idle (run_async is sync in tests)
    assert recorder.stopped is True
    assert sounds.events == ["start", "stop"]
    assert transcription.calls == [(Path("/tmp/rec.wav"), "auto")]
    assert output.delivered == ["hello world"]
    assert c.state == State.IDLE


def test_empty_transcription_returns_to_idle_without_delivering():
    c, _, _, output, _, _ = make_controller(transcription=FakeTranscription(text="   "))
    c.toggle()
    c.toggle()
    assert output.delivered == []
    assert c.state == State.IDLE


def test_transcription_error_enters_error_state():
    err = RuntimeError("API key missing")
    c, _, _, _, indicator, _ = make_controller(transcription=FakeTranscription(error=err))
    c.toggle()
    c.toggle()
    assert c.state == State.ERROR
    assert c.last_error == "API key missing"
    assert indicator.states[-1] == (State.ERROR, "API key missing")


def test_toggle_from_error_starts_new_recording():
    err = RuntimeError("boom")
    c, _, _, _, _, _ = make_controller(transcription=FakeTranscription(error=err))
    c.toggle()
    c.toggle()  # -> ERROR
    c.toggle()  # recover -> RECORDING
    assert c.state == State.RECORDING
    assert c.last_error == ""


def test_sounds_disabled_by_config():
    cfg = Config()
    cfg.general.sounds = False
    c, _, _, _, _, sounds = make_controller(config=cfg)
    c.toggle()
    assert sounds.events == []


def test_status_dict():
    c, *_ = make_controller()
    assert c.status() == {"state": "idle", "last_error": ""}
