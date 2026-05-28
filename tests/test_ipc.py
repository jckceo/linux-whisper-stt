import threading
import time

from linux_whisper_stt.ipc import IPCServer, send_command


def test_roundtrip(tmp_path):
    sock = tmp_path / "test.sock"

    def handler(cmd: str) -> dict:
        return {"echo": cmd, "state": "idle"}

    server = IPCServer(handler, socket_path=sock)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    # wait for the socket file to appear
    for _ in range(50):
        if sock.exists():
            break
        time.sleep(0.02)

    resp = send_command("toggle", socket_path=sock)
    assert resp == {"echo": "toggle", "state": "idle"}

    server.stop()


def test_send_command_without_server_raises(tmp_path):
    import pytest

    with pytest.raises(ConnectionError):
        send_command("toggle", socket_path=tmp_path / "absent.sock")
