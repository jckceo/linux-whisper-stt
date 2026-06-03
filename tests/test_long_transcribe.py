from pathlib import Path

from linux_whisper_stt.transcribe.long import chunked_transcribe


class FakeBackend:
    def __init__(self):
        self.calls = []

    def transcribe(self, path, language):
        self.calls.append((path, language))
        return f"text-of-{Path(path).name}"


def test_chunked_transcribe_splits_and_merges_in_order():
    backend = FakeBackend()
    captured = {}

    def export_fn(source, chunk_dir, plans):
        captured["plans"] = plans
        return [Path(f"chunk-{p.index:03d}.mp3") for p in plans]

    def transcribe_chunks_fn(b, paths, language, max_workers):
        captured["max_workers"] = max_workers
        return [b.transcribe(p, language) for p in paths]

    result = chunked_transcribe(
        backend,
        Path("rec.wav"),
        "auto",
        180.0,
        detect_fn=lambda path: [(60.0, 61.0), (130.0, 131.0)],
        export_fn=export_fn,
        transcribe_chunks_fn=transcribe_chunks_fn,
    )

    assert result == "text-of-chunk-000.mp3 text-of-chunk-001.mp3 text-of-chunk-002.mp3"
    assert captured["max_workers"] == 4
    assert len(captured["plans"]) == 3


def test_chunked_transcribe_single_chunk_falls_back_to_whole_file():
    backend = FakeBackend()
    export_calls = []

    def export_fn(source, chunk_dir, plans):
        export_calls.append(plans)
        return []

    result = chunked_transcribe(
        backend,
        Path("rec.wav"),
        "auto",
        200.0,
        detect_fn=lambda path: [],  # no silences -> single chunk plan
        export_fn=export_fn,
        transcribe_chunks_fn=lambda *a, **k: [],
    )

    assert result == "text-of-rec.wav"
    assert backend.calls == [(Path("rec.wav"), "auto")]
    assert export_calls == []
