from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from linux_whisper_stt.history import HistoryEvent, HistoryStore
from linux_whisper_stt.media.chunking import (
    estimate_mp3_bytes,
    export_chunks,
    merge_transcripts,
    plan_chunks,
)
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


def build_openai_chunk_paths(
    audio_path: Path,
    duration_seconds: float | None,
    event_dir: Path,
) -> list[Path]:
    if duration_seconds is None:
        return [audio_path]

    estimated_bytes = estimate_mp3_bytes(duration_seconds)
    chunks = plan_chunks(duration_seconds, estimated_bytes)
    return export_chunks(audio_path, event_dir / "chunks", chunks)


def transcribe_chunks(
    backend: TranscriptionBackend,
    chunk_paths: list[Path],
    language: str,
    max_workers: int = 2,
    executor_cls=ThreadPoolExecutor,
) -> list[str]:
    def transcribe(path: Path) -> str:
        return backend.transcribe(path, language)

    if max_workers <= 0:
        raise ValueError("max_workers must be greater than 0")

    results: list[str] = []
    with executor_cls(max_workers=max_workers) as executor:
        for start in range(0, len(chunk_paths), max_workers):
            batch = chunk_paths[start : start + max_workers]
            futures = [executor.submit(transcribe, path) for path in batch]
            results.extend(future.result() for future in futures)
    return results


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
        chunk_paths_fn: Callable[
            [Path, float | None, Path], list[Path]
        ] = build_openai_chunk_paths,
    ):
        self.config = config
        self.history = history
        self.backends = backends
        self.prepare_fn = prepare_fn
        self.copy_fn = copy_fn
        self.popup_fn = popup_fn
        self.progress_fn = progress_fn
        self.chunk_paths_fn = chunk_paths_fn

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
            with self._event_directory(event) as event_dir:
                self._progress("preparing", event.id, "Preparing file")
                prepared = self.prepare_fn(source_path, event_dir)
                event.source_type = prepared.source_type
                self.history.update_event(event)

                if self.config.general.engine == "openai":
                    chunk_paths = self.chunk_paths_fn(
                        prepared.audio_path,
                        prepared.duration_seconds,
                        event_dir,
                    )
                    self._progress(
                        "transcribing",
                        event.id,
                        f"Transcribing file 1/{len(chunk_paths)}",
                    )
                    parts = transcribe_chunks(
                        self._backend(),
                        chunk_paths,
                        self.config.general.language,
                        max_workers=2,
                    )
                    final_text = merge_transcripts(parts)
                else:
                    self._progress("transcribing", event.id, "Transcribing file")
                    transcript = self._backend().transcribe(
                        prepared.audio_path, self.config.general.language
                    )
                    final_text = transcript.strip()

                self._progress("merging", event.id, "Saving transcript")
                event = self._complete_file_event(event, prepared, final_text)
        except Exception as exc:
            event = self._fail_event(event, str(exc))
            self._progress("failed", event.id, str(exc))
            self._popup(event)
            return event

        if final_text:
            self._copy_result(final_text)
        self._progress("completed", event.id, "Completed")
        self._popup(event)
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
        try:
            self.progress_fn(JobProgress(state, event_id, detail))
        except Exception:
            pass

    def _copy_result(self, text: str) -> None:
        try:
            self.copy_fn(text)
        except Exception:
            pass

    def _popup(self, event: HistoryEvent) -> None:
        try:
            self.popup_fn(event)
        except Exception:
            pass

    def _backend(self) -> TranscriptionBackend:
        engine = self.config.general.engine
        backend = self.backends.get(engine)
        if backend is None:
            raise RuntimeError(f"No transcription backend configured for engine: {engine}")
        return backend

    @contextmanager
    def _event_directory(self, event: HistoryEvent) -> Iterator[Path]:
        with TemporaryDirectory(prefix=f"linux-whisper-stt-{event.id}-") as directory:
            yield Path(directory)

    def _complete_file_event(
        self,
        event: HistoryEvent,
        prepared: PreparedMedia,
        transcript: str,
    ) -> HistoryEvent:
        if self.config.history.enabled:
            return self.history.complete_event(
                event.id,
                prepared.audio_path,
                transcript,
                duration_seconds=prepared.duration_seconds,
            )

        event.status = "completed"
        event.audio_path = str(prepared.audio_path)
        event.transcript_path = ""
        event.duration_seconds = prepared.duration_seconds
        event.error = ""
        event.transcript_text = transcript
        return event

    def _fail_event(self, event: HistoryEvent, message: str) -> HistoryEvent:
        if self.config.history.enabled:
            return self.history.fail_event(event.id, message)

        event.status = "failed"
        event.error = message
        return event
