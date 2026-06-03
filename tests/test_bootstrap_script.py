from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bootstrap.sh"


def script_text() -> str:
    return SCRIPT.read_text()


def test_bootstrap_has_strict_mode():
    assert "set -euo pipefail" in script_text()


def test_bootstrap_targets_home_dir_with_override():
    assert 'TARGET="${LWSTT_DIR:-$HOME/linux-whisper-stt}"' in script_text()


def test_bootstrap_reads_prompts_from_tty_with_safe_default():
    text = script_text()
    assert "/dev/tty" in text
    assert "WITH_AUTOPASTE=0" in text
    assert "WITH_LOCAL_WHISPER=0" in text


def test_bootstrap_updates_existing_checkout_or_clones():
    text = script_text()
    assert 'git -C "$TARGET" pull --ff-only' in text
    assert 'git clone "$REPO_URL" "$TARGET"' in text


def test_bootstrap_does_not_clobber_a_non_git_target():
    text = script_text()
    assert 'elif [ -e "$TARGET" ]; then' in text
    assert "exit 1" in text


def test_bootstrap_hands_off_to_install_script_with_flags():
    text = script_text()
    assert 'exec bash "$TARGET/install.sh"' in text
    assert "--with-autopaste" in text
    assert "--with-local-whisper" in text
