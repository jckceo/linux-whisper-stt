from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from linux_whisper_stt.history import HistoryEvent, HistoryStore
from linux_whisper_stt.media.prepare import PreparedMedia, prepare_media
from linux_whisper_stt.output.clipboard import copy_to_clipboard


class TranscriptionBackend(Protocol):
    def transcribe(self, wav_path: Path, language: str) -> str:
        ...


@dataclass(frozen=True)
class JobProgress:
    state: str
    event_id: str
    detail: str


class TranscriptionJobRunner:
    def __init__(
        self,
        config,
        history: HistoryStore,
        backends: Mapping[str, TranscriptionBackend],
        prepare_fn: Callable[[Path, Path], PreparedMedia] = prepare_media,
        copy_fn: Callable[[str], None] = copy_to_clipboard,
        popup_fn: Callable[[HistoryEvent], None] = lambda event: None,
        progress_fn: Callable[[JobProgress], None] = lambda progress: None,
    ):
        self.config = config
        self.history = history
        self.backends = backends
        self.prepare_fn = prepare_fn
        self.copy_fn = copy_fn
        self.popup_fn = popup_fn
        self.progress_fn = progress_fn

    def run_file_job(self, source_path: Path | str, created_by: str) -> HistoryEvent:
        source_path = Path(source_path)
        event = self.history.create_event(
            source_type="audio_file",
            created_by=created_by,
            original_path=source_path,
            engine=self.config.general.engine,
            model=self._model_name(),
            language=self.config.general.language,
        )
        try:
            self._progress("preparing", event.id, "Preparing file")
            prepared = self.prepare_fn(source_path, self.history.directory() / event.id)
            event.source_type = prepared.source_type
            self.history.update_event(event)

            self._progress("transcribing", event.id, "Transcribing file")
            transcript = self._current_backend().transcribe(
                prepared.audio_path, self.config.general.language
            )
            final_text = transcript.strip()

            self._progress("merging", event.id, "Saving transcript")
            event = self.history.complete_event(
                event.id,
                prepared.audio_path,
                final_text,
                duration_seconds=prepared.duration_seconds,
            )

            self.copy_fn(final_text)
            self._progress("completed", event.id, "Completed")
            self.popup_fn(event)
            return event
        except Exception as exc:
            event = self.history.fail_event(event.id, str(exc))
            self._progress("failed", event.id, str(exc))
            self.popup_fn(event)
            return event

    def run_microphone_job(
        self,
        wav_path: Path | str,
        transcript_fn: Callable[[Path], str],
    ) -> HistoryEvent:
        wav_path = Path(wav_path)
        event = self.history.create_event(
            source_type="microphone",
            created_by="dictation",
            original_path=None,
            engine=self.config.general.engine,
            model=self._model_name(),
            language=self.config.general.language,
        )
        try:
            transcript = transcript_fn(wav_path)
            return self.history.complete_event(
                event.id,
                wav_path,
                transcript.strip(),
            )
        except Exception as exc:
            return self.history.fail_event(event.id, str(exc))

    def _model_name(self) -> str:
        section = getattr(self.config, self.config.general.engine, None)
        return getattr(section, "model", "") if section is not None else ""

    def _progress(self, state: str, event_id: str, detail: str) -> None:
        self.progress_fn(JobProgress(state, event_id, detail))

    def _current_backend(self) -> TranscriptionBackend:
        return self.backends[self.config.general.engine]
