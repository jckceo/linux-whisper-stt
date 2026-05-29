from __future__ import annotations


def popup_title_for_event(event) -> str:
    name = event.original_name or event.id
    if event.status == "failed":
        return f"Transcription failed: {name}"
    return f"Transcription complete: {name}"


def gtk_major_version_for_result_window(required_version: str | None) -> int:
    if required_version is not None and required_version.startswith("3."):
        return 3
    return 4


def show_result_window(event, open_history_fn=lambda event_id: None) -> None:
    import gi

    if gtk_major_version_for_result_window(gi.get_required_version("Gtk")) == 3:
        _show_result_window_gtk3(event, open_history_fn, gi)
        return

    _show_result_window_gtk4(event, open_history_fn, gi)


def _result_text(event) -> str:
    return event.error if event.status == "failed" else event.transcript_text


def _show_result_window_gtk4(event, open_history_fn, gi) -> None:
    gi.require_version("Adw", "1")
    gi.require_version("Gtk", "4.0")
    from gi.repository import Adw, Gdk, Gtk

    Adw.init()

    text = _result_text(event)
    window = Adw.Window()
    window.set_title(popup_title_for_event(event))
    window.set_default_size(720, 520)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    box.set_margin_start(12)
    box.set_margin_end(12)

    scroller = Gtk.ScrolledWindow()
    scroller.set_vexpand(True)
    scroller.set_hexpand(True)

    buffer = Gtk.TextBuffer()
    buffer.set_text(text or "")
    text_view = Gtk.TextView(buffer=buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    scroller.set_child(text_view)
    box.append(scroller)

    buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    buttons.set_halign(Gtk.Align.END)

    copy_button = Gtk.Button(label="Copy")
    copy_button.connect(
        "clicked",
        lambda *_: Gdk.Display.get_default().get_clipboard().set(text or ""),
    )
    buttons.append(copy_button)

    history_button = Gtk.Button(label="Open history")
    history_button.connect("clicked", lambda *_: open_history_fn(event.id))
    buttons.append(history_button)

    close_button = Gtk.Button(label="Close")
    close_button.connect("clicked", lambda *_: window.close())
    buttons.append(close_button)

    box.append(buttons)
    window.set_content(box)
    window.present()


def _show_result_window_gtk3(event, open_history_fn, gi) -> None:
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gdk, Gtk

    text = _result_text(event)
    window = Gtk.Window(title=popup_title_for_event(event))
    window.set_default_size(720, 520)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.set_border_width(12)

    scroller = Gtk.ScrolledWindow()
    scroller.set_vexpand(True)
    scroller.set_hexpand(True)

    buffer = Gtk.TextBuffer()
    buffer.set_text(text or "")
    text_view = Gtk.TextView(buffer=buffer)
    text_view.set_editable(False)
    text_view.set_cursor_visible(False)
    text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    scroller.add(text_view)
    box.pack_start(scroller, True, True, 0)

    buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    buttons.set_halign(Gtk.Align.END)

    copy_button = Gtk.Button(label="Copy")

    def copy_text(*_):
        clipboard = Gtk.Clipboard.get_default(Gdk.Display.get_default())
        clipboard.set_text(text or "", -1)

    copy_button.connect("clicked", copy_text)
    buttons.pack_start(copy_button, False, False, 0)

    history_button = Gtk.Button(label="Open history")
    history_button.connect("clicked", lambda *_: open_history_fn(event.id))
    buttons.pack_start(history_button, False, False, 0)

    close_button = Gtk.Button(label="Close")
    close_button.connect("clicked", lambda *_: window.close())
    buttons.pack_start(close_button, False, False, 0)

    box.pack_start(buttons, False, False, 0)
    window.add(box)
    window.show_all()
