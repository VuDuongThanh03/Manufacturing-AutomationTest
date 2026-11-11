"""Phía máy tính: gửi lệnh test tới thiết bị, kiểm tra phản hồi, ghi log.

Dùng trực tiếp từ dòng lệnh:
    python host.py --port socket://localhost:5000 AT AT+CHECK_FW AT+TEST=START
"""
import argparse
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import serial

EOL = b"\r\n"
RE_DATA_LINE = re.compile(r"^[A-Z_]+:.+$")  # dòng dữ liệu hợp lệ: KEY:value

# Các trạng thái của một lần gửi lệnh
OK = "OK"
ERROR = "ERROR"                # thiết bị từ chối lệnh
TIMEOUT = "TIMEOUT"            # hết thời gian chờ mà chưa có OK/ERROR
BAD_RESPONSE = "BAD_RESPONSE"  # phản hồi sai cấu trúc


@dataclass
class CommandResult:
    command: str
    status: str
    lines: list[str]
    elapsed_ms: float


class SerialClient:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0,
                 log_file: str | Path | None = None):
        # serial_for_url nhận cả tên cổng "COM5" lẫn URL "socket://localhost:5000"
        self.ser = serial.serial_for_url(port, baudrate=baudrate, timeout=0.05)
        self.timeout = timeout
        self.log_file = Path(log_file) if log_file else None
        self.on_log = None  # hàm callback để giao diện hiển thị log

    def close(self) -> None:
        self.ser.close()

    def _log(self, direction: str, text: str) -> None:
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S.%f}"[:-3] + f" {direction} {text}"
        if self.log_file:
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        if self.on_log:
            self.on_log(line)

    def send_command(self, command: str) -> CommandResult:
        """Gửi một lệnh và chờ tới khi nhận OK/ERROR hoặc hết timeout."""
        self.ser.reset_input_buffer()
        self.ser.write(command.encode("ascii") + EOL)
        self._log("TX", command)

        start = time.perf_counter()
        buffer, lines, status = b"", [], TIMEOUT
        while time.perf_counter() - start < self.timeout and status == TIMEOUT:
            buffer += self.ser.read(256)
            while EOL in buffer:
                raw, buffer = buffer.split(EOL, 1)
                line = raw.decode("ascii", errors="replace")
                self._log("RX", line)
                lines.append(line)
                if line in (OK, ERROR):
                    status = line
                    break
                if not RE_DATA_LINE.match(line):
                    status = BAD_RESPONSE
                    break
        elapsed = (time.perf_counter() - start) * 1000
        if status != OK:
            self._log("!!", f"{status} cho lệnh {command} sau {elapsed:.0f} ms")
        return CommandResult(command, status, lines, elapsed)

    def run_script(self, commands: list[str]) -> list[CommandResult]:
        """Chạy lần lượt một kịch bản gồm nhiều lệnh."""
        return [self.send_command(c) for c in commands if c.strip()]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gửi lệnh AT tới thiết bị")
    parser.add_argument("--port", required=True, help="COM5 hoặc socket://localhost:5000")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--log", default="session.log")
    parser.add_argument("commands", nargs="+")
    args = parser.parse_args()

    client = SerialClient(args.port, args.baudrate, args.timeout, args.log)
    try:
        for result in client.run_script(args.commands):
            print(f"{result.command:16} {result.status:13} {result.lines} "
                  f"({result.elapsed_ms:.0f} ms)")
    finally:
        client.close()
