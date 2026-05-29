from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from .autostart import uninstall_autostart
from .cli import entrypoint

SERVICE_NAME = "linux-whisper-stt.service"


def service_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "systemd/user" / SERVICE_NAME


def service_installed() -> bool:
    return service_path().exists()


def _systemd_quote_arg(arg: str) -> str:
    escaped = arg.replace("%", "%%")
    if not any(ch.isspace() or ch in {'"', "\\"} for ch in escaped):
        return escaped
    escaped = escaped.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def default_exec_start(entrypoint_fn: Callable[[], str] = entrypoint) -> str:
    return " ".join((_systemd_quote_arg(entrypoint_fn()), _systemd_quote_arg("daemon")))


def service_content(command: str | None = None) -> str:
    command = command or default_exec_start()
    return f"""[Unit]
Description=linux-whisper-stt daemon
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Type=simple
ExecStart={command}
Restart=on-failure
RestartSec=2

[Install]
WantedBy=graphical-session.target
"""


def install_service(
    command: str | None = None,
    runner=subprocess.run,
    disable_autostart=uninstall_autostart,
) -> Path:
    path = service_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(service_content(command=command))
    try:
        runner(["systemctl", "--user", "daemon-reload"], check=True)
        runner(
            ["systemctl", "--user", "enable", "--now", SERVICE_NAME],
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        path.unlink(missing_ok=True)
        raise
    disable_autostart()
    return path


def uninstall_service(runner=subprocess.run) -> Path:
    path = service_path()
    runner(
        ["systemctl", "--user", "disable", "--now", SERVICE_NAME],
        check=False,
    )
    path.unlink(missing_ok=True)
    runner(["systemctl", "--user", "daemon-reload"], check=True)
    return path
