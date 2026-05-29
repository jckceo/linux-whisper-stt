from linux_whisper_stt.config import Config
from linux_whisper_stt.sounds import Sounds, play


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


def test_missing_paplay_does_not_raise():
    def missing_paplay(*_args, **_kwargs):
        raise FileNotFoundError("paplay")

    play("/a/start.wav", runner=missing_paplay)


def test_play_falls_back_to_pw_play_when_paplay_is_missing():
    calls = []

    def fake_which(name):
        return {"pw-play": "/usr/bin/pw-play"}.get(name)

    def fake_runner(cmd, **kwargs):
        calls.append((cmd, kwargs))

    play("/a/start.wav", runner=fake_runner, which=fake_which)

    assert calls == [(["/usr/bin/pw-play", "/a/start.wav"], {"check": False})]
