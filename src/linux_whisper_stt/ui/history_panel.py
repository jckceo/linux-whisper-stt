from __future__ import annotations

import subprocess


def event_title(event) -> str:
    return (
        getattr(event, "original_name", "")
        or getattr(event, "created_at", "")
        or getattr(event, "id", "")
    )


def metadata_lines(event) -> list[str]:
    lines = []
    source_type = getattr(event, "source_type", "")
    status = getattr(event, "status", "")
    engine = getattr(event, "engine", "")
    model = getattr(event, "model", "")
    language = getattr(event, "language", "")
    duration_seconds = getattr(event, "duration_seconds", None)
    error = getattr(event, "error", "")

    if source_type:
        lines.append(f"Source: {source_type}")
    if status:
        lines.append(f"Status: {status}")
    if engine:
        lines.append(f"Engine: {engine}")
    if model:
        lines.append(f"Model: {model}")
    if language:
        lines.append(f"Language: {language}")
    if duration_seconds is not None:
        lines.append(f"Duration: {duration_seconds:.1f}s")
    if error:
        lines.append(f"Error: {error}")
    return lines


def open_audio(path: str, runner=subprocess.Popen) -> None:
    if path:
        runner(["xdg-open", path])


def build_history_tab(Gtk, history_store, copy_fn, open_audio_fn=open_audio):
    selected_event = {"event": None}

    root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    root.set_margin_top(18)
    root.set_margin_bottom(18)
    root.set_margin_start(18)
    root.set_margin_end(18)

    list_scroller = Gtk.ScrolledWindow()
    list_scroller.set_vexpand(True)
    list_scroller.set_hexpand(False)

    list_box = Gtk.ListBox()
    list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
    list_scroller.set_child(list_box)
    root.append(list_scroller)

    detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    detail.set_hexpand(True)
    detail.set_vexpand(True)

    title_label = Gtk.Label(label="Select a history item", xalign=0)
    title_label.set_wrap(True)
    detail.append(title_label)

    metadata_label = Gtk.Label(label="", xalign=0)
    metadata_label.set_wrap(True)
    detail.append(metadata_label)

    transcript_buffer = Gtk.TextBuffer()
    transcript_view = Gtk.TextView(buffer=transcript_buffer)
    transcript_view.set_editable(False)
    transcript_view.set_cursor_visible(False)
    transcript_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

    transcript_scroller = Gtk.ScrolledWindow()
    transcript_scroller.set_hexpand(True)
    transcript_scroller.set_vexpand(True)
    transcript_scroller.set_child(transcript_view)
    detail.append(transcript_scroller)

    buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    buttons.set_halign(Gtk.Align.END)

    copy_button = Gtk.Button(label="Copy")
    open_button = Gtk.Button(label="Open audio file")
    delete_button = Gtk.Button(label="Delete")
    for button in (copy_button, open_button, delete_button):
        button.set_sensitive(False)
        buttons.append(button)
    detail.append(buttons)
    root.append(detail)

    def show_event(event) -> None:
        selected_event["event"] = event
        has_event = event is not None
        title_label.set_text(event_title(event) if has_event else "Select a history item")
        metadata_label.set_text("\n".join(metadata_lines(event)) if has_event else "")
        transcript_buffer.set_text(
            getattr(event, "transcript_text", "") if has_event else ""
        )
        copy_button.set_sensitive(has_event)
        open_button.set_sensitive(bool(getattr(event, "audio_path", "") if has_event else ""))
        delete_button.set_sensitive(has_event)

    def clear_rows() -> None:
        row = list_box.get_first_child()
        while row is not None:
            list_box.remove(row)
            row = list_box.get_first_child()

    def load_rows() -> None:
        clear_rows()
        for event in history_store.list_events():
            row = Gtk.ListBoxRow()
            row.history_event = event
            label = Gtk.Label(label=event_title(event), xalign=0)
            label.set_wrap(True)
            row.set_child(label)
            list_box.append(row)

    def on_row_selected(_list_box, row) -> None:
        show_event(getattr(row, "history_event", None) if row is not None else None)

    def on_copy(_button) -> None:
        event = selected_event["event"]
        if event is not None:
            copy_fn(getattr(event, "transcript_text", "") or "")

    def on_open(_button) -> None:
        event = selected_event["event"]
        if event is not None:
            open_audio_fn(getattr(event, "audio_path", ""))

    def on_delete(_button) -> None:
        event = selected_event["event"]
        if event is None:
            return
        history_store.delete_event(event.id)
        load_rows()
        first_row = list_box.get_first_child()
        if first_row is not None:
            list_box.select_row(first_row)
        else:
            show_event(None)

    list_box.connect("row-selected", on_row_selected)
    copy_button.connect("clicked", on_copy)
    open_button.connect("clicked", on_open)
    delete_button.connect("clicked", on_delete)
    load_rows()

    return root
