from linux_whisper_stt.output import clipboard


def test_copy_invokes_wl_copy_with_text():
    calls = []

    def fake_runner(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class R:
            returncode = 0
            stdout = ""

        return R()

    clipboard.copy_to_clipboard("hello", runner=fake_runner)
    cmd, kwargs = calls[0]
    assert cmd[0] == "wl-copy"
    assert kwargs["input"] == "hello"


def test_read_returns_stdout():
    def fake_runner(cmd, **kwargs):
        class R:
            returncode = 0
            stdout = "clip contents"

        return R()

    assert clipboard.read_clipboard(runner=fake_runner) == "clip contents"
