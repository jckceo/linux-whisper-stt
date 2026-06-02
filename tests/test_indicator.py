from linux_whisper_stt.assets import asset_path
from linux_whisper_stt.controller import State
from linux_whisper_stt.tray.icon_animator import (
    Blink,
    Flash,
    IconAnimator,
    Static,
    icon_for_state,
    plan_icon,
)
from linux_whisper_stt.tray.indicator import (
    PrintIndicator,
    build_settings_command,
    file_filter_patterns,
    open_settings_once,
)


def test_required_tray_icons_exist():
    for name in ("idle", "recording_on", "recording_off", "busy", "done", "error"):
        assert asset_path("icons", name + ".png").exists(), name


def test_icon_mapping_distinct_for_each_state():
    names = {icon_for_state(s) for s in State}
    # idle, recording, busy(transcribing+pasting), error  -> 4 distinct names
    assert len(names) == 4
    assert icon_for_state(State.TRANSCRIBING) == icon_for_state(State.PASTING)


def test_print_indicator_records_states():
    ind = PrintIndicator()
    ind.set_state(State.RECORDING, "rec")
    assert ind.last == (State.RECORDING, "rec")


def test_settings_command_uses_entrypoint():
    cmd = build_settings_command(entrypoint_fn=lambda: "/abs/linux-whisper-stt")
    assert cmd == ["/abs/linux-whisper-stt", "setup"]


def test_open_settings_reuses_running_process():
    class RunningProcess:
        def poll(self):
            return None

    launched = []

    proc = RunningProcess()
    result = open_settings_once(
        proc,
        popen_fn=lambda cmd: launched.append(cmd),
        command_fn=lambda: ["/abs/linux-whisper-stt", "setup"],
    )

    assert result is proc
    assert launched == []


def test_open_settings_starts_when_no_process_is_running():
    class ExitedProcess:
        def poll(self):
            return 0

    class NewProcess:
        pass

    new_proc = NewProcess()

    result = open_settings_once(
        ExitedProcess(),
        popen_fn=lambda cmd: new_proc,
        command_fn=lambda: ["/abs/linux-whisper-stt", "setup"],
    )

    assert result is new_proc


def test_file_filter_patterns_include_audio_and_video():
    patterns = file_filter_patterns()
    assert "*.mp3" in patterns
    assert "*.wav" in patterns
    assert "*.mp4" in patterns
    assert "*.mkv" in patterns


def test_plan_icon_idle_at_startup_is_static_neutral():
    assert plan_icon(None, State.IDLE) == Static("idle")


def test_plan_icon_recording_blinks_red():
    assert plan_icon(State.IDLE, State.RECORDING) == Blink("recording_on", "recording_off")


def test_plan_icon_transcribing_and_pasting_are_static_busy():
    assert plan_icon(State.RECORDING, State.TRANSCRIBING) == Static("busy")
    assert plan_icon(State.TRANSCRIBING, State.PASTING) == Static("busy")


def test_plan_icon_idle_after_active_job_flashes_done():
    assert plan_icon(State.PASTING, State.IDLE) == Flash("done", "idle")
    assert plan_icon(State.TRANSCRIBING, State.IDLE) == Flash("done", "idle")


def test_plan_icon_idle_after_error_is_static_neutral():
    assert plan_icon(State.ERROR, State.IDLE) == Static("idle")


def test_plan_icon_error_is_static_red():
    assert plan_icon(State.IDLE, State.ERROR) == Static("error")


class FakeClock:
    def __init__(self):
        self.scheduled = []   # (id, ms, callback)
        self.cancelled = []
        self._next = 1

    def schedule(self, ms, callback):
        sid = self._next
        self._next += 1
        self.scheduled.append((sid, ms, callback))
        return sid

    def cancel(self, sid):
        self.cancelled.append(sid)

    def fire_last(self):
        _sid, _ms, callback = self.scheduled[-1]
        return callback()


def _make_animator(clock, icons):
    return IconAnimator(
        set_icon=icons.append,
        schedule=clock.schedule,
        cancel=clock.cancel,
        blink_ms=600,
        flash_ms=1500,
    )


def test_animator_recording_blinks_between_frames():
    clock, icons = FakeClock(), []
    animator = _make_animator(clock, icons)

    animator.apply(State.RECORDING)
    assert icons[-1] == "recording_on"
    assert clock.scheduled[-1][1] == 600

    assert clock.fire_last() is True  # blink keeps repeating
    assert icons[-1] == "recording_off"
    clock.fire_last()
    assert icons[-1] == "recording_on"


def test_animator_static_state_cancels_running_blink():
    clock, icons = FakeClock(), []
    animator = _make_animator(clock, icons)

    animator.apply(State.RECORDING)
    blink_sid = clock.scheduled[-1][0]
    animator.apply(State.TRANSCRIBING)

    assert blink_sid in clock.cancelled
    assert icons[-1] == "busy"


def test_animator_idle_after_job_flashes_done_then_settles():
    clock, icons = FakeClock(), []
    animator = _make_animator(clock, icons)

    animator.apply(State.TRANSCRIBING)
    animator.apply(State.IDLE)
    assert icons[-1] == "done"
    assert clock.scheduled[-1][1] == 1500

    assert clock.fire_last() is False  # one-shot
    assert icons[-1] == "idle"


def test_animator_idle_at_startup_is_neutral_without_flash():
    clock, icons = FakeClock(), []
    animator = _make_animator(clock, icons)

    animator.apply(State.IDLE)
    assert icons == ["idle"]
    assert clock.scheduled == []


def test_animator_error_is_static_red():
    clock, icons = FakeClock(), []
    animator = _make_animator(clock, icons)

    animator.apply(State.ERROR)
    assert icons[-1] == "error"
    assert clock.scheduled == []


def test_animator_recording_reapplied_while_blinking_resets_timer():
    clock, icons = FakeClock(), []
    animator = _make_animator(clock, icons)

    animator.apply(State.RECORDING)
    first_sid = clock.scheduled[-1][0]
    animator.apply(State.RECORDING)

    assert first_sid in clock.cancelled          # old blink timer cancelled
    assert clock.scheduled[-1][0] != first_sid   # a fresh timer was scheduled
    assert icons[-1] == "recording_on"


def test_animator_flash_interrupted_by_new_state_cancels_flash():
    clock, icons = FakeClock(), []
    animator = _make_animator(clock, icons)

    animator.apply(State.TRANSCRIBING)
    animator.apply(State.IDLE)               # starts the done->idle flash
    flash_sid = clock.scheduled[-1][0]
    animator.apply(State.ERROR)              # new state interrupts the flash

    assert flash_sid in clock.cancelled
    assert icons[-1] == "error"
