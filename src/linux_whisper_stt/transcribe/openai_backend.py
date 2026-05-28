from __future__ import annotations

from pathlib import Path
from typing import Callable


def _default_client_factory(api_key: str):
    from openai import OpenAI

    return OpenAI(api_key=api_key)


class OpenAITranscriber:
    def __init__(
        self,
        api_key_provider: Callable[[], str | None],
        model: str,
        client_factory: Callable[[str], object] = _default_client_factory,
    ):
        self.api_key_provider = api_key_provider
        self.model = model
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
        with open(wav_path, "rb") as f:
            resp = client.audio.transcriptions.create(file=f, **kwargs)
        return resp.text
