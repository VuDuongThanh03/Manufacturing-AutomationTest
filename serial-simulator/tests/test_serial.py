import socket
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from device_sim import DeviceSimulator, serve
from host import BAD_RESPONSE, ERROR, OK, TIMEOUT, SerialClient


def test_device_answers_known_commands():
    dev = DeviceSimulator(serial_number="DUT42", fw_version="9.9.9")
    assert dev.handle("AT") == ["OK"]
    assert dev.handle("at+sn?") == ["SN:DUT42", "OK"]
    assert dev.handle("AT+CHECK_FW") == ["FW:9.9.9", "OK"]
    assert dev.handle("AT+UNKNOWN") == ["ERROR"]


def test_device_remembers_test_state():
    dev = DeviceSimulator()
    assert dev.handle("AT+TEST?") == ["TEST:IDLE", "OK"]
    dev.handle("AT+TEST=START")
    assert dev.handle("AT+TEST?") == ["TEST:RUNNING", "OK"]


class FakeDevice(DeviceSimulator):
    """Thiết bị trả lời theo kịch bản cố định để test các trường hợp lỗi."""

    def handle(self, command):
        if command == "SILENT":
            return None
        if command == "GARBAGE":
            return ["#@!garbage"]
        return super().handle(command)


@pytest.fixture
def client(tmp_path):
    """Dựng thiết bị giả lập trên TCP và một client kết nối vào nó."""
    server = socket.create_server(("127.0.0.1", 0))
    port = server.getsockname()[1]

    def run():
        conn, _ = server.accept()
        with conn:
            def read():
                try:
                    return conn.recv(1024) or None
                except OSError:
                    return None
            serve(read, conn.sendall, FakeDevice())

    threading.Thread(target=run, daemon=True).start()
    c = SerialClient(f"socket://127.0.0.1:{port}", timeout=0.4,
                     log_file=tmp_path / "session.log")
    yield c
    c.close()
    server.close()


def test_command_ok_with_data(client):
    result = client.send_command("AT+CHECK_FW")
    assert result.status == OK
    assert result.lines == ["FW:1.2.3", "OK"]


def test_unknown_command_returns_error(client):
    assert client.send_command("AT+NOPE").status == ERROR


def test_silent_device_gives_timeout(client):
    result = client.send_command("SILENT")
    assert result.status == TIMEOUT
    assert result.elapsed_ms >= 400


def test_malformed_response_is_detected(client):
    assert client.send_command("GARBAGE").status == BAD_RESPONSE


def test_session_is_logged(client):
    client.run_script(["AT", "AT+SN?"])
    log = client.log_file.read_text(encoding="utf-8")
    assert "TX AT+SN?" in log
    assert "RX SN:DUT000001" in log
