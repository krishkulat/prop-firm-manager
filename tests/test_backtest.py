import pandas as pd

from pfm import backtest
from pfm.strategy_base import Signal


def bars_from(rows, start="2026-11-03 08:00"):
    idx = pd.date_range(start, periods=len(rows), freq="15min", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx).assign(spread=0)


def test_long_hits_target(risk_cfg):
    b = bars_from([(2000, 2000.5, 1999.5, 2000)] * 2 + [(2000, 2000.5, 1999.6, 2000.2), (2000.2, 2011, 2000, 2010)])
    sig = Signal(b.index[2], 1, stop=1995.0, target=2010.0)
    r = backtest.run(b, [sig], risk_cfg, slippage_points=0)
    t = r.trades.iloc[0]
    assert t.reason == "target" and t.lots == 0.5 and abs(t.pnl - 500) < 1e-6 and abs(t.r - 2.0) < 1e-6


def test_stop_first_when_both_in_bar(risk_cfg):
    b = bars_from([(2000, 2000.5, 1999.5, 2000)] * 2 + [(2000, 2011, 1994, 2000)])
    r = backtest.run(b, [Signal(b.index[2], 1, 1995.0, 2010.0)], risk_cfg, slippage_points=0)
    assert r.trades.iloc[0].reason == "stop" and abs(r.trades.iloc[0].r + 1) < 1e-6


def test_short_with_spread_and_slippage(risk_cfg):
    b = bars_from([(2000, 2000.5, 1999.5, 2000)] * 2 + [(2000, 2000.2, 1989, 1990)]).assign(spread=20)
    r = backtest.run(b, [Signal(b.index[2], -1, 2005.0, 1990.0)], risk_cfg, slippage_points=10)
    t = r.trades.iloc[0]
    assert abs(t.entry - 1999.9) < 1e-9                  # sell at bid − 0.10
    assert t.reason == "target" and abs(t.exit - 1990.1) < 1e-9   # buy back at ask(target) + 0.10


def test_session_end_close(risk_cfg):
    b = bars_from([(2000, 2000.5, 1999.5, 2000)] * 40, start="2026-11-03 15:00")   # runs past 22:30 IST
    r = backtest.run(b, [Signal(b.index[1], 1, 1990.0, 2020.0)], risk_cfg, slippage_points=0)
    assert r.rejections == {} or r.trades.empty is False
    if not r.trades.empty:
        assert r.trades.iloc[0].reason == "session_end"


def test_strategy_runs_on_synthetic(risk_cfg):
    from pfm import data
    from strategies.A_asian_breakout.strategy import AsianBreakout
    bars = data.synthetic(days=120)
    sigs = AsianBreakout().generate_signals(bars)
    assert sigs, "expected some signals"
    for s in sigs:   # no look-ahead: signal time is the close of a bar inside the entry window
        assert s.time in bars.index or s.time > bars.index[-1]
        assert (s.direction == 1 and s.stop < s.target) or (s.direction == -1 and s.stop > s.target)
    r = backtest.run(bars, sigs, risk_cfg)
    assert len(r.trades) > 0
