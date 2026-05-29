from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path


def _default_client_factory(api_key: str):
    from openai import OpenAI

    return OpenAI(api_key=api_key)


class OpenAITranscriber:
    def __init__(
        self,
        api_key_provider: Callable[[], str | None],
        model: str,
        dictionary_terms: str = "",
        client_factory: Callable[[str], object] = _default_client_factory,
    ):
        self.api_key_provider = api_key_provider
        self.model = model
        self.dictionary_terms = dictionary_terms
        self.client_factory = client_factory

    def transcribe(self, wav_path: Path, language: str) -> str:
        api_key = self.api_key_provider()
        if not api_key:
            raise RuntimeError(
                "OpenAI API key missing. Run: linux-whisper-stt setup"
            )
        client = self.client_factory(api_key=api_key)
        kwargs = {"model": self.model}
        if language and language != "auto":
            kwargs["language"] = language
        prompt = build_dictionary_prompt(self.dictionary_terms)
        if prompt:
            kwargs["prompt"] = prompt
        with open(wav_path, "rb") as f:
            resp = client.audio.transcriptions.create(file=f, **kwargs)
        return resp.text


def build_dictionary_prompt(terms: str) -> str:
    entries = [entry.strip() for entry in re.split(r"[,\n]+", terms or "")]
    entries = [entry for entry in entries if entry]
    if not entries:
        return ""
    return (
        "Use this dictionary/glossary for domain-specific transcription terms. "
        "Preserve these spellings and capitalization when spoken: "
        f"{', '.join(entries)}."
    )
