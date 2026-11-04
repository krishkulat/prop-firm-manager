"""Risk engine — Python mirror of mql5/Include/PFM/RiskEngine.mqh.

Every order request goes through `RiskEngine.check()`. Any failed check returns ok=False (fail-safe).
Both implementations must give the same answer for the same inputs; tests/test_risk.py pins the behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time

import pandas as pd

IST = "Asia/Kolkata"
OZ_PER_LOT = 100.0          # XAUUSD: 1 lot = 100 oz → $1 move = $100 per lot
LOT_STEP = 0.01
MIN_LOT = 0.01


def _t(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


@dataclass
class Decision:
    ok: bool
    reason: str
    lots: float = 0.0
    risk_usd: float = 0.0


@dataclass
class AccountState:
    initial: float
    equity: float
    day_start_equity: float
    day_peak_equity: float | None = None
    trades_today: int = 0
    open_positions: int = 0
    open_risk_usd: float = 0.0
    day_closed_pnl: float = 0.0
    step_target_usd: float | None = None   # profit target of the current challenge step
    eod_hwm: float | None = None           # highest end-of-day equity so far (None = initial)
    killed: bool = False
    locked_for_day: bool = False


@dataclass
class RiskEngine:
    cfg: dict
    news_times_utc: list[pd.Timestamp] = field(default_factory=list)
    max_loss_trailing: bool = False         # firm product flag: kill and throttle follow the EOD high-water mark

    def __post_init__(self):
        c = self.cfg
        self.entry_start = _t(c["entry_start_ist"])
        self.entry_end = _t(c["entry_end_ist"])
        self.flat_by = _t(c["flat_by_ist"])

    # ---- reference level for kill and throttle -----------------------------------------------------
    def mark(self, st: AccountState) -> float:
        """Initial balance, or the EOD high-water mark when max loss trails (Q-003). Never below initial."""
        return max(st.initial, st.eod_hwm or st.initial) if self.max_loss_trailing else st.initial

    @staticmethod
    def close_day(st: AccountState) -> None:
        """Call at each day roll, before day_start_equity moves, with st.equity at the day's end."""
        st.eod_hwm = max(st.eod_hwm or st.initial, st.equity)

    # ---- sizing --------------------------------------------------------------------------------
    def risk_pct(self, st: AccountState) -> float:
        dd = (self.mark(st) - st.equity) / st.initial * 100
        return self.cfg["throttle_risk_pct"] if dd >= self.cfg["throttle_dd_pct"] else self.cfg["risk_per_trade_pct"]

    @staticmethod
    def lots_for(risk_usd: float, stop_distance: float) -> float:
        if stop_distance <= 0:
            return 0.0
        raw = risk_usd / (stop_distance * OZ_PER_LOT)
        lots = int(raw / LOT_STEP + 1e-9) * LOT_STEP   # round DOWN
        return round(lots, 2) if lots >= MIN_LOT else 0.0

    # ---- limits that act on the whole account ----------------------------------------------------
    def update_limits(self, st: AccountState) -> str | None:
        """Call on every price update. Returns an action string if the account must be flattened."""
        c = self.cfg
        dd_pct = (self.mark(st) - st.equity) / st.initial * 100
        if dd_pct >= c["kill_dd_pct"]:
            st.killed = True
            return "kill"
        day_base = max(st.day_start_equity, st.day_peak_equity or st.day_start_equity)
        if (day_base - st.equity) / st.initial * 100 >= c["daily_stop_pct"]:
            st.locked_for_day = True
            return "daily_stop"
        if (st.equity - st.day_start_equity) / st.initial * 100 >= c["daily_profit_stop_pct"]:
            st.locked_for_day = True
            return "daily_profit_stop"
        if st.step_target_usd and (st.equity - st.day_start_equity) >= c["max_day_share_of_target"] * st.step_target_usd:
            st.locked_for_day = True
            return "day_share_cap"
        return None

    def in_news_blackout(self, now_utc: pd.Timestamp) -> bool:
        before = pd.Timedelta(minutes=self.cfg["news_flat_before_min"])
        after = pd.Timedelta(minutes=self.cfg["news_resume_after_min"])
        return any(n - before <= now_utc <= n + after for n in self.news_times_utc)

    def must_be_flat(self, now_utc: pd.Timestamp) -> bool:
        ist = now_utc.tz_convert(IST)
        if ist.time() >= self.flat_by:
            return True
        # flat before the weekend: Friday after flat_by handled above; Saturday/Sunday always flat
        return ist.dayofweek >= 5

    # ---- per-order gate --------------------------------------------------------------------------
    def check(self, st: AccountState, now_utc: pd.Timestamp, entry: float, stop: float,
              spread_points: float, spread_median_points: float, feed_age_s: float = 0.0,
              has_stop: bool = True) -> Decision:
        c = self.cfg
        if st.killed:
            return Decision(False, "killed")
        if st.locked_for_day:
            return Decision(False, "locked_for_day")
        if not has_stop or stop is None:
            return Decision(False, "no_stop")
        if feed_age_s > c["stale_feed_seconds"]:
            return Decision(False, "stale_feed")
        ist = now_utc.tz_convert(IST)
        if ist.dayofweek >= 5 or not (self.entry_start <= ist.time() < self.entry_end):
            return Decision(False, "outside_hours")
        if self.in_news_blackout(now_utc):
            return Decision(False, "news_blackout")
        if st.trades_today >= c["max_trades_per_day"]:
            return Decision(False, "max_trades")
        if st.open_positions >= c["max_open_positions"]:
            return Decision(False, "max_positions")
        if spread_median_points > 0 and spread_points > c["spread_max_ratio"] * spread_median_points:
            return Decision(False, "spread")
        risk_usd = st.initial * self.risk_pct(st) / 100
        if st.open_risk_usd + risk_usd > st.initial * c["max_open_risk_pct"] / 100 + 1e-9:
            return Decision(False, "max_open_risk")
        # a new loss must not be able to push the account through the daily stop or the kill level
        day_room = st.initial * c["daily_stop_pct"] / 100 - (st.day_start_equity - st.equity) - st.open_risk_usd
        kill_room = st.initial * c["kill_dd_pct"] / 100 - (self.mark(st) - st.equity) - st.open_risk_usd
        risk_usd = min(risk_usd, day_room, kill_room)
        lots = self.lots_for(risk_usd, abs(entry - stop))
        if lots <= 0:
            return Decision(False, "size_zero")
        return Decision(True, "ok", lots, lots * abs(entry - stop) * OZ_PER_LOT)
