from __future__ import annotations

import threading
from pathlib import Path

from .assets import asset_path
from .config import load_config
from .controller import Controller, State
from .ipc import IPCServer, parse_message
from .secrets import get_api_key
from .sounds import Sounds


def build_controller(config, indicator, run_async):
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
        popup_fn=lambda _event: None,
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


def run_daemon(dry_run: bool = False) -> int:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk

    config = load_config()

    # Run blocking work (transcription) off the GTK main thread.
    def run_async(fn):
        threading.Thread(target=fn, daemon=True).start()

    if dry_run:
        from .tray.indicator import PrintIndicator

        indicator = PrintIndicator()
    else:
        from .tray.indicator import TrayIndicator

        indicator = TrayIndicator()

    controller = build_controller(config, indicator, run_async)
    if not dry_run:
        indicator.bind_controller(controller)

    # IPC: translate commands to controller calls; reply with status.
    def handle(data: str) -> dict:
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

            GLib.idle_add(apply)
            done.wait(timeout=5)
        elif command == "transcribe-file":
            done = threading.Event()
            result = {}

            def apply():
                try:
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

            GLib.idle_add(apply)
            if not done.wait(timeout=5):
                return {
                    "accepted": False,
                    "state": controller.status().get("state", "?"),
                    "error": "request timed out",
                }
            return result
        return controller.status()

    server = IPCServer(handle)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0
