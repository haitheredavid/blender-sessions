import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from blend import cli, printresults
from blend import model as models

FIXTURE = Path(__file__).parent / "fixtures" / "results.json"
MANIFEST = {
    "schema": "print-spec/1",
    "created": "2026-10-11T13:00:00-04:00",  # after the slice at 12:30
    "feedback_applied": ["rec-20261011-01"],
    "feedback_declined": ["rec-20261011-04"],
}


def pack(tmp_path: Path, session_hash: str = "bbbb") -> Path:
    d = tmp_path / "print" / "coupon"
    d.mkdir(parents=True)
    shutil.copy(FIXTURE, d / "results.json")
    (d / "manifest.json").write_text(json.dumps(MANIFEST))
    (d / "session.toml").write_text(f'[source]\nspec_hash = "{session_hash}"\n')
    return d


def test_facts_per_kind():
    runs = {r["id"]: r for r in json.loads(FIXTURE.read_text())["runs"]}
    assert printresults.facts(runs["che-20261011-01"]) == "warn; block 0; warn 6"
    assert printresults.facts(runs["sli-20261011-01"]) == (
        "0.16mm_optimal; 54m; 18.1 g; insignia_petg; enable_support=1"
    )
    assert printresults.facts(runs["pri-20261011-01"]) == "started"
    assert printresults.facts(runs["pri-20261011-02"]) == (
        "failed; Coupon_C10_Flat_A: sag z9; chamfer one clean"
    )
    assert printresults.facts(runs["fit-20261011-01"]).startswith("tenon-E = 0.1; petg")
    assert printresults.facts({"kind": "slice", "seconds": 7380}) == "2h03"


def test_report_statuses_and_staleness(tmp_path):
    d = pack(tmp_path)
    cfg = {"feedback_applied": ["rec-20261011-02"]}  # in model.toml, not re-packed
    rep = printresults.report(d, cfg)
    status = {r["id"]: r["status"] for r in rep["recommendations"]}
    assert status == {
        "rec-20261011-01": "applied",
        "rec-20261011-02": "applied, not re-packed",
        "rec-20261011-03": "pending",
        "rec-20261011-04": "declined",
    }
    assert rep["pending"] == ["rec-20261011-03"]
    assert len(rep["runs"]) == 5 and rep["spec"] == "print-spec/1"
    assert any("session.toml records bbbb" in n for n in rep["stale"])
    assert any(n.startswith("re-packed since slice?") for n in rep["stale"])


def test_report_fresh_slice_is_not_stale(tmp_path):
    d = pack(tmp_path, session_hash="aaaa")
    (d / "manifest.json").write_text(
        json.dumps({**MANIFEST, "created": "2026-10-11T12:00:00-04:00"})
    )
    assert printresults.report(d, {})["stale"] == []


def test_cli_print_results(tmp_path, monkeypatch):
    model = models.Model(tmp_path)
    (tmp_path / "model.toml").write_text(
        '[print]\ncollection = "Print"\n\n[print.Coupon]\n'
        'feedback_applied = ["rec-20261011-03"]\n'
    )
    pack(tmp_path)
    monkeypatch.setattr(cli, "_model", lambda ref: model)
    runner = CliRunner()
    res = runner.invoke(cli.app, ["print-results", "x", "--pack", "coupon", "--json"])
    assert res.exit_code == 0, res.output
    rep = json.loads(res.output)
    assert rep["pending"] == ["rec-20261011-02"]  # 03: applied in [print.Coupon]
    res = runner.invoke(cli.app, ["print-results", "x", "--pack", "coupon"])
    assert res.exit_code == 0 and "sli-20261011-01" in res.output
    assert runner.invoke(cli.app, ["print-results", "x"]).exit_code == 1  # no main pack
