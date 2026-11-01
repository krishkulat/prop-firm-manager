import pandas as pd

from pfm.risk import AccountState, RiskEngine

T_OK = pd.Timestamp("2026-11-03 09:00", tz="UTC")       # 14:30 IST Tuesday


def st(eq=50000, day_start=None, **kw):
    return AccountState(initial=50000, equity=eq, day_start_equity=day_start or eq, **kw)


def test_sizing_half_percent(risk_cfg):
    d = RiskEngine(risk_cfg).check(st(), T_OK, entry=2000.0, stop=1995.0, spread_points=25, spread_median_points=25)
    assert d.ok and d.lots == 0.5 and abs(d.risk_usd - 250) < 1e-6     # $250 / ($5 × 100 oz)


def test_rounds_down(risk_cfg):
    d = RiskEngine(risk_cfg).check(st(), T_OK, 2000.0, 1993.0, 25, 25)
    assert d.lots == 0.35                                               # 250/700 = 0.357 → 0.35


def test_throttle_after_3pct_dd(risk_cfg):
    d = RiskEngine(risk_cfg).check(st(eq=48400), T_OK, 2000.0, 1995.0, 25, 25)
    assert d.ok and d.lots == 0.25


def test_rejections(risk_cfg):
    e = RiskEngine(risk_cfg)
    assert e.check(st(), pd.Timestamp("2026-11-03 04:00", tz="UTC"), 2000, 1995, 25, 25).reason == "outside_hours"
    assert e.check(st(), pd.Timestamp("2026-11-07 09:00", tz="UTC"), 2000, 1995, 25, 25).reason == "outside_hours"  # Saturday
    assert e.check(st(trades_today=3), T_OK, 2000, 1995, 25, 25).reason == "max_trades"
    assert e.check(st(), T_OK, 2000, 1995, 60, 25).reason == "spread"
    assert e.check(st(), T_OK, 2000, None, 25, 25, has_stop=False).reason == "no_stop"
    assert e.check(st(), T_OK, 2000, 1995, 25, 25, feed_age_s=99).reason == "stale_feed"
    assert e.check(st(open_positions=2), T_OK, 2000, 1995, 25, 25).reason == "max_positions"
    assert e.check(st(open_risk_usd=400), T_OK, 2000, 1995, 25, 25).reason == "max_open_risk"


def test_news_blackout(risk_cfg):
    e = RiskEngine(risk_cfg, [pd.Timestamp("2026-11-03 09:05", tz="UTC")])
    assert e.check(st(), T_OK, 2000, 1995, 25, 25).reason == "news_blackout"
    assert e.check(st(), pd.Timestamp("2026-11-03 09:30", tz="UTC"), 2000, 1995, 25, 25).ok


def test_risk_capped_by_daily_room(risk_cfg):
    # down $600 today (1.2%); daily stop 1.5% = $750 → only $150 of room
    d = RiskEngine(risk_cfg).check(st(eq=49400, day_start=50000), T_OK, 2000, 1995, 25, 25)
    assert d.ok and d.risk_usd <= 150 + 1e-6


def test_daily_stop_and_kill(risk_cfg):
    e = RiskEngine(risk_cfg)
    s = st(eq=49240, day_start=50000)
    assert e.update_limits(s) == "daily_stop" and s.locked_for_day
    assert e.check(s, T_OK, 2000, 1995, 25, 25).reason == "locked_for_day"
    k = st(eq=47000, day_start=47000)
    assert e.update_limits(k) == "kill" and e.check(k, T_OK, 2000, 1995, 25, 25).reason == "killed"


def test_profit_stop(risk_cfg):
    s = st(eq=50760, day_start=50000)
    assert RiskEngine(risk_cfg).update_limits(s) == "daily_profit_stop"


def test_must_be_flat(risk_cfg):
    e = RiskEngine(risk_cfg)
    assert e.must_be_flat(pd.Timestamp("2026-11-03 17:05", tz="UTC"))      # 22:35 IST
    assert not e.must_be_flat(T_OK)
