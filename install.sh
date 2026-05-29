#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$HOME/.local/share/linux-whisper-stt/models"
WHISPER_DIR="$REPO_DIR/.whisper.cpp"
WITH_AUTOPASTE=0
WITH_LOCAL_WHISPER=0
BASE_PACKAGES=(
  python3.12 python3.12-venv
  wl-clipboard ffmpeg pipewire-bin
  gir1.2-ayatanaappindicator3-0.1 gir1.2-gtk-4.0 gir1.2-adw-1
)
LOCAL_WHISPER_PACKAGES=(build-essential cmake git)

usage() {
  cat <<'EOF'
Usage: ./install.sh [OPTIONS]

Options:
  --with-autopaste       Enable Wayland auto-paste integration
  --with-local-whisper   Enable offline transcription
  --help                 Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --with-autopaste)
      WITH_AUTOPASTE=1
      ;;
    --with-local-whisper)
      WITH_LOCAL_WHISPER=1
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

echo "==> System packages (sudo)"
sudo apt-get update
sudo apt-get install -y "${BASE_PACKAGES[@]}"

echo "==> Python venv (system-site-packages for PyGObject)"
/usr/bin/python3.12 -m venv --system-site-packages "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install -e "$REPO_DIR"

if [ "$WITH_AUTOPASTE" = "1" ]; then
  echo "==> Auto-paste packages and uinput access"
  sudo apt-get install -y ydotool ydotoold
  sudo groupadd -f input
  sudo usermod -aG input "$USER"
  echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' \
    | sudo tee /etc/udev/rules.d/80-uinput.rules >/dev/null
  sudo udevadm control --reload-rules && sudo udevadm trigger || true

  echo "==> ydotoold user service"
  YDOTOOLD_BIN="$(command -v ydotoold || true)"
  if [ -n "$YDOTOOLD_BIN" ]; then
    mkdir -p "$HOME/.config/systemd/user"
    cat > "$HOME/.config/systemd/user/ydotoold.service" <<EOF
[Unit]
Description=ydotool daemon
[Service]
ExecStart=$YDOTOOLD_BIN
Restart=always
[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable --now ydotoold.service || true
  else
    echo "   ydotoold not found; auto-paste will fall back to clipboard until it is installed."
  fi
else
  echo "==> Skipping Wayland auto-paste integration (pass --with-autopaste to enable)"
fi

if [ "$WITH_LOCAL_WHISPER" = "1" ]; then
  echo "==> Local whisper build packages"
  sudo apt-get install -y "${LOCAL_WHISPER_PACKAGES[@]}"

  echo "==> whisper.cpp (local engine)"
  if [ ! -d "$WHISPER_DIR" ]; then
    git clone https://github.com/ggml-org/whisper.cpp "$WHISPER_DIR"
  fi
  cmake -S "$WHISPER_DIR" -B "$WHISPER_DIR/build"
  cmake --build "$WHISPER_DIR/build" -j --config Release
  mkdir -p "$MODELS_DIR"
  bash "$WHISPER_DIR/models/download-ggml-model.sh" small
  cp "$WHISPER_DIR/models/ggml-small.bin" "$MODELS_DIR/"
  WHISPER_BIN="$(find "$WHISPER_DIR/build" -name whisper-cli -type f 2>/dev/null | head -1)"
  [ -z "$WHISPER_BIN" ] && WHISPER_BIN="$(find "$WHISPER_DIR" -name main -type f 2>/dev/null | head -1)"

  echo "==> Default config (point local engine at the built binary)"
  "$REPO_DIR/.venv/bin/python" - "$WHISPER_BIN" <<'PYEOF'
import sys
from linux_whisper_stt.config import load_config, save_config
c = load_config()
if len(sys.argv) > 1 and sys.argv[1]:
    c.local.binary_path = sys.argv[1]
save_config(c)
PYEOF
else
  echo "==> Skipping offline transcription setup (pass --with-local-whisper to enable)"
fi

echo "==> Autostart entry"
"$REPO_DIR/.venv/bin/python" -c "from linux_whisper_stt.autostart import install_autostart; print('autostart:', install_autostart())"

echo
echo "Done. Next:"
if [ "$WITH_AUTOPASTE" = "1" ]; then
  echo "  1) Log out/in once so the input group change applies."
else
  echo "  1) Optional: rerun with --with-autopaste to enable Wayland auto-paste integration."
fi
echo "  2) Run:  $REPO_DIR/.venv/bin/linux-whisper-stt setup   (enter API key, set shortcut)"
echo "  3) The tray icon appears at next login (autostart) or run: linux-whisper-stt daemon"
