from linux_whisper_stt.output import paste


def test_available_true_when_found():
    assert paste.ydotool_available(which=lambda name: "/usr/bin/ydotool") is True


def test_available_false_when_missing():
    assert paste.ydotool_available(which=lambda name: None) is False


def test_paste_types_text_with_ydotool_stdin():
    calls = []

    def fake_runner(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class R:
            returncode = 0

        return R()

    paste.paste_via_ydotool("ciao", runner=fake_runner)
    cmd, kwargs = calls[0]
    assert cmd == ["ydotool", "type", "--file", "-"]
    assert kwargs["input"] == "ciao"
    assert kwargs["text"] is True
    assert kwargs["check"] is True
