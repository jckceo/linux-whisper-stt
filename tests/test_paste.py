from linux_whisper_stt.output import paste


def test_available_true_when_found():
    assert paste.ydotool_available(which=lambda name: "/usr/bin/ydotool") is True


def test_available_false_when_missing():
    assert paste.ydotool_available(which=lambda name: None) is False


def test_paste_sends_ctrl_v_keycodes():
    calls = []

    def fake_runner(cmd, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0

        return R()

    paste.paste_via_ydotool(runner=fake_runner)
    cmd = calls[0]
    assert cmd[:2] == ["ydotool", "key"]
    # ctrl down, v down, v up, ctrl up
    assert cmd[2:] == ["29:1", "47:1", "47:0", "29:0"]
