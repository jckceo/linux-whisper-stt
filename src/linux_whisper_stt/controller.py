from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from pathlib import Path


class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    PASTING = "pasting"
    ERROR = "error"


class Controller:
    def __init__(
        self,
        recorder,
        transcription,
        output,
        indicator,
        sounds,
        config,
        run_async: Callable[[Callable[[], None]], None] | None = None,
        history=None,
        file_jobs=None,
        media=None,
    ):
        self.recorder = recorder
        self.transcription = transcription
        self.output = output
        self.indicator = indicator
        self.sounds = sounds
        self.config = config
        self.history = history
        self.file_jobs = file_jobs
        self.media = media
        # default: run inline (deterministic for tests). Daemon injects a thread runner.
        self._run_async = run_async or (lambda fn: fn())
        self.state = State.IDLE
        self.last_error = ""

    # --- public API (called from IPC handler / tray menu) ---

    def toggle(self) -> None:
        if self.state in (State.IDLE, State.ERROR):
            self._begin_recording()
        elif self.state == State.RECORDING:
            self._end_recording()
        # TRANSCRIBING / PASTING: busy, ignore

    def start(self) -> None:
        if self.state in (State.IDLE, State.ERROR):
            self._begin_recording()

    def stop(self) -> None:
        if self.state == State.RECORDING:
            self._end_recording()

    def cancel(self) -> None:
        """Discard an in-progress recording without transcribing it."""
        if self.state != State.RECORDING:
            return
        wav_path = self.recorder.stop()
        # Resume whatever we paused (same ordering as a normal stop), then throw
        # the captured audio away — no transcription, no history, no paste.
        if self.media is not None:
            self.media.resume()
        wav_path.unlink(missing_ok=True)
        self._set_state(State.IDLE, "Recording cancelled")

    def status(self) -> dict:
        return {"state": self.state.value, "last_error": self.last_error}

    def transcribe_file(self, path: Path, created_by: str) -> dict:
        if self.state not in (State.IDLE, State.ERROR):
            return {
                "accepted": False,
                "state": self.state.value,
                "error": "busy",
            }
        if self.file_jobs is None:
            return {
                "accepted": False,
                "state": self.state.value,
                "error": "file transcription is not configured",
            }

        self.last_error = ""
        self._set_state(State.TRANSCRIBING)
        response = {"accepted": True, "state": self.state.value}
        self._run_async(lambda: self._run_file_job(path, created_by))
        return response

    # --- internals ---

    def _begin_recording(self) -> None:
        self.last_error = ""
        self.recorder.start()
        self._set_state(State.RECORDING)
        if self.config.general.sounds:
            self.sounds.play_start()
        if self.media is not None and self.config.general.pause_on_recording:
            self.media.pause()

    def _end_recording(self) -> None:
        if self.config.general.sounds:
            self.sounds.play_stop()
        wav_path = self.recorder.stop()
        # Resume only after capture has stopped, so resumed audio can't bleed
        # into the recording tail. Always resume whatever we paused, even if the
        # flag was toggled off mid-recording; no-op when nothing was paused.
        if self.media is not None:
            self.media.resume()
        self._set_state(State.TRANSCRIBING)
        self._run_async(lambda: self._transcribe_and_deliver(wav_path))

    def _transcribe_and_deliver(self, wav_path: Path) -> None:
        try:
            text = self.transcription.transcribe(wav_path, self.config.general.language)
            if self.history is not None:
                self.history.save(wav_path, text)
            if not text or not text.strip():
                self._set_state(State.IDLE, "Nothing transcribed")
                return
            self._set_state(State.PASTING)
            result = self.output.deliver(text.strip())
            self._set_state(State.IDLE, result.message)
        except Exception as e:
            self._fail(str(e))
        finally:
            wav_path.unlink(missing_ok=True)

    def _run_file_job(self, path: Path, created_by: str) -> None:
        try:
            event = self.file_jobs.run_file_job(path, created_by=created_by)
            if event is not None and getattr(event, "status", "") == "failed":
                self._fail(getattr(event, "error", "") or "File transcription failed")
                return
            self._set_state(State.IDLE, "Saved to history")
        except Exception as e:
            self._fail(str(e))

    def _fail(self, message: str) -> None:
        self.last_error = message
        self._set_state(State.ERROR, message)

    def _set_state(self, state: State, detail: str = "") -> None:
        self.state = state
        self.indicator.set_state(state, detail)
