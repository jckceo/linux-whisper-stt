from __future__ import annotations

import subprocess


def play(path: str, runner=subprocess.run) -> None:
    # check=False: a missing audio server should never break dictation.
    try:
        runner(["paplay", str(path)], check=False)
    except FileNotFoundError:
        pass


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
