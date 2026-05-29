from __future__ import annotations

import json
import subprocess
import sys
import threading
from dataclasses import asdict

from linux_whisper_stt.history import HistoryEvent
from linux_whisper_stt.output.clipboard import copy_to_clipboard
from linux_whisper_stt.tray.indicator import build_settings_command


def popup_title_for_event(event) -> str:
    name = event.original_name or event.id
    if event.status == "failed":
        return f"Transcription failed: {name}"
    return f"Transcription complete: {name}"


def result_window_subprocess_command(
    python_executable: str = sys.executable,
) -> list[str]:
    return [
        python_executable,
        "-m",
        "linux_whisper_stt.ui.result_window",
        "--show",
    ]


def show_result_window_in_subprocess(
    event: HistoryEvent,
    popen_fn=subprocess.Popen,
    command_fn=result_window_subprocess_command,
    reap_fn=None,
):
    process = popen_fn(command_fn(), stdin=subprocess.PIPE, text=True)
    if reap_fn is None:
        reap_fn = reap_process_nonblocking
    try:
        if process.stdin is None:
            raise RuntimeError("result window subprocess stdin is unavailable")
        process.stdin.write(json.dumps(asdict(event)))
        process.stdin.close()
    finally:
        reap_fn(process)
    return process


def reap_process_nonblocking(process, thread_factory=threading.Thread) -> None:
    thread = thread_factory(target=process.wait, daemon=True)
    thread.start()


def open_history_from_popup(
    _event_id,
    popen_fn=subprocess.Popen,
    command_fn=build_settings_command,
):
    return popen_fn(command_fn())


def copy_result_text(text: str, copy_fn=copy_to_clipboard) -> None:
    copy_fn(text or "")


def show_result_window(event, open_history_fn=None, copy_fn=copy_to_clipboard) -> None:
    import gi

    gi.require_version("Adw", "1")
    gi.require_version("Gtk", "4.0")
    from gi.repository import Adw, Gtk

    Adw.init()
    if open_history_fn is None:
        open_history_fn = open_history_from_popup

    app = Adw.Application()

    def activate(application):
        window = Adw.ApplicationWindow(application=application)
        window.set_title(popup_title_for_event(event))
        window.set_default_size(720, 520)
        window.connect("close-request", lambda *_: application.quit() or False)

        text = _result_text(event)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_hexpand(True)

        buffer = Gtk.TextBuffer()
        buffer.set_text(text or "")
        text_view = Gtk.TextView(buffer=buffer)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroller.set_child(text_view)
        box.append(scroller)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)

        copy_button = Gtk.Button(label="Copy")
        copy_button.connect(
            "clicked",
            lambda *_: copy_result_text(text, copy_fn=copy_fn),
        )
        buttons.append(copy_button)

        history_button = Gtk.Button(label="Open history")
        history_button.connect("clicked", lambda *_: open_history_fn(event.id))
        buttons.append(history_button)

        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda *_: window.close())
        buttons.append(close_button)

        box.append(buttons)
        window.set_content(box)
        window.present()

    app.connect("activate", activate)
    app.run([])


def _result_text(event) -> str:
    return event.error if event.status == "failed" else event.transcript_text


def _event_from_stdin(stdin) -> HistoryEvent:
    return HistoryEvent(**json.loads(stdin.read()))


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv != ["--show"]:
        return 2
    show_result_window(_event_from_stdin(sys.stdin))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
