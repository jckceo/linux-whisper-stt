from linux_whisper_stt.config import Config
from linux_whisper_stt.controller import State
from linux_whisper_stt.daemon import build_controller, make_ipc_handler
from linux_whisper_stt.jobs import TranscriptionJobRunner


class FakeComponent:
    pass


class FakeIndicator:
    def __init__(self):
        self.states = []

    def set_state(self, state, detail=""):
        self.states.append((state, detail))


def test_build_controller_wires_file_job_runner(monkeypatch):
    import linux_whisper_stt.audio.recorder
    import linux_whisper_stt.history
    import linux_whisper_stt.output.manager
    import linux_whisper_stt.transcribe.local_backend
    import linux_whisper_stt.transcribe.manager
    import linux_whisper_stt.transcribe.openai_backend

    monkeypatch.setattr(
        linux_whisper_stt.audio.recorder, "Recorder", lambda **_kwargs: FakeComponent()
    )
    monkeypatch.setattr(
        linux_whisper_stt.transcribe.openai_backend,
        "OpenAITranscriber",
        lambda **_kwargs: FakeComponent(),
    )
    monkeypatch.setattr(
        linux_whisper_stt.transcribe.local_backend.LocalWhisperCppTranscriber,
        "from_config",
        lambda _config: FakeComponent(),
    )
    monkeypatch.setattr(
        linux_whisper_stt.transcribe.manager,
        "TranscriptionManager",
        lambda *_args, **_kwargs: FakeComponent(),
    )
    monkeypatch.setattr(
        linux_whisper_stt.output.manager,
        "OutputManager",
        lambda _config: FakeComponent(),
    )
    monkeypatch.setattr(
        "linux_whisper_stt.daemon.Sounds", lambda *_args, **_kwargs: FakeComponent()
    )
    monkeypatch.setattr(
        linux_whisper_stt.history,
        "HistoryStore",
        lambda _config: FakeComponent(),
    )

    controller = build_controller(Config(), FakeIndicator(), lambda fn: fn())

    assert isinstance(controller.file_jobs, TranscriptionJobRunner)
    controller.file_jobs.progress_fn(type("Progress", (), {"state": "transcribing"})())
    assert controller.indicator.states[-1][0] == State.TRANSCRIBING


def test_structured_unknown_command_returns_error():
    class Controller:
        def status(self):
            return {"state": "idle", "last_error": ""}

    handler = make_ipc_handler(Controller(), lambda fn: fn())

    assert handler('{"command": "bogus"}') == {"error": "unknown command: bogus"}
