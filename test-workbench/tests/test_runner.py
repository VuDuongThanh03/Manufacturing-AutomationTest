import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runner import FAIL, PASS, TestCase, export_csv, load_test_cases, run_test_case

SAMPLE = Path(__file__).resolve().parents[1] / "sample_tests.json"


def case(command, **kwargs):
    return TestCase(id="T", name="t", command=command, **kwargs)


def test_pass_when_output_matches():
    result = run_test_case(case("{python} -c \"print('FW:1.2.3')\"", expect_regex=r"FW:\d"))
    assert result.status == PASS


def test_fail_when_output_does_not_match():
    result = run_test_case(case("{python} -c \"print('hello')\"", expect_regex=r"FW:\d"))
    assert result.status == FAIL


def test_fail_on_wrong_exit_code():
    result = run_test_case(case("{python} -c \"import sys; sys.exit(3)\""))
    assert result.status == FAIL
    assert "3" in result.message


def test_fail_on_timeout():
    result = run_test_case(case("{python} -c \"import time; time.sleep(5)\"", timeout=0.5))
    assert result.status == FAIL
    assert result.duration_s < 4


def test_sample_file_gives_expected_results():
    results = [run_test_case(c) for c in load_test_cases(SAMPLE)]
    assert [r.status for r in results] == [PASS, PASS, FAIL, FAIL, PASS]


def test_duplicate_ids_are_rejected(tmp_path):
    path = tmp_path / "dup.json"
    item = {"id": "A", "name": "x", "command": "echo"}
    path.write_text(json.dumps([item, item]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_test_cases(path)


def test_export_csv(tmp_path):
    results = [run_test_case(case("{python} -c \"print('ok')\""))]
    out = tmp_path / "result.csv"
    export_csv(results, out)
    rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
    assert rows[0]["status"] == PASS
