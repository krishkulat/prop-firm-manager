"""Strategy E (H-004) on the synthetic fixture, DST handling in Python and in the EA, no look-ahead."""
import re
import shutil
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from pfm import backtest, data
from strategies.E_us_open_impulse.strategy import UsOpenImpulse

EA = Path(__file__).resolve().parent.parent / "mql5/Experts/UsOpenImpulse_E.mq5"
IST, NY = "Asia/Kolkata", "America/New_York"


@pytest.fixture(scope="module")
def bars():
    return data.synthetic(days=400, start="2026-01-05")   # spans both 2026 DST changes


def gen(bars, **p):
    return UsOpenImpulse().generate_signals(bars, p)


def test_signals_shape(bars):
    sigs = gen(bars)
    assert sigs
    assert len({s.time.tz_convert(NY).date() for s in sigs}) == len(sigs)        # one per day
    for s in sigs:
        ny = s.time.tz_convert(NY)
        assert (ny.hour, ny.minute) == (9, 30) and ny.dayofweek < 5
        ex = s.exit_time.tz_convert(NY)
        assert (ex.hour, ex.minute) == (11, 30) and ex.date() == ny.date()
        assert s.target == s.direction * float("inf")
        c = bars.at[s.time - pd.Timedelta(minutes=15), "close"]
        assert (s.stop - c) * s.direction < 0                                    # stop on the losing side


@pytest.mark.parametrize("date, ist", [
    ("2026-03-06", "20:00"), ("2026-03-09", "19:00"),     # US DST starts Sunday 2026-03-08
    ("2026-10-30", "19:00"), ("2026-11-02", "20:00"),     # US DST ends Sunday 2026-11-01
])
def test_entry_clock_across_dst(bars, date, ist):
    s = next(s for s in gen(bars, benchmark="no_filter") if str(s.time.tz_convert(NY).date()) == date)
    assert s.time.tz_convert(IST).strftime("%H:%M") == ist


def test_every_default_exit_stays_before_flat_by_and_entry_inside_window(bars, risk_cfg):
    for s in gen(bars, benchmark="no_filter"):
        e, x = s.time.tz_convert(IST).time(), s.exit_time.tz_convert(IST).time()
        assert pd.Timestamp(risk_cfg["entry_start_ist"]).time() <= e < pd.Timestamp(risk_cfg["entry_end_ist"]).time()
        assert x < pd.Timestamp(risk_cfg["flat_by_ist"]).time()


def test_impulse_atr_and_stop_values(bars):
    from pfm.strategy_base import h1_atr_on
    atr = pd.Series(h1_atr_on(bars).values, index=bars.index)
    for s in gen(bars)[:20]:
        ny = s.time.tz_convert(NY)
        a = atr.loc[s.time]
        c = bars.at[s.time - pd.Timedelta(minutes=15), "close"]
        o = bars.at[s.time - pd.Timedelta(hours=1), "open"]
        assert (ny - pd.Timedelta(hours=1)).strftime("%H:%M") == "08:30"
        assert abs((c - o) / a) >= 1.0 and np.sign(c - o) == s.direction
        assert s.stop == pytest.approx(c - s.direction * 1.5 * a)


def test_no_look_ahead_future_bars_change_nothing(bars):
    sigs = gen(bars)
    s = sigs[len(sigs) // 2]
    later = bars.copy()
    # entry bar onward, including the unfinished H1 bar around the entry and the rest of its day
    mask = later.index >= s.time
    later.loc[mask, ["open", "high", "low", "close"]] *= 1.5
    k = lambda x: (x.time, x.direction, x.stop)
    assert [k(x) for x in gen(later) if x.time <= s.time] == [k(x) for x in sigs if x.time <= s.time]


def test_atr_ignores_the_h1_bar_still_open_at_entry(bars):
    s = gen(bars)[10]
    h1_open = s.time.floor("1h")
    assert h1_open < s.time                                                     # entry falls inside an H1 bar
    changed = bars.copy()
    changed.loc[h1_open, "high"] = bars.at[h1_open, "high"] + 500               # huge range in the unfinished H1 bar
    out = next(x for x in gen(changed) if x.time == s.time)
    assert out.stop == s.stop


def test_missing_bar_skips_the_day(bars):
    s = gen(bars)[5]
    for gone in (s.time, s.time - pd.Timedelta(minutes=15), s.time - pd.Timedelta(hours=1)):
        assert s.time not in [x.time for x in gen(bars.drop(index=gone))]


def test_benchmarks(bars):
    base = gen(bars)
    opp = gen(bars, benchmark="opposite_side")
    rnd = gen(bars, benchmark="random_side", benchmark_seed=3)
    nof = gen(bars, benchmark="no_filter")
    assert [s.time for s in opp] == [s.time for s in rnd] == [s.time for s in base]
    assert [s.exit_time for s in rnd] == [s.exit_time for s in base]
    assert all(o.direction == -b.direction for o, b in zip(opp, base))
    for o, b in zip(opp, base):                                                 # same distance, other side
        c = bars.at[b.time - pd.Timedelta(minutes=15), "close"]
        assert o.stop - c == pytest.approx(c - b.stop)
    assert {s.direction for s in rnd} == {1, -1}
    assert [s.direction for s in rnd] == [s.direction for s in gen(bars, benchmark="random_side", benchmark_seed=3)]
    assert [s.direction for s in rnd] != [s.direction for s in gen(bars, benchmark="random_side", benchmark_seed=4)]
    assert len(nof) > len(base) and set(s.time for s in base) <= set(s.time for s in nof)
    assert [s.time for s in nof] == [s.time for s in gen(bars, impulse_atr=0.0)]
    with pytest.raises(ValueError):
        gen(bars, benchmark="nope")
    with pytest.raises(ValueError):
        gen(bars, exit_et="09:30")


def test_runs_through_backtester(bars, risk_cfg):
    r = backtest.run(bars, gen(bars), risk_cfg)
    assert len(r.trades) > 0 and "outside_hours" not in r.rejections
    assert set(r.trades.reason) <= {"time_exit", "stop", "end_of_data", "daily_stop", "daily_profit_stop"}
    assert (r.trades.reason == "time_exit").any()
    assert (r.trades.direction == 1).any() and (r.trades.direction == -1).any()


def test_three_tunable_params_match_params_yaml():
    import yaml
    y = yaml.safe_load((Path(__file__).resolve().parent.parent / "strategies/E_us_open_impulse/params.yaml").read_text(encoding="utf-8"))
    assert set(y["ranges"]) == set(y["default"]) == {"impulse_atr", "stop_atr", "exit_et"}
    assert all(UsOpenImpulse.default_params[k] == v for k, v in y["default"].items())
    assert np.prod([len(v) for v in y["ranges"].values()]) + 4 <= 50


# ---------------------------------------------------------------- the EA's own DST code, compiled from the .mq5
SHIM = r"""
#define _DEFAULT_SOURCE
#include <stdio.h>
#include <string.h>
#include <time.h>
typedef long long datetime_t;
#define datetime datetime_t
typedef struct { int year, mon, day, hour, min, sec, day_of_week, day_of_year; } MqlDateTime;
static void ZeroMemory_(MqlDateTime *t){ memset(t, 0, sizeof *t); }
#define ZeroMemory(t) ZeroMemory_(&(t))
static datetime StructToTime_(MqlDateTime *t){
  struct tm x; memset(&x, 0, sizeof x);
  x.tm_year=t->year-1900; x.tm_mon=t->mon-1; x.tm_mday=t->day; x.tm_hour=t->hour; x.tm_min=t->min; x.tm_sec=t->sec;
  return (datetime)timegm(&x); }
#define StructToTime(t) StructToTime_(&(t))
static void TimeToStruct_(datetime d, MqlDateTime *t){
  time_t s=(time_t)d; struct tm x; gmtime_r(&s,&x);
  t->year=x.tm_year+1900; t->mon=x.tm_mon+1; t->day=x.tm_mday; t->hour=x.tm_hour; t->min=x.tm_min; t->sec=x.tm_sec;
  t->day_of_week=x.tm_wday; t->day_of_year=x.tm_yday; }
#define TimeToStruct(d,t) TimeToStruct_(d,&(t))
%s
int main(void){ long long g; while(scanf("%%lld",&g)==1) printf("%%ld\n",(long)NyOffset(g)); return 0; }
"""


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_ea_dst_rule_matches_tz_database(tmp_path):
    block = re.search(r"PFM-DST-BEGIN.*?\n(.*)//--- PFM-DST-END", EA.read_text(encoding="utf-8"), re.S).group(1)
    src = tmp_path / "dst.c"
    src.write_text(SHIM % block, encoding="utf-8")
    exe = tmp_path / "dst"
    subprocess.run(["cc", "-w", "-x", "c", str(src), "-o", str(exe)], check=True)
    hours = pd.date_range("2019-01-01", "2031-01-01", freq="1h", tz="UTC")
    # plus the minutes either side of each change
    edges = [t for t in hours if t.month in (3, 11) and t.dayofweek == 6 and t.hour in (6, 7)]
    extra = [t + pd.Timedelta(seconds=d) for t in edges for d in (-1, 0, 1)]
    times = list(hours) + extra
    out = subprocess.run([str(exe)], input="\n".join(str(int(t.timestamp())) for t in times), capture_output=True,
                         text=True, check=True).stdout.split()
    tz = ZoneInfo(NY)
    want = [str(int(t.to_pydatetime().astimezone(tz).utcoffset().total_seconds())) for t in times]
    assert out == want


def test_ea_uses_risk_engine_and_visible_stop():
    src = EA.read_text(encoding="utf-8")
    assert "#include <PFM/RiskEngine.mqh>" in src
    assert 'Risk.Check(entry,stop,news,why)' in src and 'Risk.Open(dir,lots,stop,0.0,"PFM-E")' in src
    assert "InpMinHoldSeconds" in src
    for name in ("InpImpulseATR = 1.0", "InpStopATR    = 1.5", 'InpExitET     = "11:30"'):
        assert name in src
