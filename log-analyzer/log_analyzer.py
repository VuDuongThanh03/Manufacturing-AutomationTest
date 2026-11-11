"""Đọc hàng loạt file .log kiểm tra thiết bị, thống kê lỗi và xuất báo cáo.

Cách chạy:
    python log_analyzer.py --logs logs --out report

Kết quả:
    report/report.xlsx  - 3 sheet: Summary, Devices, Errors
    report/errors.png   - biểu đồ số lần xuất hiện của từng mã lỗi
"""
import argparse
import re
import time
from pathlib import Path

import pandas as pd

# Dòng mở đầu:  ... SN=DUT000001 STATION=FT1 START
RE_START = re.compile(r"SN=(?P<sn>\w+)\s+STATION=(?P<station>\w+)\s+START")
# Dòng lỗi:     ... [ERROR] STEP=WIFI_TEST RESULT=FAIL CODE=ERR_TIMEOUT
RE_FAIL = re.compile(r"\[ERROR\]\s+STEP=(?P<step>\w+)\s+RESULT=FAIL\s+CODE=(?P<code>\w+)")
# Dòng kết quả: ... SN=DUT000001 FINAL=PASS
RE_FINAL = re.compile(r"SN=(?P<sn>\w+)\s+FINAL=(?P<final>PASS|FAIL)")


def parse_log(text: str) -> dict:
    """Phân tích nội dung một file log, trả về thông tin của thiết bị.

    Log thiếu dòng FINAL (test bị ngắt giữa chừng) được đánh dấu INCOMPLETE.
    """
    record = {"sn": None, "station": None, "result": "INCOMPLETE",
              "fail_step": None, "error_code": None}
    for line in text.splitlines():
        if m := RE_START.search(line):
            record["sn"] = m["sn"]
            record["station"] = m["station"]
        elif m := RE_FAIL.search(line):
            record["fail_step"] = m["step"]
            record["error_code"] = m["code"]
        elif m := RE_FINAL.search(line):
            record["sn"] = record["sn"] or m["sn"]
            record["result"] = m["final"]
    return record


def parse_folder(log_dir: Path) -> pd.DataFrame:
    """Đọc toàn bộ file .log trong thư mục thành một bảng dữ liệu."""
    records = []
    for path in sorted(log_dir.glob("*.log")):
        record = parse_log(path.read_text(encoding="utf-8", errors="replace"))
        record["file"] = path.name
        records.append(record)
    return pd.DataFrame(records, columns=["file", "sn", "station", "result",
                                          "fail_step", "error_code"])


def summarize(df: pd.DataFrame) -> dict:
    """Tính tổng số thiết bị, số PASS/FAIL và tỉ lệ đạt (yield rate)."""
    total = len(df)
    passed = int((df["result"] == "PASS").sum())
    failed = int((df["result"] == "FAIL").sum())
    return {
        "total": total,
        "pass": passed,
        "fail": failed,
        "incomplete": total - passed - failed,
        "yield_rate_%": round(passed / total * 100, 2) if total else 0.0,
        "defect_rate_%": round(failed / total * 100, 2) if total else 0.0,
    }


def error_table(df: pd.DataFrame) -> pd.DataFrame:
    """Gom nhóm theo mã lỗi và bước test, sắp xếp giảm dần theo số lần gặp."""
    fails = df[df["result"] == "FAIL"]
    if fails.empty:
        return pd.DataFrame(columns=["error_code", "fail_step", "count"])
    return (fails.groupby(["error_code", "fail_step"]).size()
            .reset_index(name="count")
            .sort_values("count", ascending=False, ignore_index=True))


def export_report(df: pd.DataFrame, out_dir: Path) -> None:
    """Xuất báo cáo Excel và biểu đồ lỗi."""
    import matplotlib
    matplotlib.use("Agg")  # vẽ ra file, không cần màn hình
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(df)
    errors = error_table(df)

    with pd.ExcelWriter(out_dir / "report.xlsx") as writer:
        pd.DataFrame([summary]).to_excel(writer, sheet_name="Summary", index=False)
        df.to_excel(writer, sheet_name="Devices", index=False)
        errors.to_excel(writer, sheet_name="Errors", index=False)

    by_code = errors.groupby("error_code")["count"].sum().sort_values()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if not by_code.empty:
        ax.barh(by_code.index, by_code.values, color="#c0392b")
    ax.set_title(f"Error codes - yield {summary['yield_rate_%']}% "
                 f"({summary['pass']}/{summary['total']})")
    ax.set_xlabel("Number of devices")
    fig.tight_layout()
    fig.savefig(out_dir / "errors.png", dpi=120)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phân tích log kiểm tra thiết bị")
    parser.add_argument("--logs", default="logs", help="thư mục chứa file .log")
    parser.add_argument("--out", default="report", help="thư mục xuất báo cáo")
    args = parser.parse_args()

    t0 = time.perf_counter()
    df = parse_folder(Path(args.logs))
    if df.empty:
        raise SystemExit(f"Không tìm thấy file .log nào trong '{args.logs}'")
    export_report(df, Path(args.out))
    elapsed = time.perf_counter() - t0

    print(f"Đã phân tích {len(df)} file log trong {elapsed:.2f} giây")
    for key, value in summarize(df).items():
        print(f"  {key:14}: {value}")
    print(error_table(df).to_string(index=False))
    print(f"Báo cáo: {Path(args.out) / 'report.xlsx'}, {Path(args.out) / 'errors.png'}")


if __name__ == "__main__":
    main()
