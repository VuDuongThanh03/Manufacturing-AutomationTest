"""Sinh file log giả lập kết quả kiểm tra thiết bị trên dây chuyền.

Mỗi thiết bị (DUT) có một file .log, gồm các bước test và kết quả cuối.

Cách chạy:
    python generate_logs.py --count 500 --out logs
"""
import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

STATIONS = ["FT1", "FT2", "FT3"]
STEPS = ["FW_VERSION", "MEMORY_TEST", "WIFI_TEST", "USB_TEST", "CHECKSUM"]
# Mã lỗi có thể gặp ở từng bước test
ERROR_CODES = {
    "FW_VERSION": ["ERR_FW_MISMATCH"],
    "MEMORY_TEST": ["ERR_MEM_FAIL"],
    "WIFI_TEST": ["ERR_TIMEOUT", "ERR_LOW_SIGNAL"],
    "USB_TEST": ["ERR_TIMEOUT", "ERR_NO_DEVICE"],
    "CHECKSUM": ["CHECKSUM_FAIL"],
}


def make_log(serial: str, start: datetime, fail_rate: float, rng: random.Random) -> str:
    """Tạo nội dung log cho một thiết bị."""
    station = rng.choice(STATIONS)
    t = start
    lines = [f"{t:%Y-%m-%d %H:%M:%S} [INFO] SN={serial} STATION={station} START"]
    final = "PASS"
    for step in STEPS:
        t += timedelta(seconds=rng.randint(1, 4))
        if rng.random() < fail_rate:
            code = rng.choice(ERROR_CODES[step])
            lines.append(f"{t:%Y-%m-%d %H:%M:%S} [ERROR] STEP={step} RESULT=FAIL CODE={code}")
            final = "FAIL"
            break  # gặp lỗi thì dừng test thiết bị này
        lines.append(f"{t:%Y-%m-%d %H:%M:%S} [INFO] STEP={step} RESULT=PASS")
    t += timedelta(seconds=1)
    lines.append(f"{t:%Y-%m-%d %H:%M:%S} [INFO] SN={serial} FINAL={final}")
    return "\n".join(lines) + "\n"


def generate(count: int, out_dir: Path, fail_rate: float = 0.04, seed: int = 42) -> None:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 11, 10, 8, 0, 0)
    for i in range(1, count + 1):
        serial = f"DUT{i:06d}"
        start += timedelta(seconds=rng.randint(20, 40))
        (out_dir / f"{serial}.log").write_text(
            make_log(serial, start, fail_rate, rng), encoding="utf-8"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sinh log kiểm tra giả lập")
    parser.add_argument("--count", type=int, default=500, help="số thiết bị")
    parser.add_argument("--out", default="logs", help="thư mục chứa log")
    parser.add_argument("--fail-rate", type=float, default=0.04, help="xác suất lỗi mỗi bước")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate(args.count, Path(args.out), args.fail_rate, args.seed)
    print(f"Đã tạo {args.count} file log trong thư mục '{args.out}'")
