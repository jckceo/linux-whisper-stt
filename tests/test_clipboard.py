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


def test_wait_for_clipboard_returns_true_when_text_matches_after_retry():
    values = iter(["old", "hello"])
    sleeps = []

    assert clipboard.wait_for_clipboard(
        "hello",
        read_fn=lambda: next(values),
        sleep_fn=sleeps.append,
        monotonic_fn=FakeClock([0.0, 0.1, 0.2]),
    )
    assert sleeps == [0.05]


def test_wait_for_clipboard_returns_false_on_timeout():
    sleeps = []

    assert (
        clipboard.wait_for_clipboard(
            "hello",
            timeout=0.1,
            read_fn=lambda: "old",
            sleep_fn=sleeps.append,
            monotonic_fn=FakeClock([0.0, 0.2]),
        )
        is False
    )
    assert sleeps == []


class FakeClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)
