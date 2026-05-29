
import pytest

from linux_whisper_stt.transcribe.openai_backend import (
    OpenAITranscriber,
    build_dictionary_prompt,
)


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


def test_build_dictionary_prompt_normalizes_comma_and_newline_terms():
    assert build_dictionary_prompt("ASIN, FNSKU\nreimbursement adjustments") == (
        "Use this dictionary/glossary for domain-specific transcription terms. "
        "Preserve these spellings and capitalization when spoken: "
        "ASIN, FNSKU, reimbursement adjustments."
    )


def test_transcribe_passes_dictionary_prompt_when_terms_exist(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    client = FakeClient(text="x")
    t = OpenAITranscriber(
        api_key_provider=lambda: "sk-x",
        model="gpt-4o-mini-transcribe",
        dictionary_terms="ASIN, FNSKU",
        client_factory=lambda api_key: client,
    )
    t.transcribe(wav, "auto")
    assert client.audio.transcriptions.last_kwargs["prompt"] == (
        "Use this dictionary/glossary for domain-specific transcription terms. "
        "Preserve these spellings and capitalization when spoken: ASIN, FNSKU."
    )


def test_transcribe_omits_dictionary_prompt_when_terms_are_blank(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    client = FakeClient(text="x")
    t = OpenAITranscriber(
        api_key_provider=lambda: "sk-x",
        model="gpt-4o-mini-transcribe",
        dictionary_terms="  ,\n ",
        client_factory=lambda api_key: client,
    )
    t.transcribe(wav, "auto")
    assert "prompt" not in client.audio.transcriptions.last_kwargs


def test_missing_api_key_raises(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"x")
    t = OpenAITranscriber(api_key_provider=lambda: None, model="whisper-1",
                          client_factory=lambda api_key: FakeClient())
    with pytest.raises(RuntimeError) as exc:
        t.transcribe(wav, "auto")
    assert "API key" in str(exc.value)


def test_openai_transcriber_transcribe_path_uses_existing_api(tmp_path):
    wav = tmp_path / "chunk.mp3"
    wav.write_bytes(b"audio")

    class Resp:
        text = "chunk text"

    class Transcriptions:
        def create(self, **kwargs):
            assert kwargs["model"] == "gpt-4o-mini-transcribe"
            assert kwargs["language"] == "it"
            return Resp()

    class Audio:
        transcriptions = Transcriptions()

    class Client:
        audio = Audio()

    transcriber = OpenAITranscriber(
        api_key_provider=lambda: "key",
        model="gpt-4o-mini-transcribe",
        client_factory=lambda api_key: Client(),
    )

    assert transcriber.transcribe(wav, "it") == "chunk text"
