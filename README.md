# linux-whisper-stt

[![tests](https://github.com/jckceo/linux-whisper-stt/actions/workflows/tests.yml/badge.svg)](https://github.com/jckceo/linux-whisper-stt/actions/workflows/tests.yml)

Linux desktop dictation with a global shortcut, tray indicator, OpenAI or local Whisper transcription, and Wayland-friendly auto-paste.

`linux-whisper-stt` is a SuperWhisper-style tool for GNOME. Press a shortcut once to start recording, press it again to stop, and the app transcribes your speech, copies it to the clipboard, and can paste it into the active window.

## Features

- Global GNOME shortcut for start/stop dictation
- AppIndicator tray icon with state feedback and a Settings window
- OpenAI transcription via `gpt-4o-mini-transcribe`, `gpt-4o-transcribe`, or `whisper-1`
- User Dictionary/glossary for domain-specific terms such as ASIN, SKU, FNSKU, or product names
- Optional offline transcription through a locally built `whisper.cpp`
- Auto-paste on Wayland through clipboard paste via `ydotool`
- Clipboard fallback through `wl-copy`
- Autostart at login through a desktop entry
- Local audio and video file transcription from the tray, CLI, or file manager
- Per-event history with the recorded WAV/audio file and transcribed text

## Platform

Tested on Ubuntu 24.04 with GNOME 46 on Wayland.

The app expects:

- Python 3.12
- GNOME custom keybindings through `gsettings`
- GTK/libadwaita and Ayatana AppIndicator bindings
- `wl-clipboard`
- Optional `ydotool` and `ydotoold` integration for auto-paste
- `pw-record` for audio capture

## Install

Clone the repository, then run the conservative base installer:

```bash
./install.sh
```

Enable Wayland auto-paste:

```bash
./install.sh --with-autopaste
```

Enable offline transcription:

```bash
./install.sh --with-local-whisper
```

Install everything:

```bash
./install.sh --with-autopaste --with-local-whisper
```

The installer:

1. Installs required Ubuntu packages with `apt-get`.
2. Creates `.venv` with `--system-site-packages` so PyGObject can use system GTK bindings.
3. Installs this package in editable mode.
4. Optionally installs and enables a user `ydotoold` systemd service when `--with-autopaste` is passed.
5. Optionally builds `whisper.cpp` and downloads the `small` model for local transcription when `--with-local-whisper` is passed.
6. Registers an Open With desktop entry for audio/video files and refreshes the
   desktop database when `update-desktop-database` is available.
7. Writes an autostart file to `~/.config/autostart/linux-whisper-stt.desktop`.

If you enabled auto-paste, log out and back in once so group permissions for `ydotool` apply.

Then open Settings:

```bash
.venv/bin/linux-whisper-stt setup
```

Settings lets you save your OpenAI API key, choose the transcription engine, set
the language, edit the Dictionary/glossary, register the GNOME shortcut, toggle
`Auto-paste`, and control the `Start on startup` switch. Turning startup on
writes the desktop autostart entry; turning it off removes that entry.

## Start The App

The app starts automatically on the next login. To start it manually:

```bash
.venv/bin/linux-whisper-stt daemon
```

Check its state:

```bash
.venv/bin/linux-whisper-stt status
```

## Systemd User Service

Install and start the daemon as a systemd user service:

```bash
.venv/bin/linux-whisper-stt install-service
```

Installing the systemd user service removes the desktop autostart entry at
`~/.config/autostart/linux-whisper-stt.desktop` to avoid running duplicate
daemons. Use either Settings autostart or the systemd service, but not both at
the same time. If the systemd user service is installed, startup is managed by
that service and Settings will not create a duplicate desktop autostart entry.

Follow service logs:

```bash
journalctl --user -u linux-whisper-stt.service -f
```

Remove the service:

```bash
.venv/bin/linux-whisper-stt uninstall-service
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
6. If auto-paste is enabled, `ydotool` presses the paste shortcut in the active app.

## Tray Menu

The tray menu includes:

| Item | Action |
| --- | --- |
| Status | Shows idle, recording, transcribing, pasting, or error |
| Start / Stop recording | Toggles dictation |
| Transcribe file... | Chooses a local audio or video file to transcribe |
| Settings... | Opens one Settings window |
| Quit | Stops the tray process |

## File Transcription

Transcribe local media files from the tray menu with `Transcribe file...`, from
the file manager with `Open With -> Transcribe with linux-whisper-stt`, or from
the CLI with `transcribe-file <path>`.

File transcription uses the daemon's loaded Settings/config engine and
language. If you change Settings and a file job still uses the old engine or
language, restart or reload the daemon before starting the file job. When it
finishes, the final transcript is copied to the clipboard and shown in a popup.
Unlike shortcut dictation, file transcription is not auto-pasted into the active
app.

Audio and video inputs are normalized with `ffmpeg` before transcription. For
video files, history stores the extracted audio only, not a copy of the original
video. OpenAI transcription uploads are limited to 25 MB per file. Known-duration
OpenAI file jobs are transcoded to MP3 chunk or chunks, split when needed into
upload-safe chunks, transcribed, and merged into one text.

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
| `transcribe-file <path>` | Queue a local audio or video file for transcription |
| `install-open-with` | Register the file manager Open With desktop entry |
| `install-service` | Install and start the systemd user service |
| `uninstall-service` | Stop and remove the systemd user service |

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

[dictionary]
terms = ""
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

Use `Settings -> Dictionary` to add product names, acronyms, marketplace terms,
or other words that should keep a specific spelling. Entries can be comma
separated or written on separate lines. For OpenAI transcription the app sends
those entries as the transcription `prompt`, so terms such as `ASIN`, `SKU`,
`FNSKU`, `FBA`, or `reimbursement adjustments` are more likely to be preserved
correctly. The local `whisper.cpp` engine keeps the setting in config but does
not currently use it.

### Local whisper.cpp

When run with `--with-local-whisper`, the installer builds `whisper.cpp`, downloads the `small` model, and stores the model under:

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
wl-copy
ydotool key ctrl+shift+v
```

The transcribed text is copied to the clipboard first, then `ydotool` sends the
plain-text paste shortcut after a short delay. It does not type transcript
characters directly, which avoids keyboard-layout, Unicode, and held-modifier
issues.

Requirements:

- `ydotoold` is running
- `/dev/uinput` is writable for your user through the `input` group and udev rule
- you logged out and back in after installation
- `paste_mode = "auto"`

Disable auto-paste and use clipboard only from Settings, or set:

```toml
[general]
paste_mode = "clipboard_only"
```

## Security Notes

- `--with-autopaste` grants desktop input injection through `ydotool`.
- `--with-local-whisper` downloads and builds third-party code from `whisper.cpp`.
- OpenAI API keys are stored in the system keyring, not in TOML config.
- History saves each completed event under
  `~/.local/share/linux-whisper-stt/history` by default, including the
  transcripts and a recorded WAV/audio file managed by the app. Disable it with
  `[history] enabled = false`.

## History

History is available in `Settings -> History`.

When history is enabled, each completed event is stored in its own app-managed
directory:

```text
~/.local/share/linux-whisper-stt/history/<event-id>/event.json
~/.local/share/linux-whisper-stt/history/<event-id>/audio.wav
~/.local/share/linux-whisper-stt/history/<event-id>/transcript.txt
```

The event metadata records where the transcript came from, the engine, model,
language, status, duration, and original file name when applicable. In normal
operation, each completed event stores the transcript and a complete
app-managed audio file. For video transcription events, that audio file is the
extracted audio track. If the audio copy fails, the completed transcript event
is still preserved without audio.

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

Shortcut registration preserves existing GNOME custom shortcuts and only adds or updates the linux-whisper-stt entry.

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
Also check that Settings has `Auto-paste` enabled. If it is disabled, the text
will still be copied to the clipboard.

### Tray is red or stuck

Ask the daemon for the last error:

```bash
.venv/bin/linux-whisper-stt status
```

Restart the tray:

```bash
systemctl --user restart linux-whisper-stt.service
journalctl --user -u linux-whisper-stt.service -n 50 --no-pager
```

If you are not using the systemd service, quit the tray and restart it manually:

```bash
.venv/bin/linux-whisper-stt daemon
```

### Settings opens more than once

This should no longer happen. The tray tracks the Settings process and reuses it while it is open.

## Development

Run tests:

```bash
.venv/bin/python -m pytest
```

The test suite covers config parsing, IPC, recorder behavior, OpenAI/local transcription wrappers, output delivery, GNOME shortcut registration, autostart, tray behavior, Settings, and history.

## Known Limitations

- GNOME/Wayland is primary supported desktop target.
- Auto-paste depends on `/dev/uinput` access and may require logout/login.
- Local Whisper setup can take several minutes because it builds `whisper.cpp`.

## Roadmap

- Debian package or pipx-friendly installer.
- Better first-run diagnostics.
- Optional screenshot/GIF in README after a real UI capture is available.
- More desktop environment support.

## Development Attribution

Developed with Codex 5.5 xhigh.

## License

MIT. See [LICENSE](LICENSE).
