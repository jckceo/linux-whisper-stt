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


def test_send_command_retries_missing_socket(monkeypatch, tmp_path):
    import pytest

    attempts = []

    class FakeSocket:
        def connect(self, path):
            attempts.append(path)
            raise FileNotFoundError(path)

        def close(self):
            pass

    monkeypatch.setattr(
        "linux_whisper_stt.ipc.socket.socket", lambda *_args, **_kwargs: FakeSocket()
    )
    monkeypatch.setattr("linux_whisper_stt.ipc.time.sleep", lambda _seconds: None)

    with pytest.raises(ConnectionError):
        send_command(
            "toggle",
            socket_path=tmp_path / "absent.sock",
            connect_retries=2,
            retry_delay=0,
        )

    assert len(attempts) == 2


def test_send_command_retries_permission_error(monkeypatch, tmp_path):
    import pytest

    attempts = []

    class FakeSocket:
        def connect(self, path):
            attempts.append(path)
            raise PermissionError(path)

        def close(self):
            pass

    monkeypatch.setattr(
        "linux_whisper_stt.ipc.socket.socket", lambda *_args, **_kwargs: FakeSocket()
    )
    monkeypatch.setattr("linux_whisper_stt.ipc.time.sleep", lambda _seconds: None)

    with pytest.raises(ConnectionError):
        send_command(
            "toggle",
            socket_path=tmp_path / "protected.sock",
            connect_retries=2,
            retry_delay=0,
        )

    assert len(attempts) == 2


def test_send_command_invalid_json_response_raises_connection_error(
    monkeypatch, tmp_path
):
    import pytest

    class FakeSocket:
        def connect(self, path):
            pass

        def sendall(self, data):
            pass

        def recv(self, size):
            return b"not json\n"

        def close(self):
            pass

    monkeypatch.setattr(
        "linux_whisper_stt.ipc.socket.socket", lambda *_args, **_kwargs: FakeSocket()
    )

    with pytest.raises(ConnectionError) as exc:
        send_command("toggle", socket_path=tmp_path / "daemon.sock")

    assert "invalid response" in str(exc.value)


def test_ipc_server_refuses_to_unlink_live_socket(monkeypatch, tmp_path):
    sock_path = tmp_path / "live.sock"
    sock_path.write_text("socket")

    class ProbeSocket:
        def settimeout(self, timeout):
            pass

        def connect(self, path):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        "linux_whisper_stt.ipc.socket.socket",
        lambda *_args, **_kwargs: ProbeSocket(),
    )

    import pytest

    with pytest.raises(RuntimeError, match="daemon already running"):
        IPCServer(lambda _command: {}, socket_path=sock_path).serve_forever()

    assert sock_path.exists()


def test_ipc_server_unlinks_stale_socket_before_binding(monkeypatch, tmp_path):
    sock_path = tmp_path / "stale.sock"
    sock_path.write_text("socket")

    class ProbeSocket:
        def settimeout(self, timeout):
            pass

        def connect(self, path):
            raise ConnectionRefusedError(path)

        def close(self):
            pass

    class ServerSocket:
        def bind(self, path):
            assert not sock_path.exists()

        def listen(self, backlog):
            pass

        def settimeout(self, timeout):
            pass

        def accept(self):
            raise OSError("stop")

        def close(self):
            pass

    sockets = [ProbeSocket(), ServerSocket()]
    monkeypatch.setattr(
        "linux_whisper_stt.ipc.socket.socket", lambda *_args, **_kwargs: sockets.pop(0)
    )

    IPCServer(lambda _command: {}, socket_path=sock_path).serve_forever()
