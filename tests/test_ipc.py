import threading
import time

from linux_whisper_stt.ipc import IPCServer, encode_message, parse_message, send_command


def test_parse_legacy_string_command():
    assert parse_message("toggle") == {"command": "toggle"}


def test_encode_and_parse_structured_command_with_spaces():
    payload = {"command": "transcribe-file", "path": "/tmp/my file.mp4"}
    assert parse_message(encode_message(payload)) == payload


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
