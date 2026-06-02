from __future__ import annotations

from dataclasses import dataclass

from ..controller import State

_ICON_NAMES = {
    State.IDLE: "idle",
    State.RECORDING: "recording_on",
    State.TRANSCRIBING: "busy",
    State.PASTING: "busy",
    State.ERROR: "error",
}


def icon_for_state(state: State) -> str:
    return _ICON_NAMES[state]


@dataclass(frozen=True)
class Static:
    """Show one icon and stop any animation."""

    icon: str


@dataclass(frozen=True)
class Blink:
    """Alternate two icons on a timer (recording light)."""

    on: str
    off: str


@dataclass(frozen=True)
class Flash:
    """Show `flash` briefly, then settle on `then` (done -> idle)."""

    flash: str
    then: str


IconDirective = Static | Blink | Flash


def plan_icon(prev_state: State | None, new_state: State) -> IconDirective:
    if new_state == State.RECORDING:
        return Blink("recording_on", "recording_off")
    if new_state == State.IDLE and prev_state in (State.TRANSCRIBING, State.PASTING):
        return Flash("done", "idle")
    return Static(icon_for_state(new_state))


class IconAnimator:
    """Executes icon directives over injected timer callbacks.

    `set_icon(name)` shows an icon. `schedule(ms, callback)` returns a source id
    and re-fires while the callback returns True (GLib.timeout_add semantics).
    `cancel(source_id)` stops a scheduled timer.
    """

    def __init__(self, set_icon, schedule, cancel, blink_ms=600, flash_ms=1500):
        self._set_icon = set_icon
        self._schedule = schedule
        self._cancel = cancel
        self._blink_ms = blink_ms
        self._flash_ms = flash_ms
        self._prev_state = None
        self._timer = None
        self._blink_frames = None
        self._blink_on = False
        self._flash_then = None

    def apply(self, state) -> None:
        self._stop_timer()
        directive = plan_icon(self._prev_state, state)
        self._prev_state = state

        if isinstance(directive, Static):
            self._set_icon(directive.icon)
        elif isinstance(directive, Blink):
            self._blink_frames = (directive.on, directive.off)
            self._blink_on = True
            self._set_icon(directive.on)
            self._timer = self._schedule(self._blink_ms, self._blink_tick)
        elif isinstance(directive, Flash):
            self._flash_then = directive.then
            self._set_icon(directive.flash)
            self._timer = self._schedule(self._flash_ms, self._flash_tick)

    def _blink_tick(self) -> bool:
        self._blink_on = not self._blink_on
        on, off = self._blink_frames
        self._set_icon(on if self._blink_on else off)
        return True  # keep blinking

    def _flash_tick(self) -> bool:
        self._set_icon(self._flash_then)
        self._timer = None
        return False  # one-shot

    def _stop_timer(self) -> None:
        if self._timer is not None:
            self._cancel(self._timer)
            self._timer = None
