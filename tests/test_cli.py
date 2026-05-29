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
