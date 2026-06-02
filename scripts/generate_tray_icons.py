#!/usr/bin/env python3
"""Generate the tray status icons as circular PNG 'dots'.

Run once after changing colors/sizes; the generated PNGs are committed and read
at runtime by the AppIndicator. Requires pycairo (python3-gi-cairo on Ubuntu).

    python3 scripts/generate_tray_icons.py
"""
from __future__ import annotations

import math
from pathlib import Path

import cairo

SIZE = 64
CENTER = SIZE / 2
RADIUS = 24

ICONS = {
    "idle": (0.55, 0.55, 0.58),
    "recording_on": (0.90, 0.16, 0.16),
    "recording_off": (0.42, 0.10, 0.10),
    "busy": (0.98, 0.75, 0.18),
    "done": (0.20, 0.75, 0.35),
    # Same red family as recording; distinguished at runtime by the '!' overlay
    # (recording blinks, error is static) rather than by colour.
    "error": (0.85, 0.12, 0.12),
}

OUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "linux_whisper_stt"
    / "assets"
    / "icons"
)


def _draw_dot(ctx, color):
    r, g, b = color
    ctx.set_source_rgba(r, g, b, 1.0)
    ctx.arc(CENTER, CENTER, RADIUS, 0, 2 * math.pi)
    ctx.fill()


def _draw_exclamation(ctx):
    ctx.set_source_rgba(1, 1, 1, 1)
    ctx.rectangle(CENTER - 3, CENTER - 14, 6, 18)
    ctx.fill()
    ctx.arc(CENTER, CENTER + 11, 4, 0, 2 * math.pi)
    ctx.fill()


def generate():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, color in ICONS.items():
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
        ctx = cairo.Context(surface)
        _draw_dot(ctx, color)
        if name == "error":
            _draw_exclamation(ctx)
        surface.write_to_png(str(OUT_DIR / f"{name}.png"))
        print(f"wrote {name}.png")


if __name__ == "__main__":
    generate()
