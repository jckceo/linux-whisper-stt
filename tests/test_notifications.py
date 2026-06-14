from linux_whisper_stt.notifications import build_notify_command, send_notification


def test_build_notify_command_shape():
    assert build_notify_command("Title", "Body") == [
        "notify-send",
        "-a",
        "linux-whisper-stt",
        "Title",
        "Body",
    ]


def test_send_notification_invokes_runner_and_returns_true():
    calls = []

    def runner(cmd, capture_output, text, timeout):
        calls.append(cmd)

    assert send_notification("Title", "Body", runner=runner) is True
    assert calls == [["notify-send", "-a", "linux-whisper-stt", "Title", "Body"]]


def test_send_notification_returns_false_when_runner_raises():
    def runner(*a, **k):
        raise FileNotFoundError("notify-send")

    assert send_notification("Title", "Body", runner=runner) is False


def test_send_notification_returns_false_on_nonzero_exit():
    class Proc:
        returncode = 1

    assert send_notification("Title", "Body", runner=lambda *a, **k: Proc()) is False
