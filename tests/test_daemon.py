from linux_whisper_stt.config import Config
from linux_whisper_stt.controller import State
from linux_whisper_stt.daemon import (
    build_controller,
    build_result_popup_fn,
    make_ipc_handler,
    schedule_result_popup,
)
from linux_whisper_stt.jobs import TranscriptionJobRunner


class FakeComponent:
    pass


class FakeIndicator:
    def __init__(self):
        self.states = []

    def set_state(self, state, detail=""):
        self.states.append((state, detail))


class FakeHistoryStore:
    def __init__(self, _config):
        self.marked_stale_failed = False

    def mark_stale_processing_failed(self):
        self.marked_stale_failed = True


def patch_build_controller_components(monkeypatch, history_factory=None):
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
        history_factory or FakeHistoryStore,
    )


def test_build_controller_marks_stale_processing_history_failed(monkeypatch):
    history = FakeHistoryStore(Config())
    patch_build_controller_components(monkeypatch, lambda _config: history)

    build_controller(Config(), FakeIndicator(), lambda fn: fn())

    assert history.marked_stale_failed is True


def test_build_controller_wires_file_job_runner(monkeypatch):
    patch_build_controller_components(monkeypatch)

    controller = build_controller(Config(), FakeIndicator(), lambda fn: fn())

    assert isinstance(controller.file_jobs, TranscriptionJobRunner)
    controller.file_jobs.progress_fn(type("Progress", (), {"state": "transcribing"})())
    assert controller.indicator.states[-1][0] == State.TRANSCRIBING


def test_build_controller_accepts_popup_fn(monkeypatch):
    patch_build_controller_components(monkeypatch)

    popups = []
    controller = build_controller(
        Config(), FakeIndicator(), lambda fn: fn(), popup_fn=popups.append
    )

    event = object()
    controller.file_jobs.popup_fn(event)

    assert popups == [event]


def test_schedule_result_popup_uses_launcher_on_idle():
    event = object()
    idle_callbacks = []
    launched = []

    result = schedule_result_popup(
        event,
        idle_add=idle_callbacks.append,
        popup_launcher=launched.append,
    )

    assert result is None
    assert launched == []
    assert idle_callbacks[0]() is False
    assert launched == [event]


def test_build_result_popup_fn_defaults_to_subprocess_launcher(monkeypatch):
    import linux_whisper_stt.ui.result_window

    event = object()
    idle_callbacks = []
    launched = []
    monkeypatch.setattr(
        linux_whisper_stt.ui.result_window,
        "show_result_window_in_subprocess",
        launched.append,
    )

    popup_fn = build_result_popup_fn(idle_callbacks.append)
    result = popup_fn(event)

    assert result is None
    assert launched == []
    assert idle_callbacks[0]() is False
    assert launched == [event]


def test_transcribe_file_timeout_cancels_queued_idle_callback():
    queued_callbacks = []

    class Controller:
        def __init__(self):
            self.started = []

        def transcribe_file(self, path, created_by):
            self.started.append((path, created_by))
            return {"accepted": True, "state": "transcribing"}

        def status(self):
            return {"state": "idle"}

    controller = Controller()
    handler = make_ipc_handler(
        controller,
        idle_add=queued_callbacks.append,
        request_timeout=0,
    )

    result = handler(
        '{"command": "transcribe-file", "path": "/tmp/audio.mp3", "created_by": "cli"}'
    )

    assert result == {
        "accepted": False,
        "state": "idle",
        "error": "request timed out",
    }
    assert controller.started == []
    assert len(queued_callbacks) == 1
    assert queued_callbacks[0]() is False
    assert controller.started == []


def test_transcribe_file_immediate_timeout_returns_timeout_error():
    class Controller:
        def __init__(self):
            self.started = []

        def transcribe_file(self, path, created_by):
            self.started.append((path, created_by))
            return {"accepted": True, "state": "transcribing"}

        def status(self):
            return {"state": "idle"}

    controller = Controller()
    handler = make_ipc_handler(
        controller,
        idle_add=lambda fn: fn(),
        request_timeout=0,
    )

    result = handler(
        '{"command": "transcribe-file", "path": "/tmp/audio.mp3", "created_by": "cli"}'
    )

    assert result == {
        "accepted": False,
        "state": "idle",
        "error": "request timed out",
    }
    assert controller.started == []


def test_structured_unknown_command_returns_error():
    class Controller:
        def status(self):
            return {"state": "idle", "last_error": ""}

    handler = make_ipc_handler(Controller(), lambda fn: fn())

    assert handler('{"command": "bogus"}') == {"error": "unknown command: bogus"}
