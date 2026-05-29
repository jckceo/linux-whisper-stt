from linux_whisper_stt.gnome_shortcut import (
    CUSTOM_PATH,
    build_gsettings_commands,
    merge_custom_keybinding_paths,
    read_custom_keybinding_paths,
    register_shortcut,
)


def test_builds_four_gsettings_commands():
    cmds = build_gsettings_commands("<Control><Alt>space", existing_paths=[])
    assert len(cmds) == 4
    assert cmds[0][0] == "gsettings"
    assert "linux-whisper-stt" in cmds[0][-1]
    assert "custom0" not in cmds[0][-1]
    flat = [" ".join(c) for c in cmds]
    assert any("custom-keybindings" in f for f in flat)
    assert any("command" in f for f in flat)
    assert any("linux-whisper-stt toggle" in f for f in flat)
    assert any("<Control><Alt>space" in f for f in flat)


def test_custom_path_is_app_owned():
    assert "linux-whisper-stt" in CUSTOM_PATH
    assert "custom0" not in CUSTOM_PATH


def test_register_runs_every_command():
    ran = []

    def runner(cmd, **kw):
        ran.append(cmd)

        class Result:
            stdout = "[]\n"

        return Result()

    register_shortcut("<Super>d", runner=runner)
    assert len(ran) == 5
    assert len([cmd for cmd in ran if cmd[1] == "set"]) == 4


def test_merge_custom_keybinding_paths_preserves_existing_and_appends_custom_once():
    existing = ["/existing/", CUSTOM_PATH]

    paths = merge_custom_keybinding_paths(existing)

    assert paths == ["/existing/", CUSTOM_PATH]


def test_merge_custom_keybinding_paths_appends_custom_path():
    paths = merge_custom_keybinding_paths(["/existing/"])

    assert paths == ["/existing/", CUSTOM_PATH]


def test_merge_custom_keybinding_paths_deduplicates_custom_path_only():
    paths = merge_custom_keybinding_paths(["/existing/", "/existing/", CUSTOM_PATH])

    assert paths == ["/existing/", "/existing/", CUSTOM_PATH]


def test_read_custom_keybinding_paths_parses_gsettings_stdout():
    def runner(cmd, **kwargs):
        assert cmd == [
            "gsettings",
            "get",
            "org.gnome.settings-daemon.plugins.media-keys",
            "custom-keybindings",
        ]
        assert kwargs == {"check": True, "capture_output": True, "text": True}

        class Result:
            stdout = "['/existing/']\n"

        return Result()

    assert read_custom_keybinding_paths(runner=runner) == ["/existing/"]


def test_read_custom_keybinding_paths_handles_gvariant_empty_array():
    def runner(cmd, **kwargs):
        class Result:
            stdout = "@as []\n"

        return Result()

    assert read_custom_keybinding_paths(runner=runner) == []


def test_read_custom_keybinding_paths_handles_empty_array():
    def runner(cmd, **kwargs):
        class Result:
            stdout = "[]\n"

        return Result()

    assert read_custom_keybinding_paths(runner=runner) == []


def test_read_custom_keybinding_paths_ignores_non_list_output():
    def runner(cmd, **kwargs):
        class Result:
            stdout = "'/existing/'\n"

        return Result()

    assert read_custom_keybinding_paths(runner=runner) == []


def test_read_custom_keybinding_paths_handles_malformed_output():
    def runner(cmd, **kwargs):
        class Result:
            stdout = "@as [broken\n"

        return Result()

    assert read_custom_keybinding_paths(runner=runner) == []


def test_register_preserves_existing_custom_keybindings():
    calls = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class Result:
            stdout = "['/existing/']\n"

        return Result()

    register_shortcut("<Super>d", runner=runner)

    assert calls[0] == (
        [
            "gsettings",
            "get",
            "org.gnome.settings-daemon.plugins.media-keys",
            "custom-keybindings",
        ],
        {"check": True, "capture_output": True, "text": True},
    )
    assert calls[1][0] == [
        "gsettings",
        "set",
        "org.gnome.settings-daemon.plugins.media-keys",
        "custom-keybindings",
        f"['/existing/', '{CUSTOM_PATH}']",
    ]
