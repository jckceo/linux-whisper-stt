from linux_whisper_stt.output import paste


def test_available_true_when_found():
    assert paste.ydotool_available(which=lambda name: "/usr/bin/ydotool") is True


def test_available_false_when_missing():
    assert paste.ydotool_available(which=lambda name: None) is False


def test_paste_uses_plain_text_clipboard_paste_shortcut_after_delay():
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
        (["ydotool", "key", "ctrl+shift+v"], {"check": True}),
    ]


def test_paste_does_not_send_regular_paste_shortcut_or_keycodes():
    calls = []

    def fake_runner(cmd, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    paste.paste_via_ydotool("ciao", runner=fake_runner, sleep_fn=lambda _: None)

    sent_tokens = [token for call in calls for token in call[2:]]
    assert not any(":" in token for token in sent_tokens)
    assert not any(token == "ctrl+v" for token in sent_tokens)
    assert any(token == "ctrl+shift+v" for token in sent_tokens)


def test_paste_uses_clipboard_shortcut_for_non_ascii_text():
    calls = []

    def fake_runner(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class R:
            returncode = 0

        return R()

    paste.paste_via_ydotool("Questa è ok", runner=fake_runner, sleep_fn=lambda _: None)

    assert calls == [
        (["ydotool", "key", "ctrl+shift+v"], {"check": True}),
    ]
