"""Bar-based backtester with the risk engine in the loop.

Conventions
- Bars are indexed by OPEN time (UTC), prices are BID; spread column in points (0.01 USD/oz).
- Signals are produced at a bar close and filled at the next bar's open (= index equal to signal.time).
- Longs buy at ask (bid + spread) + slippage; shorts sell at bid − slippage. Exits pay the other side.
- If stop and target are both inside one bar, the stop is assumed hit first (conservative).
- Account limits are checked on each bar's worst price for open positions (conservative).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd

from .risk import IST, OZ_PER_LOT, AccountState, RiskEngine
from .strategy_base import Signal

POINT = 0.01


@dataclass
class Position:
    entry_time: pd.Timestamp
    direction: int
    entry: float
    stop: float
    target: float
    lots: float
    risk_usd: float
    worst_price: float


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: int
    entry: float
    exit: float
    lots: float
    pnl: float
    risk_usd: float
    r: float
    mae_r: float
    reason: str


@dataclass
class Result:
    trades: pd.DataFrame
    daily: pd.DataFrame          # IST date, equity at close, day low equity
    rejections: dict
    initial: float

    def to_dict(self):
        return {"trades": len(self.trades), "rejections": self.rejections}


def run(bars: pd.DataFrame, signals: list[Signal], risk_cfg: dict, initial: float | None = None,
        slippage_points: float = 30, news_times_utc: list | None = None,
        step_target_pct: float | None = None) -> Result:
    initial = initial or risk_cfg["account_size"]
    eng = RiskEngine(risk_cfg, news_times_utc or [])
    st = AccountState(initial=initial, equity=initial, day_start_equity=initial)
    if step_target_pct:
        st.step_target_usd = initial * step_target_pct / 100
    slip = slippage_points * POINT
    sig_at = {s.time: s for s in signals}
    spread_med = bars["spread"].rolling(20 * 96, min_periods=96).median().bfill()

    positions: list[Position] = []
    trades: list[Trade] = []
    rejections: dict[str, int] = {}
    daily_rows = []
    balance = initial
    cur_day = None
    day_low = initial

    def close(pos: Position, ts, bid_exit: float, spread_pts: float, reason: str):
        nonlocal balance
        px = bid_exit - slip if pos.direction == 1 else bid_exit + spread_pts * POINT + slip
        pnl = (px - pos.entry) * pos.direction * pos.lots * OZ_PER_LOT
        balance += pnl
        mae = (pos.entry - pos.worst_price) * pos.direction * pos.lots * OZ_PER_LOT
        trades.append(Trade(pos.entry_time, ts, pos.direction, pos.entry, px, pos.lots, pnl, pos.risk_usd,
                            pnl / pos.risk_usd if pos.risk_usd else 0.0,
                            max(mae, 0) / pos.risk_usd if pos.risk_usd else 0.0, reason))
        st.open_positions -= 1
        st.open_risk_usd -= pos.risk_usd
        st.day_closed_pnl += pnl

    for ts, bar in bars.iterrows():
        sp = bar["spread"]
        day = ts.tz_convert(IST).date()
        if day != cur_day:
            if cur_day is not None:
                daily_rows.append({"date": cur_day, "equity": st.equity, "low": day_low})
            cur_day = day
            st.day_start_equity = st.equity
            st.day_peak_equity = st.equity
            st.trades_today = 0
            st.locked_for_day = False
            st.day_closed_pnl = 0.0
            day_low = st.equity

        # 1) forced flat (session end / weekend) at the open of this bar
        if positions and eng.must_be_flat(ts):
            for p in list(positions):
                close(p, ts, bar["open"], sp, "session_end")
                positions.remove(p)

        # 2) new entry at this bar's open (before intrabar moves, so the entry bar's range is checked too)
        s = sig_at.get(ts)
        if s is not None:
            entry = bar["open"] + sp * POINT + slip if s.direction == 1 else bar["open"] - slip
            bad_geometry = (s.direction == 1 and not (s.stop < entry < s.target)) or \
                           (s.direction == -1 and not (s.target < entry < s.stop))
            if bad_geometry:
                rejections["gap_through_levels"] = rejections.get("gap_through_levels", 0) + 1
            else:
                dec = eng.check(st, ts, entry, s.stop, sp, spread_med.loc[ts])
                if dec.ok:
                    positions.append(Position(ts, s.direction, entry, s.stop, s.target, dec.lots, dec.risk_usd, entry))
                    st.open_positions += 1
                    st.open_risk_usd += dec.risk_usd
                    st.trades_today += 1
                else:
                    rejections[dec.reason] = rejections.get(dec.reason, 0) + 1
        # 3) stops / targets inside this bar
        for p in list(positions):
            if p.direction == 1:
                p.worst_price = min(p.worst_price, bar["low"])
                if bar["low"] <= p.stop:
                    close(p, ts, min(p.stop, bar["open"]), sp, "stop"); positions.remove(p); continue
                if bar["high"] >= p.target:
                    close(p, ts, p.target, sp, "target"); positions.remove(p); continue
            else:
                ask_hi, ask_lo = bar["high"] + sp * POINT, bar["low"] + sp * POINT
                p.worst_price = max(p.worst_price, ask_hi)
                if ask_hi >= p.stop:
                    close(p, ts, max(p.stop, bar["open"] + sp * POINT) - sp * POINT, sp, "stop"); positions.remove(p); continue
                if ask_lo <= p.target:
                    close(p, ts, p.target - sp * POINT, sp, "target"); positions.remove(p); continue

        # 4) account limits on the worst price of the bar
        def mtm(use_worst: bool) -> float:
            eq = balance
            for p in positions:
                px = (bar["low"] if p.direction == 1 else bar["high"] + sp * POINT) if use_worst else \
                     (bar["close"] if p.direction == 1 else bar["close"] + sp * POINT)
                eq += (px - p.entry) * p.direction * p.lots * OZ_PER_LOT
            return eq

        st.equity = mtm(True)
        day_low = min(day_low, st.equity)
        action = eng.update_limits(st)
        if action in ("kill", "daily_stop") and positions:
            for p in list(positions):
                worst = bar["low"] if p.direction == 1 else bar["high"]
                close(p, ts, worst, sp, action); positions.remove(p)
        st.equity = mtm(False) if positions else balance
        if action in ("daily_profit_stop", "day_share_cap") and positions:
            for p in list(positions):
                close(p, ts, bar["close"], sp, action); positions.remove(p)
            st.equity = balance

        if st.killed:
            break

    if positions:
        last_ts, last = bars.index[-1], bars.iloc[-1]
        for p in positions:
            close(p, last_ts, last["close"], last["spread"], "end_of_data")
    st.equity = balance
    if cur_day is not None:
        daily_rows.append({"date": cur_day, "equity": st.equity, "low": min(day_low, st.equity)})
    tdf = pd.DataFrame([asdict(t) for t in trades])
    return Result(tdf, pd.DataFrame(daily_rows), rejections, initial)
