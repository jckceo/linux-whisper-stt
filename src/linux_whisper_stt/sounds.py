from __future__ import annotations

import shutil
import subprocess


def play(path: str, runner=subprocess.run, which=shutil.which) -> None:
    # check=False: a missing audio server should never break dictation.
    for player in ("paplay", "pw-play"):
        binary = which(player)
        if binary is None:
            continue
        try:
            result = runner([binary, str(path)], check=False)
        except FileNotFoundError:
            continue
        if getattr(result, "returncode", 0) == 0:
            return


class Sounds:
    def __init__(self, config, start_path: str, stop_path: str, play_fn=play):
        self.config = config
        self.start_path = start_path
        self.stop_path = stop_path
        self.play_fn = play_fn

    def play_start(self) -> None:
        if self.config.general.sounds:
            self.play_fn(self.start_path)

    def play_stop(self) -> None:
        if self.config.general.sounds:
            self.play_fn(self.stop_path)
