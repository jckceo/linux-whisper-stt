import subprocess

import pytest

from linux_whisper_stt.systemd import (
    default_exec_start,
    install_service,
    service_content,
    service_installed,
    service_path,
    uninstall_service,
)


def test_service_path_uses_xdg_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert service_path() == tmp_path / "systemd/user/linux-whisper-stt.service"


def test_service_installed_returns_false_when_unit_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert service_installed() is False


def test_service_installed_returns_true_when_unit_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = tmp_path / "systemd/user/linux-whisper-stt.service"
    path.parent.mkdir(parents=True)
    path.write_text("[Unit]\n")

    assert service_installed() is True


def test_service_content_includes_daemon_unit_fields():
    content = service_content(command="/abs/linux-whisper-stt daemon")

    assert "[Unit]" in content
    assert "Description=linux-whisper-stt daemon" in content
    assert "PartOf=graphical-session.target" in content
    assert "After=graphical-session.target" in content
    assert "ExecStart=/abs/linux-whisper-stt daemon" in content
    assert "Restart=on-failure" in content
    assert "WantedBy=graphical-session.target" in content


def test_default_exec_start_uses_unquoted_simple_absolute_entrypoint():
    assert default_exec_start(entrypoint_fn=lambda: "/abs/linux-whisper-stt") == (
        "/abs/linux-whisper-stt daemon"
    )


def test_default_exec_start_escapes_percent_and_quotes_special_paths():
    assert default_exec_start(
        entrypoint_fn=lambda: '/path with spaces/linux%whisper"stt\\bin'
    ) == '"/path with spaces/linux%%whisper\\"stt\\\\bin" daemon'


def test_install_service_writes_unit_and_enables_it(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    calls = []

    def fake_runner(args, check):
        calls.append(("runner", args, check))

    def fake_uninstall_autostart():
        calls.append(("disable_autostart",))
        return tmp_path / "autostart/linux-whisper-stt.desktop"

    path = install_service(
        command="/abs/linux-whisper-stt daemon",
        runner=fake_runner,
        disable_autostart=fake_uninstall_autostart,
    )

    assert path == tmp_path / "systemd/user/linux-whisper-stt.service"
    assert path.read_text() == service_content(command="/abs/linux-whisper-stt daemon")
    assert calls == [
        (
            "runner",
            ["systemctl", "--user", "daemon-reload"],
            True,
        ),
        (
            "runner",
            ["systemctl", "--user", "enable", "--now", "linux-whisper-stt.service"],
            True,
        ),
        ("disable_autostart",),
    ]


def test_install_service_removes_unit_when_enable_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    disable_autostart_called = False

    def fake_runner(args, check):
        if args == [
            "systemctl",
            "--user",
            "enable",
            "--now",
            "linux-whisper-stt.service",
        ]:
            raise subprocess.CalledProcessError(returncode=1, cmd=args)

    def fake_disable_autostart():
        nonlocal disable_autostart_called
        disable_autostart_called = True

    with pytest.raises(subprocess.CalledProcessError):
        install_service(
            command="/abs/linux-whisper-stt daemon",
            runner=fake_runner,
            disable_autostart=fake_disable_autostart,
        )

    assert not (tmp_path / "systemd/user/linux-whisper-stt.service").exists()
    assert disable_autostart_called is False


def test_install_service_removes_unit_when_systemctl_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    disable_autostart_called = False

    def fake_runner(args, check):
        raise FileNotFoundError("systemctl")

    def fake_disable_autostart():
        nonlocal disable_autostart_called
        disable_autostart_called = True

    with pytest.raises(FileNotFoundError):
        install_service(
            command="/abs/linux-whisper-stt daemon",
            runner=fake_runner,
            disable_autostart=fake_disable_autostart,
        )

    assert not (tmp_path / "systemd/user/linux-whisper-stt.service").exists()
    assert disable_autostart_called is False


def test_uninstall_service_disables_removes_and_reloads(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = tmp_path / "systemd/user/linux-whisper-stt.service"
    path.parent.mkdir(parents=True)
    path.write_text("[Unit]\n")
    calls = []

    def fake_runner(args, check):
        calls.append((args, check))

    removed_path = uninstall_service(runner=fake_runner)

    assert removed_path == path
    assert not path.exists()
    assert calls == [
        (
            ["systemctl", "--user", "disable", "--now", "linux-whisper-stt.service"],
            False,
        ),
        (["systemctl", "--user", "daemon-reload"], True),
    ]
