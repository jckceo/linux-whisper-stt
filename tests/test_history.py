from linux_whisper_stt.config import Config
from linux_whisper_stt.controller import Controller
from linux_whisper_stt.history import HistoryStore


def test_save_writes_wav_and_txt(tmp_path):
    cfg = Config()
    cfg.history.dir = str(tmp_path / "hist")
    wav = tmp_path / "rec.wav"
    wav.write_bytes(b"RIFFDATA")
    dest = HistoryStore(cfg).save(wav, "ciao mondo", stamp="20260529-120000")
    assert dest == tmp_path / "hist" / "20260529-120000.wav"
    assert dest.read_bytes() == b"RIFFDATA"
    assert (tmp_path / "hist" / "20260529-120000.txt").read_text() == "ciao mondo"


def test_disabled_does_nothing(tmp_path):
    cfg = Config()
    cfg.history.enabled = False
    cfg.history.dir = str(tmp_path / "hist")
    wav = tmp_path / "rec.wav"
    wav.write_bytes(b"x")
    assert HistoryStore(cfg).save(wav, "x", stamp="s") is None
    assert not (tmp_path / "hist").exists()


class _Rec:
    def __init__(self, wav):
        self._wav = wav

    def start(self):
        pass

    def stop(self):
        return self._wav


class _Trans:
    def transcribe(self, wav_path, language):
        return "ciao"


class _Result:
    pasted = True
    message = "Pasted"


class _Out:
    def deliver(self, text):
        return _Result()


class _Ind:
    def set_state(self, state, detail=""):
        pass


class _Snd:
    def play_start(self):
        pass

    def play_stop(self):
        pass


def test_controller_calls_history(tmp_path):
    wav = tmp_path / "rec.wav"
    wav.write_bytes(b"data")
    saved = []

    class FakeHistory:
        def save(self, wav_path, text):
            saved.append((wav_path, text))

    c = Controller(_Rec(wav), _Trans(), _Out(), _Ind(), _Snd(), Config(), history=FakeHistory())
    c.toggle()
    c.toggle()
    assert saved == [(wav, "ciao")]
