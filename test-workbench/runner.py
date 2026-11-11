"""Phần lõi: đọc danh sách Test Case từ file JSON, chạy và xuất kết quả.

Mỗi test case chạy một lệnh, rồi kiểm tra mã thoát và (tuỳ chọn) nội dung in ra.
Phần này không phụ thuộc giao diện nên chạy được từ dòng lệnh và unit test:
    python runner.py sample_tests.json --csv result.csv
"""
import argparse
import csv
import json
import re
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

PASS, FAIL = "PASS", "FAIL"


@dataclass
class TestCase:
    __test__ = False  # để pytest không nhầm đây là lớp chứa test
    id: str
    name: str
    command: str            # "{python}" sẽ được thay bằng đường dẫn Python đang chạy
    expect_exit_code: int = 0
    expect_regex: str = ""  # nếu có, output phải khớp biểu thức này
    timeout: float = 5.0


@dataclass
class TestResult:
    __test__ = False
    id: str
    name: str
    status: str
    duration_s: float
    message: str


def load_test_cases(path: str | Path) -> list[TestCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = [TestCase(**item) for item in data]
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("ID của test case bị trùng")
    return cases


def run_test_case(case: TestCase) -> TestResult:
    # Tách lệnh thành danh sách tham số và chạy trực tiếp (không qua shell),
    # nhờ vậy khi hết timeout tiến trình bị dừng ngay.
    command = [sys.executable if part == "{python}" else part
               for part in shlex.split(case.command)]
    start = time.perf_counter()
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=case.timeout)
    except FileNotFoundError:
        return TestResult(case.id, case.name, FAIL, 0.0, f"Không tìm thấy lệnh: {command[0]}")
    except subprocess.TimeoutExpired:
        return TestResult(case.id, case.name, FAIL, round(time.perf_counter() - start, 2),
                          f"Quá thời gian {case.timeout}s")
    duration = round(time.perf_counter() - start, 2)
    output = (proc.stdout + proc.stderr).strip()

    if proc.returncode != case.expect_exit_code:
        message = f"Mã thoát {proc.returncode}, mong đợi {case.expect_exit_code}"
        return TestResult(case.id, case.name, FAIL, duration, message)
    if case.expect_regex and not re.search(case.expect_regex, output):
        message = f"Output không khớp /{case.expect_regex}/: {output[:80]!r}"
        return TestResult(case.id, case.name, FAIL, duration, message)
    return TestResult(case.id, case.name, PASS, duration, output[:80])


def export_csv(results: list[TestResult], path: str | Path) -> None:
    # utf-8-sig để Excel mở file hiển thị đúng tiếng Việt
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "status", "duration_s", "message"])
        writer.writeheader()
        writer.writerows(asdict(r) for r in results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy test case từ file JSON")
    parser.add_argument("file")
    parser.add_argument("--csv", help="xuất kết quả ra file CSV")
    args = parser.parse_args()

    results = []
    for tc in load_test_cases(args.file):
        result = run_test_case(tc)
        results.append(result)
        print(f"{result.id:8} {result.status:5} {result.duration_s:5.2f}s  "
              f"{result.name} - {result.message}")
    passed = sum(r.status == PASS for r in results)
    print(f"Tổng: {passed}/{len(results)} PASS")
    if args.csv:
        export_csv(results, args.csv)
    sys.exit(0 if passed == len(results) else 1)
