from dataclasses import dataclass

from linux_whisper_stt.ui.history_panel import (
    HISTORY_LIST_MIN_WIDTH,
    build_history_tab,
    event_title,
    metadata_lines,
    open_audio,
)


@dataclass
class Event:
    id: str = "evt-1"
    created_at: str = "2026-05-29T12:34:56"
    source_type: str = "microphone"
    status: str = "completed"
    engine: str = "openai"
    model: str = "gpt-4o-mini-transcribe"
    language: str = "it"
    duration_seconds: float | None = 65.234
    error: str = ""
    original_name: str = ""
    audio_path: str = "/tmp/audio.wav"
    transcript_text: str = "hello"
    legacy: bool = False


def test_event_title_prefers_original_name_then_created_at_then_id():
    assert event_title(Event(original_name="meeting.wav")) == "meeting.wav"
    assert event_title(Event(created_at="2026-05-29T10:00:00")) == "2026-05-29T10:00:00"
    assert event_title(Event(created_at="", id="fallback")) == "fallback"


def test_metadata_lines_includes_available_history_fields():
    event = Event(error="network failed")

    assert metadata_lines(event) == [
        "Source: microphone",
        "Status: completed",
        "Engine: openai",
        "Model: gpt-4o-mini-transcribe",
        "Language: it",
        "Duration: 65.2s",
        "Error: network failed",
    ]


def test_metadata_lines_omits_missing_optional_fields():
    event = Event(
        source_type="",
        status="failed",
        engine="",
        model="",
        language="",
        duration_seconds=None,
        error="boom",
    )

    assert metadata_lines(event) == [
        "Status: failed",
        "Error: boom",
    ]


def test_open_audio_uses_audio_player_when_path_is_present():
    calls = []

    message = open_audio(
        "/tmp/audio.wav",
        runner=lambda argv: calls.append(argv),
        which=lambda name: "/usr/bin/pw-play" if name == "pw-play" else None,
        exists_fn=lambda path: True,
    )

    assert calls == [["pw-play", "/tmp/audio.wav"]]
    assert message == "Opening audio file with pw-play"


def test_open_audio_falls_back_to_xdg_open_when_no_player_is_found():
    calls = []

    message = open_audio(
        "/tmp/audio.wav",
        runner=lambda argv: calls.append(argv),
        which=lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None,
        exists_fn=lambda path: True,
    )

    assert calls == [["xdg-open", "/tmp/audio.wav"]]
    assert message == "Opening audio file with xdg-open"


def test_open_audio_reports_missing_file():
    calls = []

    message = open_audio(
        "/tmp/missing.wav",
        runner=lambda argv: calls.append(argv),
        exists_fn=lambda path: False,
    )

    assert calls == []
    assert message == "Audio file not found: /tmp/missing.wav"


def test_open_audio_ignores_blank_path():
    calls = []

    message = open_audio("", runner=lambda argv: calls.append(argv))

    assert calls == []
    assert message == "No audio file saved for this history item"


def test_build_history_tab_selects_copies_opens_and_deletes_event():
    event = Event()
    store = FakeHistoryStore([event])
    copied = []
    opened = []

    tab = build_history_tab(
        FakeGtk,
        store,
        copy_fn=lambda text: copied.append(text),
        open_audio_fn=lambda path: opened.append(path) or "Opened audio file",
    )

    list_box = tab.children[0].child
    assert tab.children[0].min_content_width == HISTORY_LIST_MIN_WIDTH
    row = list_box.rows[0]
    list_box.select_row(row)

    detail = tab.children[1]
    title_label = detail.children[0]
    metadata_label = detail.children[1]
    scroller = detail.children[2]
    buttons = detail.children[3]

    assert title_label.label == "2026-05-29T12:34:56"
    assert metadata_label.label == "\n".join(metadata_lines(event))
    assert scroller.child.buffer.text == "hello"

    buttons.children[0].click()
    buttons.children[1].click()
    buttons.children[2].click()

    assert copied == ["hello"]
    assert opened == ["/tmp/audio.wav"]
    assert detail.children[4].label == "Opened audio file"
    assert store.deleted == ["evt-1"]


def test_build_history_tab_disables_and_ignores_delete_for_legacy_event():
    event = Event(id="legacy", legacy=True)
    store = FakeHistoryStore([event])
    copied = []
    opened = []

    tab = build_history_tab(
        FakeGtk,
        store,
        copy_fn=lambda text: copied.append(text),
        open_audio_fn=lambda path: opened.append(path),
    )

    list_box = tab.children[0].child
    list_box.select_row(list_box.rows[0])

    buttons = tab.children[1].children[3]
    copy_button = buttons.children[0]
    open_button = buttons.children[1]
    delete_button = buttons.children[2]

    assert copy_button.sensitive is True
    assert open_button.sensitive is True
    assert delete_button.sensitive is False

    copy_button.click()
    open_button.click()
    delete_button.click()

    assert copied == ["hello"]
    assert opened == ["/tmp/audio.wav"]
    assert store.deleted == []


class FakeHistoryStore:
    def __init__(self, events):
        self.events = events
        self.deleted = []

    def list_events(self):
        return list(self.events)

    def delete_event(self, event_id):
        self.deleted.append(event_id)
        self.events = [event for event in self.events if event.id != event_id]


class FakeOrientation:
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class FakeSelectionMode:
    SINGLE = "single"


class FakeWrapMode:
    WORD_CHAR = "word-char"


class FakeAlign:
    END = "end"


class FakeGtk:
    Orientation = FakeOrientation
    SelectionMode = FakeSelectionMode
    WrapMode = FakeWrapMode
    Align = FakeAlign

    class Box:
        def __init__(self, orientation=None, spacing=0):
            self.orientation = orientation
            self.spacing = spacing
            self.children = []
            self.hexpand = False
            self.vexpand = False
            self.halign = None
            self.margins = {}

        def append(self, child):
            self.children.append(child)

        def set_hexpand(self, value):
            self.hexpand = value

        def set_vexpand(self, value):
            self.vexpand = value

        def set_halign(self, value):
            self.halign = value

        def set_margin_top(self, value):
            self.margins["top"] = value

        def set_margin_bottom(self, value):
            self.margins["bottom"] = value

        def set_margin_start(self, value):
            self.margins["start"] = value

        def set_margin_end(self, value):
            self.margins["end"] = value

    class ScrolledWindow:
        def __init__(self):
            self.child = None
            self.hexpand = False
            self.vexpand = False
            self.min_content_width = None

        def set_child(self, child):
            self.child = child

        def set_hexpand(self, value):
            self.hexpand = value

        def set_vexpand(self, value):
            self.vexpand = value

        def set_min_content_width(self, value):
            self.min_content_width = value

    class ListBox:
        def __init__(self):
            self.rows = []
            self.selected_row = None
            self.callbacks = {}

        def set_selection_mode(self, mode):
            self.selection_mode = mode

        def append(self, row):
            self.rows.append(row)

        def remove(self, row):
            self.rows.remove(row)

        def get_first_child(self):
            return self.rows[0] if self.rows else None

        def connect(self, event, callback):
            self.callbacks[event] = callback

        def get_selected_row(self):
            return self.selected_row

        def select_row(self, row):
            self.selected_row = row
            self.callbacks["row-selected"](self, row)

    class ListBoxRow:
        def __init__(self):
            self.child = None

        def set_child(self, child):
            self.child = child

    class Label:
        def __init__(self, label="", xalign=None):
            self.label = label
            self.xalign = xalign
            self.wrap = False
            self.hexpand = False

        def set_text(self, text):
            self.label = text

        def set_wrap(self, value):
            self.wrap = value

        def set_xalign(self, value):
            self.xalign = value

        def set_hexpand(self, value):
            self.hexpand = value

    class TextBuffer:
        def __init__(self):
            self.text = ""

        def set_text(self, text):
            self.text = text

    class TextView:
        def __init__(self, buffer=None):
            self.buffer = buffer

        def set_editable(self, value):
            self.editable = value

        def set_cursor_visible(self, value):
            self.cursor_visible = value

        def set_wrap_mode(self, value):
            self.wrap_mode = value

    class Button:
        def __init__(self, label=""):
            self.label = label
            self.callbacks = {}
            self.sensitive = True

        def connect(self, event, callback):
            self.callbacks[event] = callback

        def click(self):
            self.callbacks["clicked"](self)

        def set_sensitive(self, value):
            self.sensitive = value
