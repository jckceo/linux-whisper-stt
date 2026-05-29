from linux_whisper_stt.ui.setup_window import (
    apply_startup_preference,
    build_window_shell,
    dictionary_help_text,
    paste_mode_from_auto_paste,
    present_existing_window,
    read_text_buffer,
    settings_tab_labels,
    shortcut_tooltip_text,
)


def test_present_existing_window_reuses_active_window():
    class Window:
        def __init__(self):
            self.presented = False

        def present(self):
            self.presented = True

    class Application:
        def __init__(self):
            self.window = Window()

        def get_active_window(self):
            return self.window

    app = Application()

    assert present_existing_window(app) is True
    assert app.window.presented is True


def test_present_existing_window_allows_first_window_creation():
    class Application:
        def get_active_window(self):
            return None

    assert present_existing_window(Application()) is False


def test_apply_startup_preference_installs_when_enabled_and_service_is_missing():
    calls = []

    def fake_install():
        calls.append("install")

    def fake_uninstall():
        calls.append("uninstall")

    mode = apply_startup_preference(
        True,
        install_fn=fake_install,
        uninstall_fn=fake_uninstall,
        service_installed_fn=lambda: False,
    )

    assert mode == "enabled"
    assert calls == ["install"]


def test_apply_startup_preference_uninstalls_when_disabled_and_service_is_missing():
    calls = []

    def fake_install():
        calls.append("install")

    def fake_uninstall():
        calls.append("uninstall")

    mode = apply_startup_preference(
        False,
        install_fn=fake_install,
        uninstall_fn=fake_uninstall,
        service_installed_fn=lambda: False,
    )

    assert mode == "disabled"
    assert calls == ["uninstall"]


def test_apply_startup_preference_uses_systemd_when_service_is_installed():
    calls = []

    def fake_install():
        calls.append("install")

    def fake_uninstall():
        calls.append("uninstall")

    mode = apply_startup_preference(
        True,
        install_fn=fake_install,
        uninstall_fn=fake_uninstall,
        service_installed_fn=lambda: True,
    )

    assert mode == "systemd"
    assert calls == []


def test_paste_mode_from_auto_paste():
    assert paste_mode_from_auto_paste(True) == "auto"
    assert paste_mode_from_auto_paste(False) == "clipboard_only"


def test_settings_tab_labels():
    assert settings_tab_labels() == ["General", "Dictionary", "History"]


def test_read_text_buffer_returns_full_text():
    class Buffer:
        def get_bounds(self):
            return "start", "end"

        def get_text(self, start, end, include_hidden_chars):
            assert (start, end, include_hidden_chars) == ("start", "end", False)
            return "ASIN, FNSKU"

    assert read_text_buffer(Buffer()) == "ASIN, FNSKU"


def test_dictionary_help_text_explains_format_and_effect():
    text = dictionary_help_text()

    assert "comma" in text
    assert "one per line" in text
    assert "OpenAI" in text
    assert "ASIN" in text


def test_shortcut_tooltip_text_mentions_gtk_binding_format():
    text = shortcut_tooltip_text()

    assert "<Control><Alt>w" in text
    assert "save" in text.lower()


def test_build_window_shell_adds_close_button():
    class HeaderBar:
        def __init__(self):
            self.packed = []
            self.show_start_title_buttons = None
            self.show_end_title_buttons = None

        def pack_end(self, widget):
            self.packed.append(widget)

        def set_show_start_title_buttons(self, value):
            self.show_start_title_buttons = value

        def set_show_end_title_buttons(self, value):
            self.show_end_title_buttons = value

    class ToolbarView:
        def __init__(self):
            self.top_bars = []
            self.content = None

        def add_top_bar(self, widget):
            self.top_bars.append(widget)

        def set_content(self, widget):
            self.content = widget

    class Button:
        def __init__(self):
            self.tooltip = None
            self.clicked = None

        @classmethod
        def new_from_icon_name(cls, icon_name):
            button = cls()
            button.icon_name = icon_name
            return button

        def set_tooltip_text(self, text):
            self.tooltip = text

        def add_css_class(self, name):
            self.css_class = name

        def connect(self, event, callback):
            self.clicked = (event, callback)

    Adw = type("Adw", (), {"HeaderBar": HeaderBar, "ToolbarView": ToolbarView})
    Gtk = type("Gtk", (), {"Button": Button})

    class Window:
        def __init__(self):
            self.closed = False
            self.content = None

        def close(self):
            self.closed = True

        def set_content(self, content):
            self.content = content

    body = object()
    win = Window()

    shell = build_window_shell(Adw, Gtk, win, body)
    header = shell.top_bars[0]
    close_button = header.packed[0]
    event, callback = close_button.clicked
    callback()

    assert shell.content is body
    assert win.content is shell
    assert header.show_start_title_buttons is False
    assert header.show_end_title_buttons is False
    assert close_button.icon_name == "window-close-symbolic"
    assert close_button.tooltip == "Close"
    assert event == "clicked"
    assert win.closed is True
