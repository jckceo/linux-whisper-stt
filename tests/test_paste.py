from linux_whisper_stt.output import paste


def test_available_true_when_found():
    assert paste.ydotool_available(which=lambda name: "/usr/bin/ydotool") is True


def test_available_false_when_missing():
    assert paste.ydotool_available(which=lambda name: None) is False


def test_paste_uses_delayed_clipboard_paste_shortcut():
    calls = []
    sleeps = []

    def fake_runner(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class R:
            returncode = 0

        return R()

    paste.paste_via_ydotool("ciao", runner=fake_runner, sleep_fn=sleeps.append)

    assert sleeps == [0.15]
    assert calls == [
        (
            [
                "ydotool",
                "key",
                "29:0",
                "56:0",
                "97:0",
                "100:0",
                "42:0",
                "54:0",
                "125:0",
                "126:0",
            ],
            {"check": False},
        ),
        (
            ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
            {"check": True},
        ),
    ]
