from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path


@dataclass
class HistoryEvent:
    id: str
    created_at: str
    source_type: str
    status: str
    created_by: str
    original_path: str | None = None
    original_name: str = ""
    audio_path: str = ""
    transcript_path: str = ""
    engine: str = ""
    model: str = ""
    language: str = "auto"
    duration_seconds: float | None = None
    error: str = ""
    legacy: bool = False
    transcript_text: str = ""


class HistoryStore:
    """Persists transcription history as structured event directories."""

    def __init__(self, config):
        self.config = config

    def directory(self) -> Path:
        return Path(os.path.expanduser(self.config.history.dir))

    def create_event(
        self,
        source_type: str,
        created_by: str,
        original_path: Path | str | None,
        engine: str,
        model: str,
        language: str,
    ) -> HistoryEvent:
        original_name = Path(original_path).name if original_path is not None else ""
        if not self.config.history.enabled:
            return HistoryEvent(
                id="disabled",
                created_at=datetime.now().isoformat(timespec="seconds"),
                source_type=source_type,
                status="disabled",
                created_by=created_by,
                original_path=None,
                original_name=original_name,
                engine=engine,
                model=model,
                language=language,
            )

        event = HistoryEvent(
            id=self._new_event_id(),
            created_at=datetime.now().isoformat(timespec="seconds"),
            source_type=source_type,
            status="processing",
            created_by=created_by,
            original_path=None,
            original_name=original_name,
            engine=engine,
            model=model,
            language=language,
        )
        self.update_event(event)
        return event

    def complete_event(
        self,
        event_id: str,
        audio_source: Path,
        transcript: str,
        duration_seconds: float | None = None,
    ) -> HistoryEvent:
        return self._complete_event(
            event_id,
            audio_source,
            transcript,
            duration_seconds=duration_seconds,
            allow_audio_failure=False,
        )

    def _complete_event(
        self,
        event_id: str,
        audio_source: Path,
        transcript: str,
        duration_seconds: float | None = None,
        allow_audio_failure: bool = False,
    ) -> HistoryEvent:
        event = self.load_event(event_id)
        if event.status == "disabled":
            return event

        event_dir = self._event_dir(event_id)
        event_dir.mkdir(parents=True, exist_ok=True)
        audio_dest = event_dir / "audio.wav"
        transcript_dest = event_dir / "transcript.txt"
        audio_source = Path(audio_source)
        try:
            if audio_source.resolve() != audio_dest.resolve():
                shutil.copyfile(audio_source, audio_dest)
            audio_path = str(audio_dest)
        except OSError:
            if not allow_audio_failure:
                raise
            audio_path = ""
        transcript_dest.write_text(transcript or "", encoding="utf-8")

        event.status = "completed"
        event.audio_path = audio_path
        event.transcript_path = str(transcript_dest)
        event.duration_seconds = duration_seconds
        event.error = ""
        event.transcript_text = transcript or ""
        self.update_event(event)
        return event

    def fail_event(self, event_id: str, message: str) -> HistoryEvent:
        event = self.load_event(event_id)
        if event.status == "disabled":
            return event
        event.status = "failed"
        event.error = message
        self.update_event(event)
        return event

    def update_event(self, event: HistoryEvent) -> None:
        if event.legacy:
            raise ValueError("legacy history events are read-only")
        if not self.config.history.enabled or event.status == "disabled":
            return
        event_dir = self._event_dir(event.id)
        event_dir.mkdir(parents=True, exist_ok=True)
        data = asdict(event)
        data.pop("transcript_text", None)
        (event_dir / "event.json").write_text(
            json.dumps(data, indent=2, sort_keys=True), encoding="utf-8"
        )

    def load_event(self, event_id: str) -> HistoryEvent:
        if event_id == "disabled":
            return HistoryEvent(
                id="disabled",
                created_at=datetime.now().isoformat(timespec="seconds"),
                source_type="",
                status="disabled",
                created_by="",
            )

        event_json = self._event_dir(event_id) / "event.json"
        data = json.loads(event_json.read_text(encoding="utf-8"))
        event_fields = {field.name for field in fields(HistoryEvent)}
        event = HistoryEvent(**{k: v for k, v in data.items() if k in event_fields})
        transcript_path = Path(event.transcript_path) if event.transcript_path else (
            self.directory() / event_id / "transcript.txt"
        )
        if transcript_path.exists():
            event.transcript_text = transcript_path.read_text(encoding="utf-8")
        return event

    def list_events(self) -> list[HistoryEvent]:
        directory = self.directory()
        if not directory.exists():
            return []

        events: list[tuple[datetime, HistoryEvent]] = []
        for child in directory.iterdir():
            if child.is_dir() and (child / "event.json").exists():
                try:
                    event = self.load_event(child.name)
                except (OSError, json.JSONDecodeError, TypeError, ValueError):
                    continue
                events.append((self._sort_time(event), event))

        for wav_path in directory.glob("*.wav"):
            txt_path = wav_path.with_suffix(".txt")
            if not txt_path.exists():
                continue
            try:
                created_at = datetime.strptime(
                    wav_path.stem, "%Y%m%d-%H%M%S"
                ).isoformat()
            except ValueError:
                created_at = datetime.fromtimestamp(wav_path.stat().st_mtime).isoformat()
            try:
                transcript_text = txt_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            event = HistoryEvent(
                id=wav_path.stem,
                created_at=created_at,
                source_type="microphone",
                status="completed",
                created_by="dictation",
                audio_path=str(wav_path),
                transcript_path=str(txt_path),
                legacy=True,
                transcript_text=transcript_text,
            )
            events.append((self._sort_time(event), event))

        return [event for _, event in sorted(events, key=lambda item: item[0], reverse=True)]

    def delete_event(self, event_id: str) -> None:
        event_dir = self._event_dir(event_id)
        if event_dir.is_dir() and (event_dir / "event.json").exists():
            shutil.rmtree(event_dir)

    def mark_stale_processing_failed(self) -> None:
        for event in self.list_events():
            if not event.legacy and event.status == "processing":
                self.fail_event(
                    event.id, "Application stopped before this job finished."
                )

    def save(self, wav_path: Path, text: str, stamp: str | None = None) -> Path | None:
        if not self.config.history.enabled:
            return None
        engine = getattr(self.config.general, "engine", "")
        event = self.create_event(
            source_type="microphone",
            created_by="dictation",
            original_path=None,
            engine=engine,
            model=self._model_for_engine(engine),
            language=getattr(self.config.general, "language", "auto"),
        )
        if stamp is not None:
            self.delete_event(event.id)
            event.id = self._new_event_id(stamp)
            self.update_event(event)
        completed = self._complete_event(
            event.id, wav_path, text, allow_audio_failure=True
        )
        return Path(completed.audio_path) if completed.audio_path else None

    def _new_event_id(self, stamp: str | None = None) -> str:
        if stamp is None:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{stamp}-{uuid.uuid4().hex[:8]}"

    def _sort_time(self, event: HistoryEvent) -> datetime:
        try:
            return datetime.fromisoformat(event.created_at)
        except ValueError:
            return datetime.min

    def _model_for_engine(self, engine: str) -> str:
        section = getattr(self.config, engine, None)
        return getattr(section, "model", "") if section is not None else ""

    def _event_dir(self, event_id: str) -> Path:
        if (
            not event_id
            or event_id in {".", ".."}
            or "/" in event_id
            or "\\" in event_id
            or Path(event_id).is_absolute()
            or Path(event_id).name != event_id
        ):
            raise ValueError("invalid history event id")
        return self.directory() / event_id
