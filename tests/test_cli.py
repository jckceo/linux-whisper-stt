import subprocess

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


def test_install_service_prints_installed_path(capsys, monkeypatch, tmp_path):
    service_file = tmp_path / "systemd/user/linux-whisper-stt.service"

    def fake_install_service():
        return service_file

    import linux_whisper_stt.systemd

    monkeypatch.setattr(linux_whisper_stt.systemd, "install_service", fake_install_service)

    rc = cli.main(["install-service"])

    assert rc == 0
    assert capsys.readouterr().out == f"installed service: {service_file}\n"


def test_uninstall_service_prints_removed_path(capsys, monkeypatch, tmp_path):
    service_file = tmp_path / "systemd/user/linux-whisper-stt.service"

    def fake_uninstall_service():
        return service_file

    import linux_whisper_stt.systemd

    monkeypatch.setattr(
        linux_whisper_stt.systemd, "uninstall_service", fake_uninstall_service
    )

    rc = cli.main(["uninstall-service"])

    assert rc == 0
    assert capsys.readouterr().out == f"removed service: {service_file}\n"


def test_install_service_reports_systemctl_failure(capsys, monkeypatch):
    def fake_install_service():
        raise subprocess.CalledProcessError(1, ["systemctl", "--user", "enable"])

    import linux_whisper_stt.systemd

    monkeypatch.setattr(linux_whisper_stt.systemd, "install_service", fake_install_service)

    rc = cli.main(["install-service"])

    assert rc == 1
    assert capsys.readouterr().out.startswith("error: ")


def test_install_open_with_prints_installed_path(capsys, monkeypatch, tmp_path):
    desktop_file = tmp_path / "linux-whisper-stt-transcribe.desktop"
    installed = {}

    def fake_install_open_with(entrypoint):
        installed["entrypoint"] = entrypoint
        return desktop_file

    import linux_whisper_stt.open_with

    monkeypatch.setattr(cli, "entrypoint", lambda: "/venv/bin/linux-whisper-stt")
    monkeypatch.setattr(
        linux_whisper_stt.open_with,
        "install_open_with",
        fake_install_open_with,
    )

    rc = cli.main(["install-open-with"])

    assert rc == 0
    assert installed == {"entrypoint": "/venv/bin/linux-whisper-stt"}
    assert capsys.readouterr().out == f"installed open-with entry: {desktop_file}\n"


def test_install_open_with_reports_os_error(capsys, monkeypatch):
    def fake_install_open_with(entrypoint):
        raise OSError("permission denied")

    import linux_whisper_stt.open_with

    monkeypatch.setattr(
        linux_whisper_stt.open_with,
        "install_open_with",
        fake_install_open_with,
    )

    rc = cli.main(["install-open-with"])

    assert rc == 1
    assert capsys.readouterr().out == "error: permission denied\n"


def test_uninstall_service_reports_os_error(capsys, monkeypatch):
    def fake_uninstall_service():
        raise OSError("permission denied")

    import linux_whisper_stt.systemd

    monkeypatch.setattr(
        linux_whisper_stt.systemd, "uninstall_service", fake_uninstall_service
    )

    rc = cli.main(["uninstall-service"])

    assert rc == 1
    assert capsys.readouterr().out == "error: permission denied\n"


def test_transcribe_file_sends_structured_ipc(monkeypatch, tmp_path, capsys):
    sent = []
    media = tmp_path / "my file.mp4"
    media.write_bytes(b"x")

    def fake_send_command(payload):
        sent.append(payload)
        return {"accepted": True, "state": "transcribing"}

    monkeypatch.setattr("linux_whisper_stt.cli.send_command", fake_send_command)

    assert cli.main(["transcribe-file", str(media)]) == 0
    assert sent == [{"command": "transcribe-file", "path": str(media)}]
    assert "accepted" in capsys.readouterr().out


def test_transcribe_file_sends_resolved_ipc_path(monkeypatch, tmp_path):
    sent = []
    media = tmp_path / "clip.mp3"
    media.write_bytes(b"x")

    def fake_send_command(payload):
        sent.append(payload)
        return {"accepted": True, "state": "transcribing"}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("linux_whisper_stt.cli.send_command", fake_send_command)

    assert cli.main(["transcribe-file", "clip.mp3"]) == 0
    assert sent == [{"command": "transcribe-file", "path": str(media.resolve())}]


def test_transcribe_file_starts_daemon_then_retries(monkeypatch, tmp_path, capsys):
    calls = []
    media = tmp_path / "clip.mp3"
    media.write_bytes(b"x")

    def fake_send_command(payload, **kwargs):
        calls.append((payload, kwargs))
        if len(calls) == 1:
            raise ConnectionError("missing socket")
        return {"accepted": True, "state": "transcribing"}

    started = []
    monkeypatch.setattr("linux_whisper_stt.cli.send_command", fake_send_command)
    monkeypatch.setattr(
        "linux_whisper_stt.cli.start_daemon_background", lambda: started.append(True)
    )
    monkeypatch.setattr("linux_whisper_stt.cli.time.sleep", lambda _seconds: None)

    assert cli.main(["transcribe-file", str(media)]) == 0
    assert started == [True]
    assert calls[0] == ({"command": "transcribe-file", "path": str(media)}, {})
    assert calls[1] == (
        {"command": "transcribe-file", "path": str(media)},
        {"connect_retries": 50, "retry_delay": 0.1},
    )
    assert "accepted" in capsys.readouterr().out


def test_transcribe_file_reports_daemon_start_failure(monkeypatch, tmp_path, capsys):
    media = tmp_path / "clip.mp3"
    media.write_bytes(b"x")

    def fake_send_command(payload, **kwargs):
        raise ConnectionError("missing socket")

    def fake_start_daemon_background():
        raise OSError("permission denied")

    monkeypatch.setattr("linux_whisper_stt.cli.send_command", fake_send_command)
    monkeypatch.setattr(
        "linux_whisper_stt.cli.start_daemon_background",
        fake_start_daemon_background,
    )

    assert cli.main(["transcribe-file", str(media)]) == 1
    assert "failed to start daemon: permission denied" in capsys.readouterr().out
