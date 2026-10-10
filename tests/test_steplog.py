import json
from datetime import date, datetime

import pytest

from blend import model as models
from blend.steplog import StepLog

NOW = datetime(2026, 10, 10, 9, 30)


def test_append_numbers_steps_and_keeps_code(models_dir):
    m = models.create("frame", base=models_dir)
    m.new_session("blockout", on=date(2026, 10, 10))
    log = StepLog(m)
    a = log.append("Outline Curve", intent="CTL outline", code="print(1)\n\n", now=NOW)
    b = log.append(
        "depth", params={"Depth": 60.0}, objects=["Frame"], session="other", now=NOW
    )
    assert (a.n, a.slug, a.code) == (1, "outline-curve", "001-outline-curve.py")
    assert a.session == "2026-10-10-blockout"  # defaults to the latest note
    assert (m.log_dir / a.code).read_text() == "# step 1: CTL outline\nprint(1)\n"
    assert b.n == 2 and b.code is None and b.session == "other"
    lines = log.jsonl.read_text().splitlines()
    assert json.loads(lines[1])["params"] == {"Depth": 60.0}
    assert [s.slug for s in log.entries()] == ["outline-curve", "depth"]
    assert [s.n for s in log.last(1)] == [2]
    assert len(log.last(0)) == 2


def test_speckle_version_attaches_to_latest_or_n(models_dir):
    log = StepLog(models.create("frame", base=models_dir))
    with pytest.raises(LookupError):
        log.set_speckle_version("abc")
    log.append("a", now=NOW)
    log.append("b", now=NOW)
    assert log.set_speckle_version("v2").n == 2
    assert log.set_speckle_version("v1", n=1).n == 1
    assert [s.speckle_version for s in log.entries()] == ["v1", "v2"]
    with pytest.raises(LookupError):
        log.set_speckle_version("x", n=9)
