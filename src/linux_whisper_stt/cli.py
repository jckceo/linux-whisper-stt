from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from .ipc import send_command

REMOTE_COMMANDS = {"toggle", "start", "stop", "status"}


def entrypoint() -> str:
    """Absolute path to the installed `linux-whisper-stt` console script.

    GNOME custom keybindings and the autostart .desktop file run without the
    venv's bin/ directory on PATH, so they must invoke this script by its
    absolute path. Falls back to the bare name if it can't be located.
    """
    candidate = Path(sys.executable).with_name("linux-whisper-stt")
    return str(candidate) if candidate.exists() else "linux-whisper-stt"


def _run_remote(command: str) -> int:
    try:
        resp = send_command(command)
    except ConnectionError as e:
        print(f"daemon not running ({e}). Start it with: linux-whisper-stt daemon")
        return 1
    if "error" in resp:
        print(f"error: {resp['error']}")
        return 1
    print(f"state: {resp.get('state', '?')}")
    if resp.get("last_error"):
        print(f"last error: {resp['last_error']}")
    return 0


def start_daemon_background(popen_fn=subprocess.Popen):
    return popen_fn(
        [entrypoint(), "daemon"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _run_transcribe_file(path: str) -> int:
    media_path = Path(path).expanduser()
    if not media_path.exists():
        print(f"error: file does not exist: {media_path}")
        return 1

    payload = {"command": "transcribe-file", "path": str(media_path)}
    try:
        resp = send_command(payload)
    except ConnectionError:
        start_daemon_background()
        time.sleep(1.0)
        try:
            resp = send_command(payload, connect_retries=50, retry_delay=0.1)
        except ConnectionError as e:
            print(
                f"daemon not running ({e}). Start it with: linux-whisper-stt daemon"
            )
            return 1

    if resp.get("accepted"):
        print("accepted")
        return 0
    print(f"error: {resp.get('error', 'request rejected')}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linux-whisper-stt")
    sub = parser.add_subparsers(dest="command")
    for name in (
        "toggle",
        "start",
        "stop",
        "status",
        "setup",
        "install-service",
        "uninstall-service",
    ):
        sub.add_parser(name)
    daemon_p = sub.add_parser("daemon")
    daemon_p.add_argument("--dry-run", action="store_true")
    transcribe_file_p = sub.add_parser("transcribe-file")
    transcribe_file_p.add_argument("path")

    try:
        args, _ = parser.parse_known_args(argv)
    except SystemExit:
        # argparse raises SystemExit(2) for an unknown subcommand or --help
        return 2
    command = args.command

    if command in REMOTE_COMMANDS:
        return _run_remote(command)
    if command == "transcribe-file":
        return _run_transcribe_file(args.path)
    if command == "daemon":
        from .daemon import run_daemon

        return run_daemon(dry_run=getattr(args, "dry_run", False))
    if command == "setup":
        from .ui.setup_window import run_setup

        return run_setup()
    if command == "install-service":
        from .systemd import install_service

        try:
            path = install_service()
        except (OSError, subprocess.CalledProcessError) as e:
            print(f"error: {e}")
            return 1
        print(f"installed service: {path}")
        return 0
    if command == "uninstall-service":
        from .systemd import uninstall_service

        try:
            path = uninstall_service()
        except (OSError, subprocess.CalledProcessError) as e:
            print(f"error: {e}")
            return 1
        print(f"removed service: {path}")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
