from __future__ import annotations

import threading

from .assets import asset_path
from .config import load_config
from .controller import Controller
from .ipc import IPCServer
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
    return Controller(recorder, transcription, output, indicator, sounds, config, run_async)


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
    def handle(command: str) -> dict:
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
