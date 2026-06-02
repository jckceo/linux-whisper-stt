from linux_whisper_stt.controller import State
from linux_whisper_stt.tray.icon_animator import Blink, Flash, Static, plan_icon
from linux_whisper_stt.tray.indicator import (
    PrintIndicator,
    build_settings_command,
    file_filter_patterns,
    icon_for_state,
    open_settings_once,
)


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
