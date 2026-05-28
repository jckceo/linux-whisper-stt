from __future__ import annotations

from pathlib import Path


def asset_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent.joinpath(*parts)
