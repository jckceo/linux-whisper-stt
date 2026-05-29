# linux-whisper-stt

Linux desktop dictation with a global shortcut, tray indicator, OpenAI or local Whisper transcription, and Wayland-friendly auto-paste.

`linux-whisper-stt` is a SuperWhisper-style tool for GNOME. Press a shortcut once to start recording, press it again to stop, and the app transcribes your speech and types the result into the active window.

## Features

- Global GNOME shortcut for start/stop dictation
- AppIndicator tray icon with state feedback and a Settings window
- OpenAI transcription via `gpt-4o-mini-transcribe`, `gpt-4o-transcribe`, or `whisper-1`
- Optional offline transcription through a locally built `whisper.cpp`
- Auto-paste on Wayland through `ydotool type --file -`
- Clipboard fallback through `wl-copy`
- Autostart at login through a desktop entry
- Per-dictation history with the recorded WAV and transcribed text

## Platform

Tested on Ubuntu 24.04 with GNOME 46 on Wayland.

The app expects:

- Python 3.12
- GNOME custom keybindings through `gsettings`
- GTK/libadwaita and Ayatana AppIndicator bindings
- `wl-clipboard`
- `ydotool` and `ydotoold` for auto-paste
- `pw-record` for audio capture

## Install

Clone the repository, then run:

```bash
./install.sh
```

The installer:

1. Installs required Ubuntu packages with `apt-get`.
2. Creates `.venv` with `--system-site-packages` so PyGObject can use system GTK bindings.
3. Installs this package in editable mode.
4. Installs and enables a user `ydotoold` systemd service.
5. Builds `whisper.cpp` and downloads the `small` model for local transcription.
6. Writes an autostart file to `~/.config/autostart/linux-whisper-stt.desktop`.

After installation, log out and back in once so group permissions for `ydotool` apply.

Then open Settings:

```bash
.venv/bin/linux-whisper-stt setup
```

Settings lets you save your OpenAI API key, choose the transcription engine, set the language, and register the GNOME shortcut.

## Start The App

The app starts automatically on the next login. To start it manually:

```bash
.venv/bin/linux-whisper-stt daemon
```

Check its state:

```bash
.venv/bin/linux-whisper-stt status
```

## Usage

Default shortcut:

```text
Ctrl+Alt+Space
```

If your desktop already captures that shortcut, open Settings and change it. `Ctrl+Alt+W` works well on many GNOME systems.

Workflow:

1. Press the shortcut to start recording.
2. Speak.
3. Press the shortcut again to stop.
4. The tray icon switches to transcribing.
5. The result is copied to the clipboard.
6. If auto-paste is enabled, `ydotool` types the text into the active app.

## Tray Menu

The tray menu includes:

| Item | Action |
| --- | --- |
| Status | Shows idle, recording, transcribing, pasting, or error |
| Start / Stop recording | Toggles dictation |
| Settings... | Opens one Settings window |
| Quit | Stops the tray process |

## CLI

Use `.venv/bin/linux-whisper-stt <command>` from the repository:

| Command | Description |
| --- | --- |
| `daemon` | Start the tray app and IPC server |
| `daemon --dry-run` | Start without GTK tray UI, useful for tests |
| `toggle` | Start or stop recording |
| `start` | Start recording |
| `stop` | Stop recording |
| `status` | Print daemon state and last error |
| `setup` | Open the Settings window |

`toggle`, `start`, `stop`, and `status` talk to the daemon over a Unix socket at:

```text
$XDG_RUNTIME_DIR/linux-whisper-stt.sock
```

## Configuration

Config file:

```text
~/.config/linux-whisper-stt/config.toml
```

Defaults:

```toml
[general]
engine = "openai"
language = "auto"
paste_mode = "auto"
sounds = true

[shortcut]
binding = "<Control><Alt>space"

[openai]
model = "gpt-4o-mini-transcribe"

[local]
model = "small"
models_dir = "~/.local/share/linux-whisper-stt/models"
binary_path = ""

[audio]
device = "default"
samplerate = 16000
max_seconds = 300

[history]
enabled = true
dir = "~/.local/share/linux-whisper-stt/history"
```

Unknown keys are ignored. The config file is written with mode `0600`.

## Transcription Engines

### OpenAI

OpenAI is the default engine. The API key is stored in the system keyring under:

```text
service: linux-whisper-stt
username: openai
```

Recommended model:

```toml
[openai]
model = "gpt-4o-mini-transcribe"
```

### Local whisper.cpp

The installer builds `whisper.cpp`, downloads the `small` model, and stores the model under:

```text
~/.local/share/linux-whisper-stt/models
```

Set this in config or through Settings:

```toml
[general]
engine = "local"
```

The local engine invokes `whisper-cli` with the configured model and language.

## Auto-paste

Auto-paste uses:

```bash
ydotool type --file -
```

The transcribed text is passed on stdin. This avoids the broken `Ctrl+V` simulation path on some Wayland sessions.

Requirements:

- `ydotoold` is running
- `/dev/uinput` is writable for your user through the `input` group and udev rule
- you logged out and back in after installation
- `paste_mode = "auto"`

Disable auto-paste and use clipboard only:

```toml
[general]
paste_mode = "clipboard_only"
```

## History

When history is enabled, each dictation is saved as:

```text
~/.local/share/linux-whisper-stt/history/YYYYMMDD-HHMMSS.wav
~/.local/share/linux-whisper-stt/history/YYYYMMDD-HHMMSS.txt
```

Disable it:

```toml
[history]
enabled = false
```

## Troubleshooting

### Shortcut does nothing

Check the registered GNOME command:

```bash
gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings
```

Then open Settings and save the shortcut again:

```bash
.venv/bin/linux-whisper-stt setup
```

If `Ctrl+Alt+Space` is already used by the desktop, change it to another binding such as `<Control><Alt>w`.

### Daemon is not running

Start it manually:

```bash
.venv/bin/linux-whisper-stt daemon
```

Or log out and back in so the autostart entry runs.

### Auto-paste does not work

Check:

```bash
systemctl --user status ydotoold
id
ls -l /dev/uinput
```

If group membership changed during install, log out and back in.

### Tray is red or stuck

Ask the daemon for the last error:

```bash
.venv/bin/linux-whisper-stt status
```

Restart the tray:

```bash
systemctl --user stop linux-whisper-stt-daemon.service
systemd-run --user --unit=linux-whisper-stt-daemon --collect "$PWD/.venv/bin/linux-whisper-stt" daemon
```

### Settings opens more than once

This should no longer happen. The tray tracks the Settings process and reuses it while it is open.

## Development

Run tests:

```bash
.venv/bin/python -m pytest
```

The test suite covers config parsing, IPC, recorder behavior, OpenAI/local transcription wrappers, output delivery, GNOME shortcut registration, autostart, tray behavior, Settings, and history.

## License

MIT. See [LICENSE](LICENSE).
