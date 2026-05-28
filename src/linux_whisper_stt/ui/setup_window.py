from __future__ import annotations


def run_setup() -> int:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gtk

    from ..config import load_config, save_config
    from ..gnome_shortcut import register_shortcut
    from ..autostart import install_autostart
    from ..secrets import get_api_key, set_api_key

    config = load_config()

    app = Adw.Application(application_id="com.github.linux_whisper_stt.Setup")

    def on_activate(application):
        win = Adw.ApplicationWindow(application=application)
        win.set_title("linux-whisper-stt — Setup")
        win.set_default_size(460, 360)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18); box.set_margin_bottom(18)
        box.set_margin_start(18); box.set_margin_end(18)

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

        status = Gtk.Label(label="", xalign=0)

        def on_save(_btn):
            key = key_entry.get_text().strip()
            if key:
                set_api_key(key)
            config.general.engine = ["openai", "local"][engine_combo.get_selected()]
            config.general.language = lang_entry.get_text().strip() or "auto"
            config.shortcut.binding = shortcut_entry.get_text().strip() or "<Control><Alt>space"
            save_config(config)
            register_shortcut(config.shortcut.binding)
            install_autostart()
            status.set_text("Saved. Shortcut registered. Autostart enabled.")

        save_btn = Gtk.Button(label="Save & register shortcut")
        save_btn.connect("clicked", on_save)
        box.append(save_btn)
        box.append(status)

        win.set_content(box)
        win.present()

    app.connect("activate", on_activate)
    return app.run([])
