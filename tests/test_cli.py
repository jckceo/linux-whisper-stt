from linux_whisper_stt import cli


def test_toggle_sends_command(capsys, monkeypatch):
    sent = {}

    def fake_send(command, socket_path=None):
        sent["cmd"] = command
        return {"state": "recording", "last_error": ""}

    monkeypatch.setattr(cli, "send_command", fake_send)
    rc = cli.main(["toggle"])
    assert rc == 0
    assert sent["cmd"] == "toggle"
    out = capsys.readouterr().out
    assert "recording" in out


def test_status_reports_daemon_not_running(capsys, monkeypatch):
    def fake_send(command, socket_path=None):
        raise ConnectionError("daemon not running")

    monkeypatch.setattr(cli, "send_command", fake_send)
    rc = cli.main(["status"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "not running" in out.lower()


def test_unknown_command_returns_error():
    rc = cli.main(["frobnicate"])
    assert rc == 2
