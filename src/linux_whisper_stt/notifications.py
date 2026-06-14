from __future__ import annotations

import subprocess


def build_notify_command(title: str, body: str, app_name: str = "linux-whisper-stt") -> list[str]:
    return ["notify-send", "-a", app_name, title, body]


def send_notification(title: str, body: str, runner=subprocess.run) -> bool:
    """Show a desktop notification via notify-send. Best-effort: never raises.

    Returns True only when notify-send ran and exited 0 (delivered to the notification
    server); False on any error or non-zero exit.
    """
    try:
        result = runner(
            build_notify_command(title, body), capture_output=True, text=True, timeout=5
        )
        return getattr(result, "returncode", 0) == 0
    except Exception:
        return False
