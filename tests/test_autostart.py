from linux_whisper_stt.autostart import autostart_path, install_autostart


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
