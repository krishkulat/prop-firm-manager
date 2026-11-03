"""R-011: repo news calendar fallback, and the backtest flattening before news like the EA."""
import shutil
from pathlib import Path

import pandas as pd

from pfm import backtest, data, worker
from pfm.strategy_base import Signal

REPO_CALENDAR = Path(worker.__file__).resolve().parent.parent / "research/news/usd_high_impact.csv"


def flat_bars(n=30, start="2026-11-03 10:00"):
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open": 2000.0, "high": 2000.5, "low": 1999.5, "close": 2000.0, "spread": 0.0}, index=idx)


def ts(s):
    return pd.Timestamp(s, tz="UTC")


# ---------------------------------------------------------------- load_news
def test_load_news_falls_back_to_repo_calendar(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    assert worker.load_news() == []
    (tmp_path / "research/news").mkdir(parents=True)
    shutil.copy(REPO_CALENDAR, tmp_path / "research/news/usd_high_impact.csv")
    news = worker.load_news()
    assert len(news) == 251 and news[0] == ts("2019-01-04 13:30") and str(news[0].tz) == "UTC"


def test_data_news_csv_wins_over_repo_calendar(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    (tmp_path / "research/news").mkdir(parents=True)
    shutil.copy(REPO_CALENDAR, tmp_path / "research/news/usd_high_impact.csv")
    (tmp_path / "data").mkdir()
    (tmp_path / "data/news.csv").write_text("time\n2026-01-01T12:00:00Z\n", encoding="utf-8")
    assert worker.load_news() == [ts("2026-01-01 12:00")]


# ---------------------------------------------------------------- flatten before news
def test_closes_at_open_of_last_bar_at_or_before_cutoff(risk_cfg):
    b = flat_bars().assign(open=2001.0)
    r = backtest.run(b, [Signal(ts("2026-11-03 11:00"), 1, 1990.0, 2020.0)], risk_cfg, slippage_points=0,
                     news_times_utc=[ts("2026-11-03 12:30")])        # cutoff 12:20 → 12:15 bar
    t = r.trades.iloc[0]
    assert t.reason == "news" and t.exit_time == ts("2026-11-03 12:15") and t.exit == 2001.0


def test_cutoff_exactly_on_a_bar_open_uses_that_bar(risk_cfg):
    r = backtest.run(flat_bars(), [Signal(ts("2026-11-03 11:00"), 1, 1990.0, 2020.0)], risk_cfg, slippage_points=0,
                     news_times_utc=[ts("2026-11-03 12:25")])        # cutoff 12:15
    assert r.trades.iloc[0].exit_time == ts("2026-11-03 12:15")


def test_short_closes_on_news_at_ask(risk_cfg):
    b = flat_bars().assign(spread=20.0)
    r = backtest.run(b, [Signal(ts("2026-11-03 11:00"), -1, 2010.0, 1980.0)], risk_cfg, slippage_points=0,
                     news_times_utc=[ts("2026-11-03 12:30")])
    t = r.trades.iloc[0]
    assert t.reason == "news" and abs(t.exit - 2000.2) < 1e-9


def test_no_entry_on_the_flatten_bar_or_inside_the_blackout(risk_cfg):
    news = [ts("2026-11-03 12:30")]
    for t0 in ("12:15", "12:30", "12:45"):                           # flatten bar; blackout runs to 12:45
        r = backtest.run(flat_bars(), [Signal(ts(f"2026-11-03 {t0}"), 1, 1990.0, 2020.0)], risk_cfg,
                         slippage_points=0, news_times_utc=news)
        assert r.trades.empty and r.rejections == {"news_blackout": 1}
    r = backtest.run(flat_bars(), [Signal(ts("2026-11-03 13:00"), 1, 1990.0, 2020.0)], risk_cfg,
                     slippage_points=0, news_times_utc=news)
    assert len(r.trades) == 1 and r.trades.iloc[0].reason != "news"


def test_no_position_held_through_any_event(risk_cfg):
    from strategies.C_sge_session_long.strategy import SgeSessionLong
    bars = data.synthetic(days=200)
    cfg = {**risk_cfg, "entry_start_ist": "06:00"}
    days = pd.date_range(bars.index[0].normalize(), bars.index[-1].normalize(), freq="B")
    news = [d + pd.Timedelta(hours=4) for d in days]                 # inside C's 01:00-07:30 UTC hold
    t = backtest.run(bars, SgeSessionLong().generate_signals(bars, {"benchmark": "no_filter"}), cfg,
                     news_times_utc=news).trades
    assert (t.reason == "news").any()
    for n in news:
        assert not ((t.entry_time <= n) & (t.exit_time > n)).any()


def test_events_outside_the_data_change_nothing(risk_cfg):
    b = flat_bars()
    sig = [Signal(ts("2026-11-03 11:00"), 1, 1990.0, 2020.0)]
    base = backtest.run(b, sig, risk_cfg, slippage_points=0)
    r = backtest.run(b, sig, risk_cfg, slippage_points=0,
                     news_times_utc=[ts("2020-01-01 12:00"), ts("2030-01-01 12:00")])
    pd.testing.assert_frame_equal(base.trades, r.trades)


def test_empty_calendar_is_identical_to_before_r011(risk_cfg):
    from strategies.B_london_fade.strategy import LondonFade
    bars = data.synthetic(days=200)
    sigs = LondonFade().generate_signals(bars)
    for news in (None, []):
        r = backtest.run(bars, sigs, risk_cfg, news_times_utc=news)
        # 66 trades and this P&L were recorded from main at 64752e4, before the change
        assert len(r.trades) == 66 and round(r.trades.pnl.sum(), 6) == -2299.656753 and r.rejections == {}
        assert "news" not in set(r.trades.reason)
