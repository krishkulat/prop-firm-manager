"""Strategy G (H-007): hand-built days for each rule, clocks, no look-ahead, benchmarks, worker."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from pfm import backtest, data, worker
from pfm.strategy_base import h1_atr_on
from strategies.G_prior_day_failed_break import strategy as G
from strategies.G_prior_day_failed_break.strategy import PriorDayFailedBreak

ROOT = Path(__file__).resolve().parent.parent
IST, NY = "Asia/Kolkata", "America/New_York"
DAY = "2026-06-17"                       # a Wednesday with no NFP or CPI


@pytest.fixture(scope="module")
def bars():
    return data.synthetic(days=400, start="2026-01-05")   # spans both 2026 DST changes


def gen(b, **p):
    return PriorDayFailedBreak().generate_signals(b, p)


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def flat():
    """2000 ± 1 every bar, so PDH 2001, PDL 1999, ATR 2, break margin 0.2, and nothing trades beyond a level."""
    idx = pd.date_range("2026-06-09 00:00", "2026-06-18 23:45", freq="15min", tz="UTC")
    return pd.DataFrame({"open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.0, "spread": 25}, index=idx)


def bar(b, at, **v):
    for k, x in v.items():
        b.loc[ts(f"{DAY} {at}"), k] = x
    return b


def test_sell_after_pdh_is_broken_and_reclaimed():
    b = bar(flat(), "10:00", high=2002.0, close=2000.5)
    s = gen(b)
    assert len(s) == 1 and s[0].time == ts(f"{DAY} 10:15") and s[0].direction == -1
    a = pd.Series(h1_atr_on(b).values, index=b.index).loc[s[0].time]
    assert s[0].stop == pytest.approx(2000 + 1.25 * a) and s[0].target == pytest.approx(2000 - 2.5 * a)
    assert s[0].exit_time == ts(f"{DAY} 16:30")


def test_buy_after_pdl_is_broken_and_reclaimed():
    s = gen(bar(flat(), "10:00", low=1998.0, close=1999.5))
    assert len(s) == 1 and s[0].time == ts(f"{DAY} 10:15") and s[0].direction == 1 and s[0].stop < 2000 < s[0].target


@pytest.mark.parametrize("n, reclaim_at, entry", [(1, None, None), (2, "10:15", "10:30"), (4, "10:15", "10:30"),
                                                  (2, "10:30", None), (4, "10:45", "11:00"), (4, "11:00", None)])
def test_reclaim_counts_the_break_bar(n, reclaim_at, entry):
    b = bar(flat(), "10:00", high=2002.0, close=2001.5)                    # break bar closes beyond the level
    for t in ("10:15", "10:30", "10:45", "11:00"):
        bar(b, t, high=2001.6, close=2001.5)
    if reclaim_at:
        bar(b, reclaim_at, close=2000.5)
    assert [x.time for x in gen(b, reclaim_bars=n)] == ([ts(f"{DAY} {entry}")] if entry else [])


@pytest.mark.parametrize("at", ["2026-06-16 22:00", "2026-06-17 03:00", "2026-06-17 07:45"])
def test_level_taken_since_the_prior_day_ended_is_dead(at):
    b = bar(flat(), "10:00", high=2002.0, close=2000.5)
    b.loc[ts(at), "high"] = 2001.01                                        # Asia included, a tick is enough
    assert gen(b) == []


def test_level_traded_inside_the_prior_day_is_the_level_itself():
    b = bar(flat(), "10:00", high=2002.5, close=2000.5)
    b.loc[ts("2026-06-16 20:00"), "high"] = 2002.0                         # before 17:00 New York: sets PDH to 2002
    assert [x.direction for x in gen(b)] == [-1]
    b.loc[ts(f"{DAY} 10:00"), "high"] = 2002.0                             # now equal to PDH: not beyond it
    assert gen(b) == []


def test_break_needs_the_margin_and_a_smaller_poke_kills_the_level():
    assert len(gen(bar(flat(), "10:00", high=2001.21, close=2000.5))) == 1
    b = bar(flat(), "10:00", high=2001.1, close=2000.5)
    assert gen(b) == []
    bar(b, "11:00", high=2003.0, close=2000.5)                             # a real break later: the level is already gone
    assert gen(b) == []


@pytest.mark.parametrize("at, ok", [("07:45", False), ("08:00", True), ("15:00", True), ("15:15", False)])
def test_break_window_utc(at, ok):
    s = gen(bar(flat(), at, high=2002.0, close=2000.5), reclaim_bars=1)
    assert bool(s) is ok


def test_last_entry_is_1515_utc():
    assert gen(bar(flat(), "15:00", high=2002.0, close=2000.5))[0].time == ts(f"{DAY} 15:15")
    b = bar(flat(), "15:00", high=2002.0, close=2001.5)
    bar(b, "15:15", close=2000.5)                                          # reclaim in time, but the entry would be 15:30
    assert gen(b) == []


def test_one_trade_a_day_first_signal_only():
    b = bar(flat(), "10:00", high=2002.0, close=2000.5)
    bar(b, "12:00", low=1998.0, close=1999.5)
    assert [(x.time, x.direction) for x in gen(b)] == [(ts(f"{DAY} 10:15"), -1)]
    b = bar(flat(), "10:00", low=1998.0, close=1999.5)
    bar(b, "10:00", high=2002.0, close=2000.5)                             # both levels on one bar: order unknown
    sigs, skips = G.scan(b)
    assert sigs == [] and skips["both_levels_same_entry"] == 1


def test_extreme_beyond_the_stop_skips_and_the_other_level_may_still_trade():
    b = bar(flat(), "10:00", high=2010.0, close=2000.5)
    sigs, skips = G.scan(b)
    assert sigs == [] and skips["extreme_beyond_stop"] == 1
    bar(b, "12:00", low=1998.0, close=1999.5)
    sigs, skips = G.scan(b)
    assert [x.direction for x in sigs] == [1] and skips["extreme_beyond_stop"] == 1


def test_extreme_covers_the_bars_up_to_the_reclaim():
    b = bar(flat(), "10:00", high=2002.0, close=2001.5)
    bar(b, "10:15", high=2010.0, close=2000.5)
    sigs, skips = G.scan(b)
    assert sigs == [] and skips["extreme_beyond_stop"] == 1


@pytest.mark.parametrize("at, ok", [("13:15", True), ("13:30", False), ("14:30", False), ("14:45", True)])
def test_break_within_60_min_after_nfp_or_cpi_is_ignored(monkeypatch, at, ok):
    monkeypatch.setattr(G, "release_times", lambda: pd.DatetimeIndex([ts(f"{DAY} 13:30")]))
    b = bar(flat(), at, high=2002.0, close=2000.5)
    bar(b, "15:00", high=2003.0, close=2000.5)                             # an ignored break still kills the level
    assert [x.time for x in gen(b, reclaim_bars=1)] == ([ts(f"{DAY} {at}") + pd.Timedelta(minutes=15)] if ok else [])


def test_calendar_gives_nfp_and_cpi_only():
    t = G.release_times()
    assert len(t) == 186 and t.is_monotonic_increasing                     # 93 + 93 of the 251 rows
    assert ts("2019-01-04 13:30") in t and ts("2019-01-30 19:00") not in t  # NFP in, FOMC out


# ---------------------------------------------------------------- clocks
@pytest.mark.parametrize("utc, day", [
    ("2026-03-05 21:45", "2026-03-05"), ("2026-03-05 22:00", "2026-03-06"),     # EST: 17:00 New York = 22:00 UTC
    ("2026-03-09 20:45", "2026-03-09"), ("2026-03-09 21:00", "2026-03-10"),     # EDT after Sunday 2026-03-08
    ("2026-10-29 20:45", "2026-10-29"), ("2026-10-29 21:00", "2026-10-30"),     # EDT
    ("2026-11-02 21:45", "2026-11-02"), ("2026-11-02 22:00", "2026-11-03"),     # EST after Sunday 2026-11-01
])
def test_day_boundary_across_dst(utc, day):
    assert pd.Timestamp(G.trading_day(pd.DatetimeIndex([ts(utc)]))[0]) == pd.Timestamp(day)


@pytest.mark.parametrize("last_in, first_after", [("2026-03-05 21:45", "2026-03-05 22:00"),
                                                  ("2026-03-09 20:45", "2026-03-09 21:00"),
                                                  ("2026-10-29 20:45", "2026-10-29 21:00"),
                                                  ("2026-11-02 21:45", "2026-11-02 22:00")])
def test_levels_end_at_17_new_york_on_both_sides_of_dst(last_in, first_after):
    idx = pd.date_range(ts(last_in) - pd.Timedelta(days=3), ts(last_in) + pd.Timedelta(days=2), freq="15min", tz="UTC")
    idx = idx[idx.dayofweek < 5]
    base = pd.DataFrame({"open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.0, "spread": 25}, index=idx)
    next_day = (ts(first_after) + pd.Timedelta(days=1)).normalize() + pd.Timedelta(hours=10)
    base.loc[next_day, ["high", "close"]] = 2002.5, 2000.5
    b = base.copy()
    b.loc[ts(last_in), "high"] = 2002.0                                    # last bar of the day: PDH is 2002, 2002.5 breaks it
    assert [x.direction for x in gen(b)] == [-1]
    b = base.copy()
    b.loc[ts(first_after), "high"] = 2002.0                                # first bar of the next day: PDH 2001, already taken
    assert gen(b) == []


def test_exit_and_entries_stay_fixed_utc_inside_the_risk_window(bars, risk_cfg):
    sigs = gen(bars)
    assert sigs
    flat_by = pd.Timestamp(risk_cfg["flat_by_ist"]).time()
    for s in sigs:
        assert s.exit_time.strftime("%H:%M") == "16:30" and s.exit_time.tz_convert(IST).strftime("%H:%M") == "22:00"
        assert s.exit_time.tz_convert(IST).time() < flat_by
        assert s.exit_time.date() == s.time.date() and s.time.dayofweek < 5
        assert "08:15" <= s.time.strftime("%H:%M") <= "15:15"
        assert risk_cfg["entry_start_ist"] <= s.time.tz_convert(IST).strftime("%H:%M") <= risk_cfg["entry_end_ist"]


def test_1630_exit_beats_flat_by_in_the_backtest(bars, risk_cfg):
    r = backtest.run(bars, gen(bars, target_r=2.5), risk_cfg)
    assert "session_end" not in set(r.trades.reason)
    te = r.trades[r.trades.reason == "time_exit"]
    assert not te.empty and (pd.to_datetime(te.exit_time).dt.strftime("%H:%M") == "16:30").all()


def test_one_signal_per_new_york_day(bars):
    d = [str(pd.Timestamp(G.trading_day(pd.DatetimeIndex([s.time]))[0]).date()) for s in gen(bars)]
    assert len(set(d)) == len(d)


# ---------------------------------------------------------------- no look-ahead
@pytest.mark.parametrize("bench", G.BENCHMARKS)
def test_changing_the_entry_bar_and_later_leaves_earlier_signals_alone(bars, bench):
    sigs = gen(bars, benchmark=bench)
    k = lambda x: (x.time, x.direction, x.stop, x.target)
    for s in (sigs[len(sigs) // 3], sigs[len(sigs) // 2], sigs[-5]):
        later = bars.copy()
        later.loc[later.index >= s.time, ["open", "high", "low", "close"]] *= 1.5
        assert [k(x) for x in gen(later, benchmark=bench) if x.time < s.time] == [k(x) for x in sigs if x.time < s.time]


def test_only_the_open_is_read_from_the_entry_bar(bars):
    sigs = gen(bars)
    s = sigs[len(sigs) // 2]
    later = bars.copy()
    later.loc[s.time, ["high", "low", "close"]] *= 1.5
    later.loc[later.index > s.time, ["open", "high", "low", "close"]] *= 1.5
    k = lambda x: (x.time, x.direction, x.stop, x.target)
    assert [k(x) for x in gen(later) if x.time <= s.time] == [k(x) for x in sigs if x.time <= s.time]


def test_atr_is_the_last_h1_bar_closed_at_or_before_the_signal():
    b = bar(flat(), "10:00", high=2002.0, close=2000.5)
    s = gen(b)[0]                                                          # entry 10:15, last closed H1 bar closes 10:00
    changed = b.copy()
    changed.loc[ts(f"{DAY} 09:45"), "low"] = 1994.0                        # inside the H1 bar closing 10:00: must count
    assert gen(changed)[0].stop > s.stop
    changed = b.copy()
    changed.loc[ts(f"{DAY} 10:15"), "low"] = 1990.0                        # inside the H1 bar closing 11:00: must not
    assert gen(changed)[0].stop == s.stop


def test_prior_day_levels_come_only_from_completed_days():
    b = bar(flat(), "10:00", high=2002.0, close=2000.5)
    b.loc[ts(f"{DAY} 18:00"), "high"] = 2100.0                             # later the same day, same New York day
    assert [x.direction for x in gen(b)] == [-1]


# ---------------------------------------------------------------- benchmarks
def test_side_benchmarks_keep_entries_and_distances(bars):
    base = gen(bars)
    opp = gen(bars, benchmark="opposite_side")
    rnd = gen(bars, benchmark="random_side", benchmark_seed=1)
    assert [s.time for s in opp] == [s.time for s in rnd] == [s.time for s in base]
    assert [s.exit_time for s in rnd] == [s.exit_time for s in base]
    assert all(o.direction == -b.direction for o, b in zip(opp, base))
    for o, b in zip(opp, base):
        p = bars.at[b.time, "open"]
        assert abs(p - o.stop) == pytest.approx(abs(b.stop - p)) and abs(o.target - p) == pytest.approx(abs(b.target - p))
    assert {s.direction for s in rnd} == {1, -1}
    d = lambda seed: [s.direction for s in gen(bars, benchmark="random_side", benchmark_seed=seed)]
    assert d(1) == d(1) and d(0) != d(1) and d(1) != d(2)
    with pytest.raises(ValueError):
        gen(bars, benchmark="nope")
    with pytest.raises(ValueError):
        gen(bars, reclaim_bars=0)


def test_no_reclaim_enters_after_the_first_break_with_the_same_stop_and_target():
    b = bar(flat(), "10:00", high=2002.0, close=2001.5)                    # no close back inside on the break bar
    assert gen(b, reclaim_bars=1) == []
    s = gen(b, benchmark="no_reclaim", reclaim_bars=1)
    assert len(s) == 1 and s[0].time == ts(f"{DAY} 10:15") and s[0].direction == -1
    r = gen(bar(flat(), "10:00", high=2002.0, close=2000.5))[0]            # same bar, reclaimed: same distances
    assert s[0].stop == pytest.approx(r.stop) and s[0].target == pytest.approx(r.target)


def test_shifted_level_moves_out_by_a_quarter_of_the_prior_range():
    # prior range 2, so the levels are 2001.5 and 1998.5
    b = bar(flat(), "10:00", high=2001.4, close=2000.5)
    assert gen(b, benchmark="shifted_level") == []                         # beyond PDH, not beyond the moved level
    b = bar(flat(), "10:00", high=2001.8, close=2000.5)
    assert [x.direction for x in gen(b, benchmark="shifted_level")] == [-1]
    b = bar(flat(), "10:00", high=2001.8, close=2001.6)                    # closes beyond the moved level: no reclaim
    assert gen(b, benchmark="shifted_level", reclaim_bars=1) == []
    assert [x.direction for x in gen(bar(flat(), "10:00", low=1998.2, close=1999.5), benchmark="shifted_level")] == [1]
    b = bar(flat(), "10:00", high=2001.6, close=2000.5)                    # 0.1 beyond, under the 0.2 margin
    assert gen(b, benchmark="shifted_level") == []


# ---------------------------------------------------------------- plumbing
def test_runs_through_the_backtester_with_the_calendar(bars, risk_cfg):
    r = backtest.run(bars, gen(bars), risk_cfg, news_times_utc=worker.load_news())
    assert len(r.trades) > 0
    assert set(r.trades.reason) <= {"stop", "target", "time_exit", "news", "daily_stop", "kill", "daily_profit_stop", "day_share_cap"}


def test_worker_loads_it_from_the_registry_and_runs_a_job(tmp_path, monkeypatch):
    strat, reg = worker.load_strategy("G")
    assert isinstance(strat, PriorDayFailedBreak) and reg["module"] == "strategies.G_prior_day_failed_break.strategy"
    assert reg["hypothesis"].endswith("H-007-prior-day-extreme-failed-break-fade.md")
    monkeypatch.setattr(worker, "RESULTS", tmp_path)
    monkeypatch.setattr(worker, "TRIALS", tmp_path / "trials.csv")
    job = {"job_id": "J-TEST-G", "kind": "backtest", "strategy": "G", "hypothesis": "H-TEST", "requested_by": "test",
           "params": {"benchmark": "random_side", "benchmark_seed": 2}, "data": {"synthetic": True, "days": 600}}
    s = worker.run_job(job)
    assert s["trades"] > 0 and s["news_calendar_loaded"] and s["params"]["benchmark_seed"] == 2


def test_three_tunable_params_match_params_yaml():
    y = yaml.safe_load((ROOT / "strategies/G_prior_day_failed_break/params.yaml").read_text(encoding="utf-8"))
    d = PriorDayFailedBreak.default_params
    assert set(y["ranges"]) == set(y["default"]) == {"reclaim_bars", "stop_atr", "target_r"}
    assert all(d[k] == v for k, v in y["default"].items()) and all(y["default"][k] in y["ranges"][k] for k in y["default"])
    assert (d["reclaim_bars"], d["stop_atr"], d["target_r"]) == (2, 1.25, 2.0)      # H-007's defaults
    assert np.prod([len(v) for v in y["ranges"].values()]) <= 43                    # plus the 7 first runs = 50
    assert set(y["benchmark"]["benchmark"]) == set(G.BENCHMARKS)
