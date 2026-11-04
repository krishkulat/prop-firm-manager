"""Strategy F (H-006) on the synthetic fixture, clocks, no look-ahead, benchmarks, the 13:30 IST window edge."""
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pfm import backtest, data, release, worker
from pfm.risk import AccountState, RiskEngine
from pfm.strategy_base import h1_atr_on
from strategies.F_asian_rise_short.strategy import AsianRiseShort

ROOT = Path(__file__).resolve().parent.parent
EA = ROOT / "mql5/Experts/AsianRiseShort_F.mq5"
MQH = ROOT / "mql5/Include/PFM/RiskEngine.mqh"
IST, NY = "Asia/Kolkata", "America/New_York"


@pytest.fixture(scope="module")
def bars():
    return data.synthetic(days=400, start="2026-01-05")   # spans both 2026 DST changes


def gen(bars, **p):
    return AsianRiseShort().generate_signals(bars, p)


def rise(bars, s):
    a = pd.Series(h1_atr_on(bars).values, index=bars.index).loc[s.time]
    return (bars.at[s.time, "open"] - bars.at[s.time - pd.Timedelta(hours=7), "open"]) / a, a


def test_signals_shape(bars):
    sigs = gen(bars)
    assert sigs
    assert len({s.time.date() for s in sigs}) == len(sigs)                       # one per day
    for s in sigs:
        assert s.time.strftime("%H:%M") == "08:00" and s.time.dayofweek < 5
        assert s.time.tz_convert(IST).strftime("%H:%M") == "13:30"
        assert s.direction == -1 and s.target == -float("inf")
        assert s.stop > bars.at[s.time, "open"]                                  # short only, stop above


@pytest.mark.parametrize("date, ist", [
    ("2026-03-06", "21:30"), ("2026-03-09", "20:30"),     # US DST starts Sunday 2026-03-08
    ("2026-10-30", "20:30"), ("2026-11-02", "21:30"),     # US DST ends Sunday 2026-11-01
])
def test_exit_clock_across_dst(bars, date, ist):
    s = next(s for s in gen(bars, benchmark="no_filter") if str(s.time.date()) == date)
    assert s.time.tz_convert(IST).strftime("%H:%M") == "13:30"                   # the entry does not move
    assert s.exit_time.tz_convert(IST).strftime("%H:%M") == ist
    assert s.exit_time.tz_convert(NY).strftime("%H:%M") == "11:00"


def test_every_exit_stays_before_flat_by(bars, risk_cfg):
    for exit_et in ("10:00", "11:00"):
        for s in gen(bars, benchmark="no_filter", exit_et=exit_et):
            assert s.exit_time.tz_convert(IST).time() < pd.Timestamp(risk_cfg["flat_by_ist"]).time()


def test_rise_atr_and_stop_values(bars):
    for s in gen(bars)[:20]:
        r, a = rise(bars, s)
        assert r >= 0.5
        assert s.stop == pytest.approx(bars.at[s.time, "open"] + 2.0 * a)


def test_threshold_selects_exactly_the_days_with_a_big_enough_rise(bars):
    nof = {s.time: s for s in gen(bars, benchmark="no_filter")}
    want = {t for t, s in nof.items() if rise(bars, s)[0] >= 0.5}
    assert {s.time for s in gen(bars)} == want


def test_no_look_ahead_only_the_entry_bar_open_is_read(bars):
    sigs = gen(bars)
    s = sigs[len(sigs) // 2]
    later = bars.copy()
    later.loc[s.time, ["high", "low", "close"]] *= 1.5                          # the rest of the entry bar
    later.loc[later.index > s.time, ["open", "high", "low", "close"]] *= 1.5    # everything after it
    k = lambda x: (x.time, x.direction, x.stop)
    assert [k(x) for x in gen(later) if x.time <= s.time] == [k(x) for x in sigs if x.time <= s.time]


def test_atr_uses_the_h1_bar_closed_at_entry_and_nothing_newer(bars):
    s = gen(bars)[10]
    assert s.time == s.time.floor("1h")
    a = rise(bars, s)[1]
    changed = bars.copy()
    changed.loc[s.time, "high"] += 500                                          # H1 bar opening at entry: must not count
    assert next(x for x in gen(changed) if x.time == s.time).stop == s.stop
    changed = bars.copy()
    changed.loc[s.time - pd.Timedelta(minutes=15), "high"] += 500               # H1 bar closing at entry: must count
    assert rise(changed, s)[1] > a


def test_missing_bar_skips_the_day(bars):
    s = gen(bars)[5]
    for gone in (s.time, s.time - pd.Timedelta(hours=7)):
        assert s.time not in [x.time for x in gen(bars.drop(index=gone))]


def test_benchmarks(bars):
    base = gen(bars)
    opp = gen(bars, benchmark="opposite_side")
    rnd = gen(bars, benchmark="random_side", benchmark_seed=3)
    assert [s.time for s in opp] == [s.time for s in rnd] == [s.time for s in base]
    assert [s.exit_time for s in rnd] == [s.exit_time for s in base]
    assert all(o.direction == 1 and o.target == float("inf") for o in opp)
    for o, b in zip(opp, base):                                                 # same distance, other side
        p = bars.at[b.time, "open"]
        assert p - o.stop == pytest.approx(b.stop - p)
    assert {s.direction for s in rnd} == {1, -1}
    assert [s.direction for s in rnd] == [s.direction for s in gen(bars, benchmark="random_side", benchmark_seed=3)]
    assert [s.direction for s in rnd] != [s.direction for s in gen(bars, benchmark="random_side", benchmark_seed=4)]
    with pytest.raises(ValueError):
        gen(bars, benchmark="nope")
    with pytest.raises(ValueError):
        gen(bars, exit_et="04:00")


def test_no_filter_is_every_day_not_threshold_zero(bars):
    nof, zero = gen(bars, benchmark="no_filter"), gen(bars, asia_rise_atr=0.0)
    assert all(s.direction == -1 for s in nof)
    assert {s.time for s in zero} < {s.time for s in nof}                       # zero still drops the days Asia fell
    assert any(rise(bars, s)[0] < 0 for s in nof)


# ---------------------------------------------------------------- the 13:30 IST window edge
def test_entry_passes_the_window_edge_in_python(risk_cfg):
    st = AccountState(initial=50000, equity=50000, day_start_equity=50000)
    e = RiskEngine(risk_cfg)
    for day in ("2026-03-06", "2026-03-09", "2026-10-30", "2026-11-02"):        # IST has no DST; both sides of the US change
        assert e.check(st, pd.Timestamp(f"{day} 08:00", tz="UTC"), 2000, 2005, 25, 25).ok
        assert e.check(st, pd.Timestamp(f"{day} 07:59", tz="UTC"), 2000, 2005, 25, 25).reason == "outside_hours"


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_entry_passes_the_window_edge_in_the_ea(tmp_path):
    src = MQH.read_text(encoding="utf-8")
    assert 'InpEntryStartIST      = "13:30"' in src and 'InpEntryEndIST        = "21:00"' in src
    cond = re.search(r"if\((dow==0 \|\| dow==6 \|\| m<ToMinutes\(InpEntryStartIST\).*?)\) \{ reason=\"outside_hours\"", src).group(1)
    code = f"""#include <stdio.h>
#define ToMinutes(x) (x)
enum {{ InpEntryStartIST = 810, InpEntryEndIST = 1260 }};
int main(void){{ int m, dow; while(scanf("%d %d",&m,&dow)==2) printf("%d\\n", ({cond}) ? 1 : 0); return 0; }}
"""
    c, exe = tmp_path / "w.c", tmp_path / "w"
    c.write_text(code, encoding="utf-8")
    subprocess.run(["cc", "-w", str(c), "-o", str(exe)], check=True)
    ist_min = (8 * 60 + 330) % 1440                                             # 08:00 UTC + 05:30, as IstNow does
    cases = f"{ist_min} 2\n{ist_min - 1} 2\n{ist_min} 6\n1259 2\n1260 2\n"
    out = subprocess.run([str(exe)], input=cases, capture_output=True, text=True, check=True).stdout.split()
    assert ist_min == 810 and out == ["0", "1", "1", "0", "1"]                  # 1 = outside_hours


def test_ea_retries_outside_hours_inside_the_entry_bar_only():
    src = EA.read_text(encoding="utf-8")
    i = src.index('if(why=="outside_hours") { lastBar=0; lastSignalDay=-1; return; }')
    assert i < src.index('if(lots<=0) { Print("PFM rejected: ",why); return; }')
    assert "if(t.hour*60+t.min!=ENTRY_MIN_UTC) return;" in src                  # a later bar cannot enter


# ---------------------------------------------------------------- EA
def test_ea_uses_risk_engine_and_visible_stop():
    src = EA.read_text(encoding="utf-8")
    assert "#include <PFM/RiskEngine.mqh>" in src
    assert "Risk.Check(entry,stop,news,why)" in src and 'Risk.Open(-1,lots,stop,0.0,"PFM-F")' in src
    assert "Risk.OnTickLimits(news)" in src
    assert "m_trade.Buy" not in src and ".Buy(" not in src                      # short only


def test_ea_dst_block_is_the_tested_one():
    block = lambda p: re.search(r"PFM-DST-BEGIN[^\n]*\n(.*)//--- PFM-DST-END", p.read_text(encoding="utf-8"), re.S).group(1)
    assert block(EA) == block(ROOT / "mql5/Experts/UsOpenImpulse_E.mq5")


def test_ea_defaults_match_params_yaml():
    import yaml
    y = yaml.safe_load((ROOT / "strategies/F_asian_rise_short/params.yaml").read_text(encoding="utf-8"))["default"]
    src = EA.read_text(encoding="utf-8")
    assert re.search(rf"InpAsiaRiseATR\s*=\s*{y['asia_rise_atr']};", src)
    assert re.search(rf"InpStopATR\s*=\s*{y['stop_atr']};", src)
    assert re.search(rf'InpExitET\s*=\s*"{y["exit_et"]}";', src)


# ---------------------------------------------------------------- pipeline
def test_runs_through_backtester(bars, risk_cfg):
    r = backtest.run(bars, gen(bars), risk_cfg)
    assert len(r.trades) > 0 and "outside_hours" not in r.rejections
    assert set(r.trades.reason) <= {"time_exit", "stop", "end_of_data", "daily_stop", "daily_profit_stop"}
    assert (r.trades.reason == "time_exit").any()
    assert (r.trades.direction == -1).all()


def test_worker_loads_it_from_the_registry_and_exit_stays_a_string():
    strat, reg = worker.load_strategy("F")
    assert isinstance(strat, AsianRiseShort) and reg["stage"] == "coded"
    assert "InpAsiaRiseATR=0.5\n" in release.make_set("the5ers_hs50k_10d", "F", 10.0)
    assert 'InpExitET=11:00\n' in release.make_set("the5ers_hs50k_10d", "F", 10.0)


def test_three_tunable_params_match_params_yaml():
    import yaml
    y = yaml.safe_load((ROOT / "strategies/F_asian_rise_short/params.yaml").read_text(encoding="utf-8"))
    assert set(y["ranges"]) == set(y["default"]) == {"asia_rise_atr", "stop_atr", "exit_et"}
    assert all(AsianRiseShort.default_params[k] == v for k, v in y["default"].items())
    assert all(y["default"][k] in y["ranges"][k] for k in y["default"])
    assert all(isinstance(v, str) for v in y["ranges"]["exit_et"])              # a bare 11:00 is the integer 660 in YAML
    assert np.prod([len(v) for v in y["ranges"].values()]) + 4 <= 50
