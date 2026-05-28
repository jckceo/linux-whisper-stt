from linux_whisper_stt import secrets


class FakeKeyring:
    def __init__(self):
        self.store = {}

    def get_password(self, service, username):
        return self.store.get((service, username))

    def set_password(self, service, username, password):
        self.store[(service, username)] = password


def test_set_then_get():
    kr = FakeKeyring()
    secrets.set_api_key("sk-123", keyring_module=kr)
    assert secrets.get_api_key(keyring_module=kr) == "sk-123"


def test_get_missing_returns_none():
    kr = FakeKeyring()
    assert secrets.get_api_key(keyring_module=kr) is None
