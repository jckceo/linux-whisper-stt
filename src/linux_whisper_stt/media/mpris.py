"""Pause/resume currently-playing MPRIS media players over D-Bus.

Used to silence music/video players while a dictation recording is in progress
so they do not bleed into the captured audio. Talks to the session bus through
``gi.repository.Gio`` (already a dependency via PyGObject), so no extra system
tool (e.g. playerctl) or Python package is required.

All public entry points swallow their own errors: failing to pause media must
never break dictation.
"""

from __future__ import annotations

from collections.abc import Callable

_MPRIS_PREFIX = "org.mpris.MediaPlayer2."
_PLAYER_PATH = "/org/mpris/MediaPlayer2"
_PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"


def _session_bus():
    # Imported lazily so importing this module never requires a session bus
    # (keeps it safe to import under tests / headless environments).
    from gi.repository import Gio

    return Gio.bus_get_sync(Gio.BusType.SESSION, None)


def _player_proxy(bus, name: str, interface: str):
    from gi.repository import Gio

    return Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.DO_NOT_AUTO_START,
        None,
        name,
        _PLAYER_PATH,
        interface,
        None,
    )


def list_playing_players() -> list[str]:
    """Return the bus names of MPRIS players currently in the "Playing" state."""
    from gi.repository import Gio, GLib

    bus = _session_bus()
    dbus = Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.DO_NOT_AUTO_START,
        None,
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        None,
    )
    names = dbus.call_sync(
        "ListNames", None, Gio.DBusCallFlags.NONE, -1, None
    ).unpack()[0]

    playing = []
    for name in names:
        if not name.startswith(_MPRIS_PREFIX):
            continue
        props = _player_proxy(bus, name, "org.freedesktop.DBus.Properties")
        try:
            status = props.call_sync(
                "Get",
                GLib.Variant("(ss)", (_PLAYER_IFACE, "PlaybackStatus")),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            ).unpack()[0]
        except Exception:
            # Player exposes no PlaybackStatus / disappeared: skip it.
            continue
        if status == "Playing":
            playing.append(name)
    return playing


def pause_player(name: str) -> None:
    from gi.repository import Gio

    proxy = _player_proxy(_session_bus(), name, _PLAYER_IFACE)
    proxy.call_sync("Pause", None, Gio.DBusCallFlags.NONE, -1, None)


def play_player(name: str) -> None:
    from gi.repository import Gio

    proxy = _player_proxy(_session_bus(), name, _PLAYER_IFACE)
    proxy.call_sync("Play", None, Gio.DBusCallFlags.NONE, -1, None)


class MprisController:
    """Pauses the players that were playing and resumes only those later."""

    def __init__(
        self,
        list_fn: Callable[[], list[str]] = list_playing_players,
        pause_fn: Callable[[str], None] = pause_player,
        resume_fn: Callable[[str], None] = play_player,
    ):
        self._list_fn = list_fn
        self._pause_fn = pause_fn
        self._resume_fn = resume_fn
        self._paused: list[str] = []

    def pause(self) -> None:
        """Pause every currently-playing player, remembering which ones."""
        self._paused = []
        try:
            for name in self._list_fn():
                try:
                    self._pause_fn(name)
                    self._paused.append(name)
                except Exception:
                    # One uncooperative player must not stop the others.
                    continue
        except Exception:
            # Never let media control break dictation.
            pass

    def resume(self) -> None:
        """Resume only the players this controller paused. No-op otherwise."""
        try:
            for name in self._paused:
                try:
                    self._resume_fn(name)
                except Exception:
                    continue
        finally:
            self._paused = []
