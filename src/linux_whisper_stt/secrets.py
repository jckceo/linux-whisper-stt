from __future__ import annotations

import keyring as _keyring

SERVICE = "linux-whisper-stt"
USERNAME = "openai"


def get_api_key(keyring_module=_keyring) -> str | None:
    return keyring_module.get_password(SERVICE, USERNAME)


def set_api_key(key: str, keyring_module=_keyring) -> None:
    keyring_module.set_password(SERVICE, USERNAME, key)
