from pathlib import Path

import pytest

from linux_whisper_stt.transcribe.openai_backend import OpenAITranscriber


class FakeTranscriptions:
    def __init__(self, text):
        self.text_value = text
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs

        class R:
            text = self.text_value

        return R()


class FakeAudio:
    def __init__(self, text):
        self.transcriptions = FakeTranscriptions(text)


class FakeClient:
    def __init__(self, api_key=None, text="ciao"):
        self.api_key = api_key
        self.audio = FakeAudio(text)


def test_transcribe_returns_text(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF....")
    client = FakeClient(text="ciao mondo")
    t = OpenAITranscriber(api_key_provider=lambda: "sk-x", model="whisper-1",
                          client_factory=lambda api_key: client)
    assert t.transcribe(wav, "auto") == "ciao mondo"
    assert client.audio.transcriptions.last_kwargs["model"] == "whisper-1"
    # 'auto' must NOT pass a language param
    assert "language" not in client.audio.transcriptions.last_kwargs


def test_transcribe_passes_explicit_language(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    client = FakeClient(text="x")
    t = OpenAITranscriber(api_key_provider=lambda: "sk-x", model="whisper-1",
                          client_factory=lambda api_key: client)
    t.transcribe(wav, "it")
    assert client.audio.transcriptions.last_kwargs["language"] == "it"


def test_missing_api_key_raises(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"x")
    t = OpenAITranscriber(api_key_provider=lambda: None, model="whisper-1",
                          client_factory=lambda api_key: FakeClient())
    with pytest.raises(RuntimeError) as exc:
        t.transcribe(wav, "auto")
    assert "API key" in str(exc.value)
