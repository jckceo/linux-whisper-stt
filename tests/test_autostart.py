from linux_whisper_stt.autostart import (
    autostart_path,
    install_autostart,
    uninstall_autostart,
)


def test_autostart_path_default(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = autostart_path()
    assert p.parts[-2:] == ("autostart", "linux-whisper-stt.desktop")


def test_install_writes_desktop_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = install_autostart()
    content = p.read_text()
    assert "linux-whisper-stt daemon" in content  # Exec uses the absolute path
    assert "[Desktop Entry]" in content
    assert "X-GNOME-Autostart-enabled=true" in content


def test_uninstall_autostart_removes_desktop_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = install_autostart()

    removed = uninstall_autostart()

    assert removed == p
    assert not p.exists()


def test_uninstall_autostart_ignores_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = autostart_path()

    removed = uninstall_autostart()

    assert removed == p
    assert not p.exists()
