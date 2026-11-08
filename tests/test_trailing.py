"""R-006 (Q-003): kill, throttle, propsim and monitor against the end-of-day high-water mark."""
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pfm import backtest, data, monitor, propsim, release
from pfm.metrics import check_gate
from pfm.risk import AccountState, RiskEngine

MQH = Path(__file__).resolve().parent.parent / "mql5/Include/PFM/RiskEngine.mqh"
T_OK = pd.Timestamp("2026-11-03 09:00", tz="UTC")       # 14:30 IST Tuesday


def st(eq, hwm=None, day_start=None, **kw):
    return AccountState(initial=50000, equity=eq, day_start_equity=day_start or eq, eod_hwm=hwm, **kw)


def trailing(cfg):
    return RiskEngine(cfg, max_loss_trailing=True)


# ---------------------------------------------------------------- risk engine
def test_q003_example_kill_and_throttle_follow_the_mark(risk_cfg):
    e = trailing(risk_cfg)                                # mark 54,500: firm floor 49,500
    assert e.update_limits(st(51500, 54500)) == "kill"    # 3,000 below the mark, above the floor
    assert e.update_limits(st(51501, 54500)) is None
    assert e.risk_pct(st(53000, 54500)) == risk_cfg["throttle_risk_pct"]
    assert e.risk_pct(st(53001, 54500)) == risk_cfg["risk_per_trade_pct"]


def test_static_engine_ignores_the_mark(risk_cfg):
    e = RiskEngine(risk_cfg)
    assert e.mark(st(50000, 54500)) == 50000
    assert e.update_limits(st(51500, 54500)) is None
    assert e.risk_pct(st(51500, 54500)) == risk_cfg["risk_per_trade_pct"]
    assert e.update_limits(st(47000, 54500)) == "kill"


def test_kill_room_in_check_is_measured_from_the_mark(risk_cfg):
    # 2,900 below the mark: 100 of kill room, throttled risk would be 125
    d = trailing(risk_cfg).check(st(51600, 54500), T_OK, 2000, 1995, 25, 25)
    assert d.ok and d.risk_usd <= 100 + 1e-6 and d.lots == 0.2
    assert trailing(risk_cfg).check(st(51500, 54500), T_OK, 2000, 1995, 25, 25).reason == "size_zero"
    d = RiskEngine(risk_cfg).check(st(51600, 54500), T_OK, 2000, 1995, 25, 25)
    assert d.ok and d.lots == 0.5                         # static: no limit near


def test_mark_is_never_below_initial_and_only_rises(risk_cfg):
    e = trailing(risk_cfg)
    assert e.mark(st(48000)) == 50000 and e.mark(st(48000, 49000)) == 50000
    s = st(51000)
    e.close_day(s)
    assert s.eod_hwm == 51000
    s.equity = 50500
    e.close_day(s)
    assert s.eod_hwm == 51000


def test_trailing_without_a_gain_equals_static(risk_cfg):
    for eq in (50000, 49000, 48400, 47100, 47000):
        a, b = RiskEngine(risk_cfg), trailing(risk_cfg)
        assert a.update_limits(st(eq, day_start=50000)) == b.update_limits(st(eq, day_start=50000))
        assert a.check(st(eq), T_OK, 2000, 1995, 25, 25) == b.check(st(eq), T_OK, 2000, 1995, 25, 25)


# ---------------------------------------------------------------- backtests stay comparable (item 5)
def test_backtest_is_unchanged_unless_the_path_is_on(risk_cfg):
    from tests.legacy_pre_r022 import LondonFadePreR022
    bars = data.synthetic(days=900)
    sigs = LondonFadePreR022().generate_signals(bars)     # frozen input: these pins guard the backtester, not B (R-022)
    off = backtest.run(bars, sigs, risk_cfg).trades
    # 275 trades and this P&L were recorded before R-006, on main at 3f26e86
    assert len(off) == 275 and round(off.pnl.sum(), 2) == 4251.61
    on = backtest.run(bars, sigs, risk_cfg, max_loss_trailing=True).trades
    assert len(on) == 186 and round(on.pnl.sum(), 2) == 1773.69             # the path does something when on
    research = {**risk_cfg, "kill_dd_pct": 1e9, "throttle_dd_pct": 1e9}     # what pfm/worker.py run_job uses
    pd.testing.assert_frame_equal(backtest.run(bars, sigs, research).trades,
                                  backtest.run(bars, sigs, research, max_loss_trailing=True).trades)


# ---------------------------------------------------------------- propsim
def r_trades(r_values):
    days = pd.bdate_range("2025-01-06", periods=len(r_values), tz="UTC") + pd.Timedelta(hours=9)
    return pd.DataFrame({"entry_time": days, "exit_time": days + pd.Timedelta(hours=2), "r": r_values,
                         "mae_r": [1.0 if r < 0 else 0.3 for r in r_values], "pnl": r_values})


def test_propsim_static_figures_match_the_old_simulator(product, risk_cfg):
    rs = np.random.default_rng(3).choice([1.6, -1.0], size=400, p=[.45, .55])
    out = propsim.simulate(r_trades(rs), product, risk_cfg, runs=200)
    # recorded from main at 3f26e86, before R-006
    assert out["static"] == {"runs": 200, "pass_rate": 0.025, "breach_rate": 0.06, "unfinished_rate": 0.915,
                             "median_days_to_pass": 116.0, "fail_reasons": {"internal_kill": 12}}
    assert out["trailing"]["breach_rate"] > out["static"]["breach_rate"]


def test_propsim_trailing_floor_breaches_where_static_does_not(product):
    risk = {"risk_per_trade_pct": 0.5, "throttle_risk_pct": 0.5, "throttle_dd_pct": 1e9, "kill_dd_pct": 1e9,
            "daily_stop_pct": 1e9, "daily_profit_stop_pct": 1e9}
    prod = {**product, "steps": [{"target_pct": 90.0, "min_profitable_days": 3}]}
    # about +10% to a mark near 55,000, then −12%: under the trailing floor, far above the static 45,000
    t = r_trades([2.0] * 10 + [-2.0] * 12).assign(mae_r=0.0)
    out = propsim.simulate(t, prod, risk, runs=5)
    assert out["static"]["breach_rate"] == 0.0
    assert out["trailing"]["fail_reasons"] == {"max_loss": 5}


def test_propsim_mark_resets_at_the_next_step(product, risk_cfg):
    # step 1 passed at +10%; the next step starts at 50,000 with the mark back at 50,000
    prod = {**product, "steps": [{"target_pct": 4.0, "min_profitable_days": 1}, {"target_pct": 4.0, "min_profitable_days": 1}]}
    out = propsim.simulate(r_trades([2.0] * 40), prod, risk_cfg, runs=1)
    assert out["trailing"]["pass_rate"] == 1.0


def test_gate_reads_trailing_when_the_product_trails(product, risk_cfg):
    rs = np.random.default_rng(3).choice([1.6, -1.0], size=400, p=[.45, .55])
    out = propsim.simulate(r_trades(rs), product, risk_cfg, runs=200)
    assert out["gated_on"] == "trailing" and out["pass_rate"] == out["trailing"]["pass_rate"]
    assert out["breach_rate"] == out["trailing"]["breach_rate"]
    ok, _ = check_gate("propsim", out, {"propsim": {"min_pass_rate": 0.3, "max_breach_rate": 0.4}})
    assert not ok
    st_prod = {**product, "max_loss_trailing": False}
    out = propsim.simulate(r_trades(rs), st_prod, risk_cfg, runs=200)
    assert out["gated_on"] == "static" and out["pass_rate"] == out["static"]["pass_rate"]


def test_propsim_empty_trades_keep_their_shape(product, risk_cfg):
    out = propsim.simulate(pd.DataFrame(), product, risk_cfg)
    assert out["pass_rate"] == 0.0 and out["static"]["runs"] == 0 and out["trailing"]["runs"] == 0


# ---------------------------------------------------------------- monitor
def test_monitor_room_uses_the_trailing_floor(product, risk_cfg):
    s = monitor.evaluate(50000, 50000, product, risk_cfg, eod_hwm=54500)
    assert s["room_to_firm_max_pct"] == 1.0 and s["room_to_kill_pct"] == -3.0 and s["eod_hwm"] == 54500
    assert any("firm MAX" in a for a in s["alerts"])
    assert s["overall_dd_pct"] == 0.0


def test_monitor_static_product_is_unchanged(product, risk_cfg):
    s = monitor.evaluate(50000, 50000, {**product, "max_loss_trailing": False}, risk_cfg, eod_hwm=54500)
    assert s["room_to_firm_max_pct"] == 10.0 and s["room_to_kill_pct"] == 6.0 and "eod_hwm" not in s


def test_monitor_mark_unknown_or_below_initial_uses_initial(product, risk_cfg):
    for hwm in (None, 49000):
        assert monitor.evaluate(49000, 50000, product, risk_cfg, hwm)["room_to_firm_max_pct"] == 8.0


def test_saved_hwm(tmp_path):
    f = tmp_path / "status.json"
    assert monitor.saved_hwm(f) is None
    f.write_text("not json", encoding="utf-8")
    assert monitor.saved_hwm(f) is None
    f.write_text('{"eod_hwm": 51000.5}', encoding="utf-8")
    assert monitor.saved_hwm(f) == 51000.5


# ---------------------------------------------------------------- EA
def test_release_set_carries_the_firm_flag():
    assert "InpMaxLossTrailing=true\n" in release.make_set("the5ers_hs50k_10d", "B", 10.0)


def test_ea_uses_the_mark_everywhere_python_does():
    src = MQH.read_text(encoding="utf-8")
    assert "(InpAccountSize-eq)" not in src                         # no static measure left in kill or throttle
    assert "PfmDrawdownPct(Mark(),InpAccountSize,eq)" in src and "PfmKillRoom(Mark()," in src
    assert "PfmDayBase(m_dayStartEquity,m_dayPeakEquity)" in src    # item 4: stricter daily base
    assert re.search(r"m_dayPeakEquity=MathMax\(m_dayPeakEquity,eq\);\s+if\(KillFlagPresent", src)


SHIM = r"""
#include <stdio.h>
#include <stdbool.h>
%s
int main(void){ int t; double s,h,e,k,o,d,p;
  while(scanf("%%d %%lf %%lf %%lf %%lf %%lf %%lf %%lf",&t,&s,&h,&e,&k,&o,&d,&p)==8){
    double m=PfmMark(t,s,h);
    printf("%%.6f %%.6f %%.6f %%.6f\n",m,PfmDrawdownPct(m,s,e),PfmKillRoom(m,s,k,e,o),PfmDayBase(d,p)); }
  return 0; }
"""


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_ea_limit_arithmetic_matches_python(tmp_path, risk_cfg):
    block = re.search(r"PFM-LIMITS-BEGIN.*?\n(.*)//--- PFM-LIMITS-END", MQH.read_text(encoding="utf-8"), re.S).group(1)
    src, exe = tmp_path / "limits.c", tmp_path / "limits"
    src.write_text(SHIM % block, encoding="utf-8")
    subprocess.run(["cc", "-w", "-x", "c", str(src), "-o", str(exe)], check=True)
    rng = np.random.default_rng(0)
    cases, want = [], []
    for _ in range(500):
        tr, hwm, eq, op = bool(rng.integers(0, 2)), rng.uniform(45000, 56000), rng.uniform(44000, 56000), rng.uniform(0, 500)
        ds, pk = rng.uniform(47000, 55000), rng.uniform(47000, 55000)
        e = RiskEngine(risk_cfg, max_loss_trailing=tr)
        s = AccountState(initial=50000, equity=eq, day_start_equity=ds, day_peak_equity=pk, eod_hwm=hwm)
        m = e.mark(s)
        cases.append(f"{int(tr)} 50000 {hwm!r} {eq!r} {risk_cfg['kill_dd_pct']} {op!r} {ds!r} {pk!r}")
        want.append((m, (m - eq) / 50000 * 100, 50000 * risk_cfg["kill_dd_pct"] / 100 - (m - eq) - op, max(ds, pk)))
    out = subprocess.run([str(exe)], input="\n".join(cases), capture_output=True, text=True, check=True).stdout.split("\n")
    for line, w in zip(out, want):
        assert [float(x) for x in line.split()] == pytest.approx(list(w), abs=1e-5)
    assert len([x for x in out if x]) == 500
