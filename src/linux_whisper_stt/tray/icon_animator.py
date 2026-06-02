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
