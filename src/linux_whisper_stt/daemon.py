from __future__ import annotations

import threading
import time
from pathlib import Path

from .assets import asset_path
from .config import load_config
from .controller import Controller, State
from .ipc import IPCServer, parse_message
from .secrets import get_api_key
from .sounds import Sounds


def build_controller(config, indicator, run_async, popup_fn=None):
    """Wire all real components into a Controller. Shared by daemon and dry-run."""
    from .audio.recorder import Recorder
    from .output.manager import OutputManager
    from .transcribe.manager import TranscriptionManager
    from .transcribe.openai_backend import OpenAITranscriber

    recorder = Recorder(
        device=config.audio.device,
        samplerate=config.audio.samplerate,
        max_seconds=config.audio.max_seconds,
    )
    openai_backend = OpenAITranscriber(
        api_key_provider=get_api_key, model=config.openai.model
    )
    from .transcribe.local_backend import LocalWhisperCppTranscriber

    backends = {
        "openai": openai_backend,
        "local": LocalWhisperCppTranscriber.from_config(config),
    }
    transcription = TranscriptionManager(config, backends)
    output = OutputManager(config)
    sounds = Sounds(
        config,
        start_path=str(asset_path("sounds", "start.wav")),
        stop_path=str(asset_path("sounds", "stop.wav")),
    )
    from .history import HistoryStore

    history = HistoryStore(config)
    history.mark_stale_processing_failed()
    from .jobs import TranscriptionJobRunner
    from .output.clipboard import copy_to_clipboard

    def report_job_progress(progress):
        detail = getattr(progress, "detail", "")
        if getattr(progress, "state", "") == "failed":
            indicator.set_state(State.ERROR, detail)
        else:
            indicator.set_state(State.TRANSCRIBING, detail)

    file_jobs = TranscriptionJobRunner(
        config=config,
        history=history,
        backends=backends,
        copy_fn=copy_to_clipboard,
        popup_fn=popup_fn or (lambda _event: None),
        progress_fn=report_job_progress,
    )
    return Controller(
        recorder,
        transcription,
        output,
        indicator,
        sounds,
        config,
        run_async=run_async,
        history=history,
        file_jobs=file_jobs,
    )


def schedule_result_popup(event, idle_add, popup_launcher):
    def show_popup():
        popup_launcher(event)
        return False

    return idle_add(show_popup)


def build_result_popup_fn(idle_add, popup_launcher=None):
    if popup_launcher is None:
        from .ui.result_window import show_result_window_in_subprocess

        popup_launcher = show_result_window_in_subprocess

    def popup_fn(event):
        return schedule_result_popup(
            event,
            idle_add=idle_add,
            popup_launcher=popup_launcher,
        )

    return popup_fn


def make_ipc_handler(controller, idle_add, request_timeout: float = 5):
    def handle(data: str) -> dict:
        structured = data.strip().startswith("{")
        payload = parse_message(data)
        command = payload["command"]
        if command in ("toggle", "start", "stop"):
            done = threading.Event()

            def apply():
                try:
                    if command == "toggle":
                        controller.toggle()
                    elif command == "start":
                        controller.start()
                    elif command == "stop":
                        controller.stop()
                finally:
                    done.set()
                return False  # GLib one-shot idle callback

            idle_add(apply)
            done.wait(timeout=5)
        elif command == "transcribe-file":
            done = threading.Event()
            result = {}
            cancelled = threading.Event()
            deadline = time.monotonic() + request_timeout

            def timeout_result() -> dict:
                return {
                    "accepted": False,
                    "state": controller.status().get("state", "?"),
                    "error": "request timed out",
                }

            def apply():
                try:
                    if cancelled.is_set() or time.monotonic() >= deadline:
                        result.update(timeout_result())
                        return False
                    result.update(
                        controller.transcribe_file(
                            Path(payload["path"]),
                            created_by=payload.get("created_by", "cli"),
                        )
                    )
                except Exception as e:
                    result.update(
                        {
                            "accepted": False,
                            "state": controller.status().get("state", "?"),
                            "error": str(e),
                        }
                    )
                finally:
                    done.set()
                return False

            idle_add(apply)
            if not done.wait(timeout=request_timeout):
                cancelled.set()
                return timeout_result()
            return result
        elif structured and command != "status":
            return {"error": f"unknown command: {command}"}
        return controller.status()

    return handle


def run_daemon(dry_run: bool = False) -> int:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk

    config = load_config()

    # Run blocking work (transcription) off the GTK main thread.
    def run_async(fn):
        threading.Thread(target=fn, daemon=True).start()

    popup_fn = None
    if dry_run:
        from .tray.indicator import PrintIndicator

        indicator = PrintIndicator()
    else:
        from .tray.indicator import TrayIndicator

        indicator = TrayIndicator()
        popup_fn = build_result_popup_fn(GLib.idle_add)

    controller = build_controller(config, indicator, run_async, popup_fn=popup_fn)
    if not dry_run:
        indicator.bind_controller(controller)
        indicator.bind_transcribe_file(
            lambda path, created_by: controller.transcribe_file(path, created_by)
        )

    server = IPCServer(make_ipc_handler(controller, GLib.idle_add))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0
