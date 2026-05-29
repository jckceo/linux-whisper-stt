
from linux_whisper_stt.config import Config, load_config, save_config


def test_defaults():
    c = Config()
    assert c.general.engine == "openai"
    assert c.general.language == "auto"
    assert c.general.paste_mode == "auto"
    assert c.general.sounds is True
    assert c.shortcut.binding == "<Control><Alt>space"
    assert c.openai.model == "gpt-4o-mini-transcribe"
    assert c.local.model == "small"
    assert c.audio.samplerate == 16000
    assert c.dictionary.terms == ""


def test_load_missing_returns_defaults(tmp_path):
    c = load_config(tmp_path / "nope.toml")
    assert c.general.engine == "openai"


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "config.toml"
    c = Config()
    c.general.engine = "local"
    c.audio.max_seconds = 120
    c.dictionary.terms = "ASIN, FNSKU, reimbursement adjustments"
    save_config(c, path)
    loaded = load_config(path)
    assert loaded.general.engine == "local"
    assert loaded.audio.max_seconds == 120
    assert loaded.dictionary.terms == "ASIN, FNSKU, reimbursement adjustments"


def test_load_ignores_unknown_keys(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[general]\nengine = "local"\nbogus = "x"\n')
    loaded = load_config(path)
    assert loaded.general.engine == "local"


def test_save_sets_restrictive_permissions(tmp_path):
    path = tmp_path / "config.toml"
    save_config(Config(), path)
    assert (path.stat().st_mode & 0o777) == 0o600
