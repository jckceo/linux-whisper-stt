from __future__ import annotations

import subprocess

from ..cli import entrypoint
from ..assets import asset_path
from ..controller import State

_ICON_NAMES = {
    State.IDLE: "idle",
    State.RECORDING: "recording",
    State.TRANSCRIBING: "busy",
    State.PASTING: "busy",
    State.ERROR: "error",
}


def icon_for_state(state: State) -> str:
    return _ICON_NAMES[state]


def build_settings_command(entrypoint_fn=entrypoint) -> list[str]:
    return [entrypoint_fn(), "setup"]


def open_settings_once(
    current_process,
    popen_fn=subprocess.Popen,
    command_fn=build_settings_command,
):
    if current_process is not None and current_process.poll() is None:
        return current_process
    return popen_fn(command_fn())


class PrintIndicator:
    """Headless indicator used by --dry-run and tests."""

    def __init__(self):
        self.last = None

    def set_state(self, state: State, detail: str = "") -> None:
        self.last = (state, detail)
        print(f"[state] {state.value} {detail}".rstrip())


class TrayIndicator:
    """AppIndicator-based tray icon. GTK 3 + AyatanaAppIndicator3."""

    def __init__(self):
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator
        from gi.repository import GLib, Gtk

        self._Gtk = Gtk
        self._GLib = GLib
        self.controller = None
        self._settings_process = None
        self.indicator = AppIndicator.Indicator.new(
            "linux-whisper-stt",
            str(asset_path("icons", "idle.png")),
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._status_item = None
        self._build_menu()

    def bind_controller(self, controller) -> None:
        self.controller = controller

    def _build_menu(self) -> None:
        Gtk = self._Gtk
        menu = Gtk.Menu()

        self._status_item = Gtk.MenuItem(label="Idle")
        self._status_item.set_sensitive(False)
        menu.append(self._status_item)

        toggle_item = Gtk.MenuItem(label="Start / Stop recording")
        toggle_item.connect("activate", lambda *_: self.controller and self.controller.toggle())
        menu.append(toggle_item)

        settings_item = Gtk.MenuItem(label="Settings…")
        settings_item.connect("activate", self._open_settings)
        menu.append(settings_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda *_: self._Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        self.indicator.set_menu(menu)

    def _open_settings(self, *_):
        self._settings_process = open_settings_once(self._settings_process)

    def set_state(self, state: State, detail: str = "") -> None:
        # Called from worker threads -> marshal onto GTK main loop.
        self._GLib.idle_add(self._apply_state, state, detail)

    def _apply_state(self, state: State, detail: str):
        self.indicator.set_icon_full(str(asset_path("icons", icon_for_state(state) + ".png")), state.value)
        label = state.value.capitalize()
        if detail:
            label += f" — {detail}"
        if self._status_item is not None:
            self._status_item.set_label(label)
        return False  # one-shot idle callback
