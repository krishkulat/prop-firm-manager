import json
import shutil

import numpy as np
import pandas as pd
import pytest

from pfm import propsim


def fake_trades(r_values, start="2025-01-06 09:00"):
    days = pd.bdate_range(start, periods=len(r_values), tz="UTC") + pd.Timedelta(hours=9)
    return pd.DataFrame({"entry_time": days, "exit_time": days + pd.Timedelta(hours=2),
                         "r": r_values, "mae_r": [1.0 if r < 0 else 0.3 for r in r_values], "pnl": r_values})


def test_always_winning_passes(product, risk_cfg):
    out = propsim.simulate(fake_trades([2.0] * 200), product, risk_cfg, runs=50)
    assert out["pass_rate"] == 1.0


def test_always_losing_never_passes(product, risk_cfg):
    out = propsim.simulate(fake_trades([-1.0] * 300), product, risk_cfg, runs=50)
    assert out["pass_rate"] == 0.0 and out["breach_rate"] > 0.9


def test_deflated_sharpe_penalises_trials():
    from pfm.metrics import deflated_sharpe
    r = np.random.default_rng(0).normal(0.0008, 0.01, 500)
    assert deflated_sharpe(r, 1) > deflated_sharpe(r, 50)


@pytest.fixture
def temp_repo(tmp_path, monkeypatch):
    import pfm
    from pfm import ledger, notify, reqs
    root = tmp_path / "repo"
    for d in ("ledger", "config", "strategies"):
        shutil.copytree(pfm.ROOT / d, root / d)
    (root / "requests").mkdir()
    for mod in (pfm, ledger, reqs, notify):
        monkeypatch.setattr(mod, "ROOT", root, raising=False)
    monkeypatch.setattr(ledger, "PATH", root / "ledger/ledger.json")
    monkeypatch.setattr(reqs, "DIR", root / "requests")
    import pfm.config as cfg
    monkeypatch.setattr(cfg, "ROOT", root)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    return root


def test_purchase_flow(temp_repo):
    from pfm import ledger, notify, reqs
    r = reqs.purchase("the5ers/hs50k_10d", "A", "test")
    assert r["id"] == "P-001" and ledger.balances()["pending"] == 99
    reply = notify.handle("/bought P-001 87654321")
    assert reply.startswith("OK") and ledger.balances()["spent"] == 99
    l = ledger.load()
    assert l["accounts"][0]["login_last4"] == "4321"
    assert "87654321" not in json.dumps(l)


def test_reject_releases(temp_repo):
    from pfm import ledger, notify, reqs
    reqs.purchase("the5ers/hs50k_10d", "A", "test")
    notify.handle("/reject P-001 not now")
    assert ledger.balances()["pending"] == 0 and ledger.balances()["reserved"] == 99


def test_retry_needs_breach_and_stop_loss(temp_repo):
    from pfm import ledger, notify, reqs
    with pytest.raises(RuntimeError):
        reqs.purchase("the5ers/hs50k_10d", "A", "retry", retry=True)
    reqs.purchase("the5ers/hs50k_10d", "A", "first"); notify.handle("/bought P-001 11112222")
    notify.handle("/breached the5ers-hs50k_10d-P-001")
    reqs.purchase("the5ers/hs50k_10d", "A", "retry", retry=True); notify.handle("/bought P-002 33334444")
    msg = notify.handle("/breached the5ers-hs50k_10d-P-002")
    assert "STOP-LOSS HIT" in msg


def test_cannot_overspend(temp_repo):
    from pfm import reqs
    reqs.purchase("the5ers/hs50k_10d", "A", "one")           # uses the $99 reserved line
    with pytest.raises(RuntimeError):
        reqs.purchase("the5ers/hs100k_10v", "A", "too big")  # $149 > $52 free


def test_payout_split(temp_repo):
    from pfm import ledger
    first = ledger.record_payout("acct", 1200)
    assert first == {"tax_reserve": 360.0, "seed_returned_to_owner": 250, "to_reserve": 590.0}
    second = ledger.record_payout("acct", 1000)
    assert second == {"new_challenges": 400.0, "reserve": 300.0, "owner": 300.0}


def test_monitor_evaluate(product, risk_cfg):
    from pfm.monitor import evaluate
    s = evaluate(48900, 50000, product, risk_cfg)
    assert s["day_loss_pct"] == 2.2 and any("DAILY" in a for a in s["alerts"])
