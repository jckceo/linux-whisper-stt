from __future__ import annotations

import errno
import json
import os
import socket
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def runtime_socket_path() -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(base) / "linux-whisper-stt.sock"


def encode_message(payload: str | dict[str, Any]) -> str:
    if isinstance(payload, str):
        return payload
    return json.dumps(payload)


def parse_message(data: str) -> dict[str, Any]:
    stripped = data.strip()
    if stripped.startswith("{"):
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict) or "command" not in parsed:
            raise ValueError("invalid IPC payload")
        return parsed
    return {"command": stripped}


def _prepare_socket_path(socket_path: Path) -> None:
    if not socket_path.exists():
        return

    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        probe.settimeout(0.1)
        probe.connect(str(socket_path))
    except FileNotFoundError:
        return
    except ConnectionRefusedError:
        socket_path.unlink(missing_ok=True)
    except OSError as e:
        if e.errno in (errno.ENOENT, errno.ECONNREFUSED, errno.ENOTSOCK, errno.EINVAL):
            socket_path.unlink(missing_ok=True)
            return
        raise RuntimeError(f"cannot inspect IPC socket at {socket_path}: {e}") from e
    else:
        raise RuntimeError(f"daemon already running at {socket_path}")
    finally:
        probe.close()


class IPCServer:
    """Listens on a Unix socket. Each connection sends one command line;
    the handler returns a dict that is sent back as one JSON line."""

    def __init__(self, handler: Callable[[str], dict], socket_path: Path | None = None):
        self.handler = handler
        self.socket_path = Path(socket_path or runtime_socket_path())
        self._sock: socket.socket | None = None
        self._running = False

    def serve_forever(self) -> None:
        _prepare_socket_path(self.socket_path)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(self.socket_path))
        self._sock.listen(8)
        self._sock.settimeout(0.5)
        self._running = True
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            with conn:
                data = conn.recv(65536).decode("utf-8").strip()
                try:
                    response = self.handler(data)
                except Exception as e:  # never crash the server loop
                    response = {"error": str(e)}
                conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
        if self._sock:
            self._sock.close()
        if self.socket_path.exists():
            self.socket_path.unlink()

    def stop(self) -> None:
        self._running = False


def send_command(
    command: str | dict[str, Any],
    socket_path: Path | None = None,
    connect_retries: int = 10,
    retry_delay: float = 0.02,
) -> dict:
    path = Path(socket_path or runtime_socket_path())
    last_err: Exception | None = None
    for attempt in range(connect_retries):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(str(path))
        except OSError as e:
            # Daemon startup can race socket creation; retry when requested.
            last_err = e
            sock.close()
            if attempt < connect_retries - 1:
                time.sleep(retry_delay)
                continue
            break
        try:
            try:
                sock.sendall((encode_message(command) + "\n").encode("utf-8"))
                data = sock.recv(65536).decode("utf-8").strip()
            except OSError as e:
                raise ConnectionError(
                    f"IPC communication failed with daemon at {path}: {e}"
                ) from e
            try:
                return json.loads(data) if data else {}
            except json.JSONDecodeError as e:
                raise ConnectionError(
                    f"invalid response from daemon at {path}: {e}"
                ) from e
        finally:
            sock.close()
    raise ConnectionError(f"daemon not running at {path}") from last_err
