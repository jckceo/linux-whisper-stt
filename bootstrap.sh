#!/usr/bin/env bash
# One-line bootstrap installer for linux-whisper-stt.
#
#   curl -fsSL https://raw.githubusercontent.com/jckceo/linux-whisper-stt/main/bootstrap.sh | bash
#
# Clones (or updates) the repo into ~/linux-whisper-stt, asks whether to enable
# the optional features, then hands off to the repo's install.sh.
set -euo pipefail

REPO_URL="https://github.com/jckceo/linux-whisper-stt"
TARGET="${LWSTT_DIR:-$HOME/linux-whisper-stt}"

# 1. Ensure git is available (needed before we can clone).
if ! command -v git >/dev/null 2>&1; then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "Error: git is required but apt-get is not available." >&2
    echo "Install git manually, then re-run." >&2
    exit 1
  fi
  echo "==> Installing git (sudo)"
  sudo apt-get update
  sudo apt-get install -y git
fi

# 2. Acquire the source.
if [ -d "$TARGET/.git" ]; then
  echo "==> Updating existing checkout at $TARGET"
  git -C "$TARGET" pull --ff-only
elif [ -e "$TARGET" ]; then
  echo "Error: $TARGET exists but is not a git checkout of linux-whisper-stt." >&2
  echo "Move or remove it, or set LWSTT_DIR to another path, then re-run." >&2
  exit 1
else
  echo "==> Cloning $REPO_URL into $TARGET"
  git clone "$REPO_URL" "$TARGET"
fi

# 3. Choose optional features (default No). Read from the terminal even when this
#    script itself arrived over a pipe (curl | bash). No terminal -> base install.
WITH_AUTOPASTE=0
WITH_LOCAL_WHISPER=0

ask() {
  # ask "Prompt [y/N] " -> returns 0 for yes, non-zero otherwise.
  local prompt="$1" reply=""
  printf '%s' "$prompt" > /dev/tty 2>/dev/null || return 1
  read -r reply < /dev/tty || reply=""
  case "$reply" in
    [yY] | [yY][eE][sS]) return 0 ;;
    *) return 1 ;;
  esac
}

if [ -r /dev/tty ]; then
  if ask "Enable Wayland auto-paste via ydotool? (requires a logout/login) [y/N] "; then
    WITH_AUTOPASTE=1
  fi
  if ask "Enable offline transcription? Builds whisper.cpp and downloads a model (several minutes). [y/N] "; then
    WITH_LOCAL_WHISPER=1
  fi
else
  echo "==> No terminal detected; installing the base setup only."
  echo "    Re-run with --with-autopaste / --with-local-whisper to enable extras."
fi

# 4. Hand off to the repo's installer with the chosen flags.
FLAGS=()
if [ "$WITH_AUTOPASTE" = "1" ]; then FLAGS+=(--with-autopaste); fi
if [ "$WITH_LOCAL_WHISPER" = "1" ]; then FLAGS+=(--with-local-whisper); fi

if [ ! -f "$TARGET/install.sh" ]; then
  echo "Error: install.sh not found in $TARGET; the checkout looks incomplete." >&2
  exit 1
fi

echo "==> Running install.sh ${FLAGS[*]:-(base)}"
exec bash "$TARGET/install.sh" "${FLAGS[@]}"
