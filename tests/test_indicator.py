from linux_whisper_stt.controller import State
from linux_whisper_stt.tray.indicator import PrintIndicator, icon_for_state


def test_icon_mapping_distinct_for_each_state():
    names = {icon_for_state(s) for s in State}
    # idle, recording, busy(transcribing+pasting), error  -> 4 distinct names
    assert len(names) == 4
    assert icon_for_state(State.TRANSCRIBING) == icon_for_state(State.PASTING)


def test_print_indicator_records_states():
    ind = PrintIndicator()
    ind.set_state(State.RECORDING, "rec")
    assert ind.last == (State.RECORDING, "rec")
