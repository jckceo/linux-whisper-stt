# linux-whisper-stt

A SuperWhisper-style push-a-shortcut dictation tool for Linux. Press a global keyboard shortcut to start recording your microphone; press it again to stop. The audio is transcribed using either the OpenAI Whisper API or a local whisper.cpp binary, then the resulting text is automatically pasted at the cursor via `ydotool` (with clipboard fallback when ydotool is unavailable). The application runs as a background daemon controlled via an AppIndicator tray icon that changes appearance to reflect the current state.

---

## How it works

1. The daemon starts and sits in the system tray showing an "idle" icon.
2. You press the configured shortcut (default `Ctrl+Alt+Space`). GNOME fires `linux-whisper-stt toggle`, which sends a command over a Unix socket to the running daemon.
3. The daemon begins recording audio from the microphone. The tray icon changes to "recording" and a start sound plays.
4. You press the shortcut again. A stop sound plays, recording ends, and the daemon enters "transcribing" state.
5. The WAV file is sent to the configured transcription engine (OpenAI API or local whisper.cpp). While transcribing, the tray shows a "busy" icon.
6. On success the transcribed text is copied to the clipboard. If `ydotool` is available and `paste_mode` is `auto`, the daemon also synthesises a `Ctrl+V` keystroke via `ydotool key` to paste it at the cursor. Otherwise the text is ready in the clipboard for you to paste manually.
7. The tray returns to idle. On any error the icon turns to "error" and the error message is stored as `last_error` (visible via `linux-whisper-stt status`).

The shortcut is registered as a GNOME custom keybinding pointing at the `linux-whisper-stt toggle` command. The daemon autostarts at login via a `.desktop` file written to `~/.config/autostart/`.

---

## Requirements

- Linux with GNOME on Wayland (tested on Ubuntu 24.04 / GNOME 46)
- Python 3.12 (system package)
- System packages installed by `install.sh`:
  - `wl-clipboard` — Wayland clipboard integration
  - `ydotool` / `ydotoold` — Wayland-compatible input event injection for auto-paste
  - `ffmpeg` — audio tooling (used by some whisper.cpp workflows)
  - `gir1.2-ayatanaappindicator3-0.1`, `gir1.2-gtk-4.0`, `gir1.2-adw-1` — GTK / tray GObject introspection bindings
  - `build-essential`, `cmake`, `git` — for compiling whisper.cpp (local engine only)
- For the OpenAI engine: an OpenAI API key with access to the audio transcriptions endpoint.
- For the local engine: whisper.cpp compiled by `install.sh`.

---

## Install

```bash
./install.sh
```

`install.sh` does the following in order:

1. Installs system packages via `apt-get`.
2. Creates `.venv` with `--system-site-packages` (required for PyGObject bindings) and installs the package in editable mode.
3. Creates a `udev` rule so `ydotool` can access `/dev/uinput`, adds you to the `input` group, and installs a user-level systemd service for `ydotoold`.
4. Clones and compiles whisper.cpp into `.whisper.cpp/` and downloads the `small` GGML model to `~/.local/share/linux-whisper-stt/models/`.
5. Writes the whisper.cpp binary path into the config file.
6. Installs the autostart `.desktop` entry.

After installation, run the interactive setup wizard:

```bash
linux-whisper-stt setup
```

The setup window lets you enter your OpenAI API key (stored in the system keyring via `keyring`), choose the engine, language, and shortcut binding, then registers the GNOME custom keybinding.

Finally, log out and back in so the `input` group membership takes effect for ydotool auto-paste.

---

## Usage

### Shortcut

The default shortcut is `Ctrl+Alt+Space` (configured as `<Control><Alt>space` in GNOME). Press it once to start recording, press it again to stop and transcribe.

### Tray menu

Right-click (or left-click, depending on your desktop) the tray icon to see:

| Menu item | Action |
|-----------|--------|
| Status label | Read-only: shows the current state and any detail message |
| Start / Stop recording | Equivalent to pressing the shortcut |
| Settings... | Opens the setup window |
| Quit | Stops the daemon |

### CLI commands

All commands are available as `linux-whisper-stt <command>`:

| Command | Description |
|---------|-------------|
| `daemon` | Start the background daemon (tray icon + IPC server). Pass `--dry-run` for a headless test run. |
| `toggle` | Toggle recording on a running daemon |
| `start` | Start recording on a running daemon (no-op if already recording) |
| `stop` | Stop recording on a running daemon (no-op if not recording) |
| `status` | Print the daemon's current state and last error |
| `setup` | Open the graphical setup / settings window |

`toggle`, `start`, `stop`, and `status` communicate with the daemon over a Unix socket at `$XDG_RUNTIME_DIR/linux-whisper-stt.sock`. If the daemon is not running they print a helpful message and exit with code 1.

---

## Configuration

The configuration file lives at `~/.config/linux-whisper-stt/config.toml` (or `$XDG_CONFIG_HOME/linux-whisper-stt/config.toml`). It is created with defaults on first save. The file is written with mode `0600`.

All sections and fields with their defaults:

```toml
[general]
engine = "openai"       # Transcription engine: "openai" or "local"
language = "auto"       # BCP-47 language code (e.g. "en", "it") or "auto" for detection
paste_mode = "auto"     # "auto" = paste via ydotool if available; "clipboard_only" = never auto-paste
sounds = true           # Play start/stop sounds (uses paplay)

[shortcut]
binding = "<Control><Alt>space"  # GNOME keybinding string

[openai]
model = "gpt-4o-mini-transcribe"  # OpenAI model; also valid: "gpt-4o-transcribe", "whisper-1"

[local]
model = "small"                                          # whisper.cpp model name (matches ggml-<model>.bin)
models_dir = "~/.local/share/linux-whisper-stt/models"  # Directory containing GGML model files
binary_path = ""                                         # Path to whisper-cli binary; if empty, searches PATH for "whisper-cli"

[audio]
device = "default"    # ALSA/PulseAudio device name
samplerate = 16000    # Sample rate in Hz
max_seconds = 300     # Maximum recording length in seconds
```

Unknown keys in the TOML file are silently ignored, so it is safe to add comments or extra entries.

---

## Transcription engines

### OpenAI (default)

Sends audio to the OpenAI audio transcriptions endpoint. Requires an API key, stored in the system keyring under the service name `linux-whisper-stt`. Set it with `linux-whisper-stt setup` or directly with `keyring set linux-whisper-stt openai`.

Available models: `gpt-4o-mini-transcribe` (default, cheapest), `gpt-4o-transcribe` (higher accuracy), `whisper-1` (legacy).

When `language` is `auto`, the language parameter is omitted from the API call and the model detects it automatically. Setting a specific language code improves accuracy and speed.

### Local (whisper.cpp)

Runs entirely offline using a locally compiled whisper.cpp binary. `install.sh` builds the binary and downloads the `small` model. The model file must be named `ggml-<model>.bin` and placed in `models_dir`.

The daemon invokes `whisper-cli -m <model_path> -f <wav_path> -l <lang> -nt` and captures stdout as the transcription. If `binary_path` is empty, the binary is looked up on `PATH`.

---

## Auto-paste with ydotool

Auto-paste requires:

1. The `ydotoold` daemon running (installed as a user systemd service by `install.sh`).
2. Your user being a member of the `input` group AND a `udev` rule granting `input` group write access to `/dev/uinput`. Both are set up by `install.sh`, but the group membership only takes effect after you log out and back in.

When auto-paste is active, the daemon calls `ydotool key 29:1 47:1 47:0 29:0` (Left-Ctrl+V press/release). This works on Wayland because ydotool uses the kernel `uinput` interface rather than X11 protocol.

If ydotool is not available or `paste_mode = "clipboard_only"`, the text is placed on the Wayland clipboard (via `wl-copy`) and you paste it manually with `Ctrl+V`.

---

## Troubleshooting

**Tray icon does not appear.**
The tray requires the `AyatanaAppIndicator3` GTK extension. On Ubuntu GNOME this is present by default. On other desktops you may need to install the relevant GNOME Shell extension or system package (`gir1.2-ayatanaappindicator3-0.1`).

**"daemon not running" when pressing the shortcut.**
The daemon is not started yet. Either log out/in so the autostart entry fires, or run `linux-whisper-stt daemon` manually in a terminal.

**Auto-paste does not work.**
Check that: (a) you have logged out and back in since running `install.sh`, (b) `ydotoold` is running (`systemctl --user status ydotoold`), (c) `id` shows `input` in your groups, and (d) `paste_mode` is not `clipboard_only`.

**Shortcut does not register or overwrites another keybinding.**
In v1 the shortcut registration calls `gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['<path>']"` which replaces the entire custom-keybindings list with only the linux-whisper-stt entry. Any existing custom shortcuts will be unregistered. This is a known limitation of the v1 implementation (see `gnome_shortcut.py`). As a workaround, re-add your other shortcuts manually in the GNOME Settings keyboard panel after running setup.

**OpenAI error: API key missing.**
Run `linux-whisper-stt setup` and enter your API key, or run `keyring set linux-whisper-stt openai` from the terminal with the venv active.

---

## License

MIT — see [LICENSE](LICENSE).
