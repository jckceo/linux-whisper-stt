from __future__ import annotations

import json
import os
import socket
import tempfile
from pathlib import Path
from typing import Callable


def runtime_socket_path() -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(base) / "linux-whisper-stt.sock"


class IPCServer:
    """Listens on a Unix socket. Each connection sends one command line;
    the handler returns a dict that is sent back as one JSON line."""

    def __init__(self, handler: Callable[[str], dict], socket_path: Path | None = None):
        self.handler = handler
        self.socket_path = Path(socket_path or runtime_socket_path())
        self._sock: socket.socket | None = None
        self._running = False

    def serve_forever(self) -> None:
        if self.socket_path.exists():
            self.socket_path.unlink()
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(self.socket_path))
        self._sock.listen(8)
        self._sock.settimeout(0.5)
        self._running = True
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
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


def send_command(command: str, socket_path: Path | None = None) -> dict:
    path = Path(socket_path or runtime_socket_path())
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(str(path))
    except (FileNotFoundError, ConnectionRefusedError) as e:
        raise ConnectionError(f"daemon not running at {path}") from e
    try:
        sock.sendall((command + "\n").encode("utf-8"))
        data = sock.recv(65536).decode("utf-8").strip()
    finally:
        sock.close()
    return json.loads(data) if data else {}
