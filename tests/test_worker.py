"""R-012: backtest summary reports a +50% spread stress next to the +50% slippage one."""
import json
import subprocess
import sys
from types import SimpleNamespace

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


def test_second_worker_cannot_take_the_lock(tmp_path):
    p = tmp_path / "logs" / "worker.lock"
    first = worker.acquire_lock(p)
    assert first is not None
    code = ("import sys; from pathlib import Path; from pfm import worker; "
            f"sys.exit(0 if worker.acquire_lock(Path({str(p)!r})) is None else 1)")
    assert subprocess.run([sys.executable, "-c", code], cwd=worker.ROOT).returncode == 0      # refused while held
    first.close()
    second = worker.acquire_lock(p)                                                            # free once released
    assert second is not None
    second.close()


def test_code_changed_only_for_code_paths(monkeypatch):
    files = {"docs": "results/reports/daily/x.md\nqueue/pending/J.yaml\n", "code": "results/x.md\npfm/worker.py\n",
             "strategy": "strategies/F_x/strategy.py\n"}
    monkeypatch.setattr(worker, "git", lambda *a, **k: SimpleNamespace(stdout=files[a[-1]]))
    assert not worker.code_changed("a", "docs")
    assert worker.code_changed("a", "code")
    assert worker.code_changed("a", "strategy")
    assert not worker.code_changed("a", "a")
    assert not worker.code_changed("", "code")                                                 # no HEAD read
