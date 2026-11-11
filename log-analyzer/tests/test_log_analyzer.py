import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate_logs import generate
from log_analyzer import error_table, parse_folder, parse_log, summarize

PASS_LOG = """2026-11-10 08:00:00 [INFO] SN=DUT000001 STATION=FT1 START
2026-11-10 08:00:02 [INFO] STEP=FW_VERSION RESULT=PASS
2026-11-10 08:00:03 [INFO] SN=DUT000001 FINAL=PASS
"""

FAIL_LOG = """2026-11-10 08:00:00 [INFO] SN=DUT000002 STATION=FT2 START
2026-11-10 08:00:02 [ERROR] STEP=WIFI_TEST RESULT=FAIL CODE=ERR_TIMEOUT
2026-11-10 08:00:03 [INFO] SN=DUT000002 FINAL=FAIL
"""


def test_parse_pass_log():
    record = parse_log(PASS_LOG)
    assert record["sn"] == "DUT000001"
    assert record["station"] == "FT1"
    assert record["result"] == "PASS"
    assert record["error_code"] is None


def test_parse_fail_log():
    record = parse_log(FAIL_LOG)
    assert record["result"] == "FAIL"
    assert record["fail_step"] == "WIFI_TEST"
    assert record["error_code"] == "ERR_TIMEOUT"


def test_log_without_final_line_is_incomplete():
    record = parse_log(PASS_LOG.splitlines()[0])
    assert record["result"] == "INCOMPLETE"


def test_summary_and_error_table(tmp_path):
    (tmp_path / "a.log").write_text(PASS_LOG, encoding="utf-8")
    (tmp_path / "b.log").write_text(FAIL_LOG, encoding="utf-8")
    df = parse_folder(tmp_path)
    summary = summarize(df)
    assert summary["total"] == 2
    assert summary["pass"] == 1
    assert summary["yield_rate_%"] == 50.0
    errors = error_table(df)
    assert errors.loc[0, "error_code"] == "ERR_TIMEOUT"
    assert errors.loc[0, "count"] == 1


def test_generated_logs_are_all_parsed(tmp_path):
    generate(50, tmp_path, fail_rate=0.1, seed=1)
    df = parse_folder(tmp_path)
    assert len(df) == 50
    assert set(df["result"]) <= {"PASS", "FAIL"}
    assert df["sn"].notna().all()
