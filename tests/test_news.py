"""R-011: repo news calendar fallback, and the backtest flattening before news like the EA."""
import hashlib
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


def test_data_news_csv_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    (tmp_path / "research/news").mkdir(parents=True)
    shutil.copy(REPO_CALENDAR, tmp_path / "research/news/usd_high_impact.csv")
    (tmp_path / "data").mkdir()
    (tmp_path / "data/news.csv").write_text("time\n2026-01-01T12:00:00Z\n", encoding="utf-8")
    assert len(worker.load_news()) == 251
    (tmp_path / "research/news/usd_high_impact.csv").unlink()
    assert worker.load_news() == []                                  # no fallback to data/news.csv either


# ---------------------------------------------------------------- calendar identity in summary.json (R-015)
def test_calendar_info_identifies_the_file():
    i = worker.news_calendar_info(worker.load_news())
    assert i["news_calendar_path"] == "research/news/usd_high_impact.csv"
    assert i["news_calendar_events"] == 251
    assert i["news_calendar_last_event"].startswith("2026-10-28")
    assert i["news_calendar_sha256"] == hashlib.sha256(REPO_CALENDAR.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_calendar_hash_ignores_line_endings_but_not_content(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    f = tmp_path / "research/news/usd_high_impact.csv"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"time,event\n2026-01-01T12:00:00Z,CPI\n")
    lf = worker.news_calendar_info(worker.load_news())["news_calendar_sha256"]
    f.write_bytes(b"time,event\r\n2026-01-01T12:00:00Z,CPI\r\n")
    assert worker.news_calendar_info(worker.load_news())["news_calendar_sha256"] == lf
    f.write_bytes(b"time,event\n2026-01-02T12:00:00Z,CPI\n")
    assert worker.news_calendar_info(worker.load_news())["news_calendar_sha256"] != lf


def test_calendar_info_without_a_file(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    i = worker.news_calendar_info([])
    assert i["news_calendar_events"] == 0 and i["news_calendar_last_event"] is None and i["news_calendar_sha256"] is None


def test_covers_data_is_false_when_bars_run_past_the_last_event():
    news = [ts("2026-11-03 13:00")]
    assert worker.calendar_covers_data(news, flat_bars(n=4, start="2026-11-03 12:00"))    # ends 12:45
    assert worker.calendar_covers_data(news, flat_bars(n=5, start="2026-11-03 12:00"))    # last bar on the event
    assert not worker.calendar_covers_data(news, flat_bars(n=6, start="2026-11-03 12:00"))
    assert not worker.calendar_covers_data([], flat_bars())                               # no calendar covers nothing


def test_summary_carries_calendar_fields_and_trades_are_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "RESULTS", tmp_path)
    monkeypatch.setattr(worker, "TRIALS", tmp_path / "trials.csv")
    from tests.legacy_pre_r022 import LondonFadePreR022   # frozen input: these pins guard the worker, not B (R-022)
    real = worker.load_strategy
    monkeypatch.setattr(worker, "load_strategy", lambda key: (LondonFadePreR022(), real(key)[1]) if key == "B" else real(key))
    job = {"job_id": "J-TEST-015", "kind": "backtest", "strategy": "B", "hypothesis": "H-TEST",
           "requested_by": "test", "data": {"synthetic": True, "days": 600}}
    s = worker.run_job(job)
    assert s["news_calendar_loaded"] and s["news_calendar_events"] == 251 and len(s["news_calendar_sha256"]) == 64
    assert s["news_calendar_covers_data"] is True                    # synthetic research split ends 2023
    t = pd.read_csv(tmp_path / "J-TEST-015/trades.csv")
    # 75 trades and this P&L were recorded from main at 3f26e86, before R-015, with the same calendar file
    assert len(t) == 75 and round(t.pnl.sum(), 6) == -457.869933


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
    from tests.legacy_pre_r022 import LondonFadePreR022
    bars = data.synthetic(days=200)
    sigs = LondonFadePreR022().generate_signals(bars)     # frozen input: these pins guard the backtester, not B (R-022)
    for news in (None, []):
        r = backtest.run(bars, sigs, risk_cfg, news_times_utc=news)
        # 66 trades and this P&L were recorded from main at 64752e4, before the change
        assert len(r.trades) == 66 and round(r.trades.pnl.sum(), 6) == -2299.656753 and r.rejections == {}
        assert "news" not in set(r.trades.reason)
