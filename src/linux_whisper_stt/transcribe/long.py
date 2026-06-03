from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from ..jobs import transcribe_chunks
from ..media.chunking import (
    detect_silences,
    export_chunks,
    merge_transcripts,
    plan_silence_chunks,
)


def chunked_transcribe(
    backend,
    wav_path: Path,
    language: str,
    duration_seconds: float,
    *,
    target_seconds: float = 55.0,
    min_seconds: float = 20.0,
    max_workers: int = 4,
    detect_fn=detect_silences,
    export_fn=export_chunks,
    transcribe_chunks_fn=transcribe_chunks,
    separator: str = " ",
) -> str:
    """Transcribe a long recording by cutting on silences and running chunks in parallel.

    Cuts only at silence midpoints (never mid-word). If the audio yields a single chunk
    (no usable silence), transcribes the original file in one request instead.
    """
    silences = detect_fn(wav_path)
    plans = plan_silence_chunks(duration_seconds, silences, target_seconds, min_seconds)
    if len(plans) <= 1:
        return backend.transcribe(wav_path, language)
    with TemporaryDirectory(prefix="lwstt-chunks-") as tmp:
        chunk_paths = export_fn(wav_path, Path(tmp) / "chunks", plans)
        parts = transcribe_chunks_fn(backend, chunk_paths, language, max_workers=max_workers)
    return merge_transcripts(parts, separator=separator)
