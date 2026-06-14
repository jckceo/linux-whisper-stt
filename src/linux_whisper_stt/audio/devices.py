from __future__ import annotations

import json
import subprocess


def parse_audio_sources(pw_dump_output: str) -> list[str]:
    """Names of PipeWire capture sources (real microphones) from `pw-dump` JSON.

    Output monitors (`*.monitor`) are excluded because they are not `Audio/Source` nodes.
    Raises on invalid JSON; callers that want fail-open behavior wrap this (see has_audio_input).
    """
    sources: list[str] = []
    for obj in json.loads(pw_dump_output):
        props = ((obj.get("info") or {}).get("props")) or {}
        if props.get("media.class") == "Audio/Source":
            sources.append(props.get("node.description") or props.get("node.name") or "?")
    return sources


def has_audio_input(runner=subprocess.run) -> bool | None:
    """True if >=1 capture source exists, False if none, None if undetectable.

    Returns None on any probe failure (pw-dump missing, non-zero exit, invalid JSON) so the
    caller can fail open and record anyway rather than block on a flaky probe.
    """
    try:
        proc = runner(["pw-dump"], capture_output=True, text=True, timeout=5)
        if proc.returncode != 0:
            return None
        return len(parse_audio_sources(proc.stdout or "")) > 0
    except Exception:
        return None
