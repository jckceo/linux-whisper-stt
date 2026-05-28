from linux_whisper_stt.config import Config
from linux_whisper_stt.sounds import Sounds


def make(sounds_enabled=True):
    cfg = Config()
    cfg.general.sounds = sounds_enabled
    played = []
    s = Sounds(cfg, start_path="/a/start.wav", stop_path="/a/stop.wav",
               play_fn=lambda p: played.append(p))
    return s, played


def test_plays_start_and_stop_when_enabled():
    s, played = make(True)
    s.play_start()
    s.play_stop()
    assert played == ["/a/start.wav", "/a/stop.wav"]


def test_silent_when_disabled():
    s, played = make(False)
    s.play_start()
    s.play_stop()
    assert played == []
