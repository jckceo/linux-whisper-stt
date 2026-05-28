from __future__ import annotations

import argparse
import sys

from .ipc import send_command

REMOTE_COMMANDS = {"toggle", "start", "stop", "status"}


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linux-whisper-stt")
    sub = parser.add_subparsers(dest="command")
    for name in ("toggle", "start", "stop", "status", "setup"):
        sub.add_parser(name)
    daemon_p = sub.add_parser("daemon")
    daemon_p.add_argument("--dry-run", action="store_true")

    try:
        args, _ = parser.parse_known_args(argv)
    except SystemExit:
        # argparse raises SystemExit(2) for an unknown subcommand or --help
        return 2
    command = args.command

    if command in REMOTE_COMMANDS:
        return _run_remote(command)
    if command == "daemon":
        from .daemon import run_daemon

        return run_daemon(dry_run=getattr(args, "dry_run", False))
    if command == "setup":
        from .ui.setup_window import run_setup

        return run_setup()

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
