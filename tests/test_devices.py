import json

from linux_whisper_stt.audio.devices import has_audio_input, parse_audio_sources

SAMPLE = json.dumps(
    [
        {"info": {"props": {"media.class": "Audio/Source", "node.description": "Built-in Mic"}}},
        {"info": {"props": {"media.class": "Audio/Sink", "node.description": "Speakers"}}},
        {"info": {"props": {"media.class": "Audio/Source", "node.name": "alsa_input.usb-Q9"}}},
        {"info": {"props": {}}},
        {"foo": "bar"},
    ]
)


class Proc:
    def __init__(self, returncode, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


def test_parse_audio_sources_returns_only_audio_source_nodes():
    assert parse_audio_sources(SAMPLE) == ["Built-in Mic", "alsa_input.usb-Q9"]


def test_parse_audio_sources_empty_when_no_sources():
    data = json.dumps([{"info": {"props": {"media.class": "Audio/Sink"}}}])
    assert parse_audio_sources(data) == []


def test_has_audio_input_true_when_sources_present():
    assert has_audio_input(runner=lambda *a, **k: Proc(0, SAMPLE)) is True


def test_has_audio_input_false_when_no_sources():
    assert has_audio_input(runner=lambda *a, **k: Proc(0, "[]")) is False


def test_has_audio_input_none_on_nonzero_exit():
    assert has_audio_input(runner=lambda *a, **k: Proc(1, "")) is None


def test_has_audio_input_none_on_invalid_json():
    assert has_audio_input(runner=lambda *a, **k: Proc(0, "not json")) is None


def test_has_audio_input_none_when_tool_missing():
    def runner(*a, **k):
        raise FileNotFoundError("pw-dump")

    assert has_audio_input(runner=runner) is None
