"""Thiết bị giả lập: nhận lệnh AT và trả lời như một bo mạch thật.

Chạy không cần phần cứng (qua TCP):
    python device_sim.py --tcp 5000
Chạy trên cổng COM ảo (ví dụ cặp COM5 <-> COM6 tạo bằng com0com):
    python device_sim.py --port COM6

Giao thức: mỗi lệnh là một dòng kết thúc bằng \\r\\n. Thiết bị trả về
0 hoặc nhiều dòng dữ liệu dạng "KEY:value", rồi một dòng "OK" hoặc "ERROR".
"""
import argparse
import random
import socket

import serial

EOL = b"\r\n"


class DeviceSimulator:
    """Phần xử lý lệnh, tách khỏi phần truyền nhận để dễ viết unit test."""

    def __init__(self, serial_number: str = "DUT000001", fw_version: str = "1.2.3",
                 fault_rate: float = 0.0, seed: int | None = None):
        self.serial_number = serial_number
        self.fw_version = fw_version
        self.fault_rate = fault_rate  # xác suất thiết bị phản hồi lỗi (để test timeout)
        self.testing = False
        self._rng = random.Random(seed)

    def handle(self, command: str) -> list[str] | None:
        """Trả về danh sách dòng phản hồi; None nghĩa là im lặng (gây timeout)."""
        command = command.strip().upper()
        if self.fault_rate and self._rng.random() < self.fault_rate:
            # Giả lập 2 kiểu lỗi: không trả lời, hoặc trả lời sai cấu trúc
            return None if self._rng.random() < 0.5 else ["#@!garbage"]
        if command == "AT":
            return ["OK"]
        if command == "AT+SN?":
            return [f"SN:{self.serial_number}", "OK"]
        if command == "AT+CHECK_FW":
            return [f"FW:{self.fw_version}", "OK"]
        if command == "AT+TEST=START":
            self.testing = True
            return ["TEST:RUNNING", "OK"]
        if command == "AT+TEST=STOP":
            self.testing = False
            return ["TEST:STOPPED", "OK"]
        if command == "AT+TEST?":
            return [f"TEST:{'RUNNING' if self.testing else 'IDLE'}", "OK"]
        return ["ERROR"]


def serve(read, write, device: DeviceSimulator) -> None:
    """Vòng lặp đọc lệnh - trả lời, dùng chung cho cổng COM và TCP."""
    buffer = b""
    while True:
        chunk = read()
        if chunk is None:  # kết nối đã đóng
            return
        buffer += chunk
        while EOL in buffer:
            line, buffer = buffer.split(EOL, 1)
            command = line.decode("ascii", errors="replace")
            response = device.handle(command)
            print(f"RX {command!r} -> TX {response}")
            if response is not None:
                write(EOL.join(r.encode("ascii") for r in response) + EOL)


def serve_tcp(port: int, device: DeviceSimulator) -> None:
    with socket.create_server(("127.0.0.1", port)) as server:
        print(f"Thiết bị giả lập đang chờ tại socket://localhost:{port}")
        while True:
            conn, _ = server.accept()
            with conn:
                def read():
                    try:
                        return conn.recv(1024) or None
                    except ConnectionError:
                        return None
                serve(read, conn.sendall, device)


def serve_serial(port: str, baudrate: int, device: DeviceSimulator) -> None:
    with serial.Serial(port, baudrate, timeout=0.2) as ser:
        print(f"Thiết bị giả lập đang chạy trên {port} @ {baudrate}")
        serve(lambda: ser.read(ser.in_waiting or 1), ser.write, device)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thiết bị giả lập nhận lệnh AT")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tcp", type=int, help="chạy qua TCP ở cổng này")
    group.add_argument("--port", help="cổng COM, ví dụ COM6")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--fault-rate", type=float, default=0.0,
                        help="xác suất phản hồi lỗi/im lặng, ví dụ 0.2")
    args = parser.parse_args()
    dev = DeviceSimulator(fault_rate=args.fault_rate)
    try:
        if args.tcp:
            serve_tcp(args.tcp, dev)
        else:
            serve_serial(args.port, args.baudrate, dev)
    except KeyboardInterrupt:
        print("Đã dừng.")
