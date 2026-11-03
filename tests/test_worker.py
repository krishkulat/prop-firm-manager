"""R-012: backtest summary reports a +50% spread stress next to the +50% slippage one."""
import json

import pandas as pd

from pfm import worker


def run_synthetic(tmp_path, monkeypatch, job_id="J-TEST-001"):
    monkeypatch.setattr(worker, "RESULTS", tmp_path)
    monkeypatch.setattr(worker, "TRIALS", tmp_path / "trials.csv")
    job = {"job_id": job_id, "kind": "backtest", "strategy": "B", "hypothesis": "H-TEST",
           "requested_by": "test", "data": {"synthetic": True, "days": 600}}
    return worker.run_job(job), tmp_path / job_id / "summary.json"


def test_summary_has_stress_spread_pf(tmp_path, monkeypatch):
    s, path = run_synthetic(tmp_path, monkeypatch)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["stress_spread_pf"] == s["stress_spread_pf"]
    assert s["stress_spread_pf"] < s["pf"]                           # a wider spread costs money
    assert s["stress_slip_pf"] != s["stress_spread_pf"]              # 25 pt spread and 30 pt slip stress differ


def test_stress_spread_is_reporting_only(tmp_path, monkeypatch):
    s, _ = run_synthetic(tmp_path, monkeypatch)
    assert "stress_spread_pf" not in str(s["gate"])
    assert len(pd.read_csv(tmp_path / "trials.csv")) == 1            # the stress runs are not extra trials
