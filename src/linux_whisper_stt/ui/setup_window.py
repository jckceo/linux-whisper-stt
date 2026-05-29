from __future__ import annotations


def present_existing_window(application) -> bool:
    win = application.get_active_window()
    if win is None:
        return False
    win.present()
    return True


def build_window_shell(Adw, Gtk, win, content):
    toolbar = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_show_start_title_buttons(False)
    header.set_show_end_title_buttons(False)
    close_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
    close_button.set_tooltip_text("Close")
    close_button.add_css_class("flat")
    close_button.connect("clicked", lambda *_: win.close())
    header.pack_end(close_button)
    toolbar.add_top_bar(header)
    toolbar.set_content(content)
    win.set_content(toolbar)
    return toolbar


def apply_startup_preference(
    enabled: bool,
    install_fn=None,
    uninstall_fn=None,
    service_installed_fn=None,
):
    from ..autostart import install_autostart, uninstall_autostart
    from ..systemd import service_installed

    install_fn = install_fn or install_autostart
    uninstall_fn = uninstall_fn or uninstall_autostart
    service_installed_fn = service_installed_fn or service_installed
    if service_installed_fn():
        return "systemd"
    if enabled:
        install_fn()
        return "enabled"
    uninstall_fn()
    return "disabled"


def paste_mode_from_auto_paste(enabled: bool) -> str:
    return "auto" if enabled else "clipboard_only"


def run_setup() -> int:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gtk

    from ..autostart import autostart_enabled
    from ..config import load_config, save_config
    from ..gnome_shortcut import register_shortcut
    from ..secrets import get_api_key, set_api_key
    from ..systemd import service_installed

    config = load_config()

    app = Adw.Application(application_id="com.github.linux_whisper_stt.Setup")

    def on_activate(application):
        if present_existing_window(application):
            return

        win = Adw.ApplicationWindow(application=application)
        win.set_title("linux-whisper-stt — Setup")
        win.set_default_size(460, 360)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)

        # API key
        box.append(Gtk.Label(label="OpenAI API key", xalign=0))
        key_entry = Gtk.PasswordEntry(show_peek_icon=True)
        existing = get_api_key()
        if existing:
            key_entry.set_text(existing)
        box.append(key_entry)

        # Engine
        box.append(Gtk.Label(label="Engine", xalign=0))
        engine_combo = Gtk.DropDown.new_from_strings(["openai", "local"])
        engine_combo.set_selected(0 if config.general.engine == "openai" else 1)
        box.append(engine_combo)

        # Language
        box.append(Gtk.Label(label="Language", xalign=0))
        lang_entry = Gtk.Entry(text=config.general.language)
        box.append(lang_entry)

        # Shortcut
        box.append(Gtk.Label(label="Shortcut", xalign=0))
        shortcut_entry = Gtk.Entry(text=config.shortcut.binding)
        box.append(shortcut_entry)

        auto_paste_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        auto_paste_label = Gtk.Label(label="Auto-paste", xalign=0)
        auto_paste_label.set_hexpand(True)
        auto_paste_row.append(auto_paste_label)
        auto_paste_switch = Gtk.Switch()
        auto_paste_switch.set_active(config.general.paste_mode == "auto")
        auto_paste_row.append(auto_paste_switch)
        box.append(auto_paste_row)

        startup_service_installed = service_installed()
        startup_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        startup_label = Gtk.Label(label="Start on startup", xalign=0)
        startup_label.set_hexpand(True)
        startup_row.append(startup_label)
        startup_switch = Gtk.Switch()
        startup_switch.set_active(startup_service_installed or autostart_enabled())
        if startup_service_installed:
            startup_switch.set_sensitive(False)
        startup_row.append(startup_switch)
        box.append(startup_row)

        status = Gtk.Label(label="", xalign=0)

        def on_save(_btn):
            try:
                key = key_entry.get_text().strip()
                if key:
                    set_api_key(key)
                config.general.engine = ["openai", "local"][engine_combo.get_selected()]
                config.general.language = lang_entry.get_text().strip() or "auto"
                config.general.paste_mode = paste_mode_from_auto_paste(
                    auto_paste_switch.get_active()
                )
                config.shortcut.binding = shortcut_entry.get_text().strip() or "<Control><Alt>space"
                save_config(config)
                register_shortcut(config.shortcut.binding)
                startup_mode = apply_startup_preference(startup_switch.get_active())
                if startup_mode == "systemd":
                    status.set_text(
                        "Saved. Shortcut registered. Startup is managed by systemd service."
                    )
                elif startup_mode == "enabled":
                    status.set_text(
                        "Saved. Shortcut registered. Start on startup enabled."
                    )
                else:
                    status.set_text(
                        "Saved. Shortcut registered. Start on startup disabled."
                    )
            except Exception as e:
                status.set_text(f"Error: {e}")

        save_btn = Gtk.Button(label="Save & register shortcut")
        save_btn.connect("clicked", on_save)
        box.append(save_btn)
        box.append(status)

        build_window_shell(Adw, Gtk, win, box)
        win.present()

    app.connect("activate", on_activate)
    return app.run([])
