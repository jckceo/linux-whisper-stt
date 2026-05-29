from linux_whisper_stt.gnome_shortcut import build_gsettings_commands, register_shortcut


def test_builds_four_gsettings_commands():
    cmds = build_gsettings_commands("<Control><Alt>space")
    assert len(cmds) == 4
    assert cmds[0][0] == "gsettings"
    assert "custom0" in cmds[0][-1]
    flat = [" ".join(c) for c in cmds]
    assert any("custom-keybindings" in f for f in flat)
    assert any("command" in f for f in flat)
    assert any("linux-whisper-stt toggle" in f for f in flat)
    assert any("<Control><Alt>space" in f for f in flat)


def test_register_runs_every_command():
    ran = []
    register_shortcut("<Super>d", runner=lambda cmd, **kw: ran.append(cmd))
    assert len(ran) == 4
