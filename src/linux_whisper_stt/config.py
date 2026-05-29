from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import tomli_w


@dataclass
class GeneralConfig:
    engine: str = "openai"          # openai | local
    language: str = "auto"          # auto | it | en | ...
    paste_mode: str = "auto"        # auto | clipboard_only
    sounds: bool = True


@dataclass
class ShortcutConfig:
    binding: str = "<Control><Alt>space"


@dataclass
class OpenAIConfig:
    model: str = "gpt-4o-mini-transcribe"


@dataclass
class LocalConfig:
    model: str = "small"
    models_dir: str = "~/.local/share/linux-whisper-stt/models"
    binary_path: str = ""


@dataclass
class AudioConfig:
    device: str = "default"
    samplerate: int = 16000
    max_seconds: int = 300


@dataclass
class HistoryConfig:
    enabled: bool = True
    dir: str = "~/.local/share/linux-whisper-stt/history"


def _build(dc_cls, data: dict):
    known = {f.name for f in fields(dc_cls)}
    return dc_cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Config:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    shortcut: ShortcutConfig = field(default_factory=ShortcutConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    local: LocalConfig = field(default_factory=LocalConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        return cls(
            general=_build(GeneralConfig, data.get("general", {})),
            shortcut=_build(ShortcutConfig, data.get("shortcut", {})),
            openai=_build(OpenAIConfig, data.get("openai", {})),
            local=_build(LocalConfig, data.get("local", {})),
            audio=_build(AudioConfig, data.get("audio", {})),
            history=_build(HistoryConfig, data.get("history", {})),
        )

    def to_dict(self) -> dict:
        return {
            "general": asdict(self.general),
            "shortcut": asdict(self.shortcut),
            "openai": asdict(self.openai),
            "local": asdict(self.local),
            "audio": asdict(self.audio),
            "history": asdict(self.history),
        }


def default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "linux-whisper-stt" / "config.toml"


def load_config(path: Path | None = None) -> Config:
    path = path or default_config_path()
    if not path.exists():
        return Config()
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return Config.from_dict(data)


def save_config(config: Config, path: Path | None = None) -> None:
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(config.to_dict(), f)
    os.chmod(path, 0o600)
