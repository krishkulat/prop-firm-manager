import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def risk_cfg():
    from pfm import config
    return config.risk_profile("the5ers_hs50k_10d")


@pytest.fixture
def product():
    from pfm import config
    return config.firm_product("the5ers/hs50k_10d")


class LondonFadeV10:
    """B v1.0 (fade, target 2R), kept only so the figures pinned before R-019 keep testing the backtester and worker."""
    name = "B"
    default_params = {"stop_atr": 1.2, "min_range_atr": 1.5, "max_range_atr": 4.0}

    def generate_signals(self, bars, params=None):
        from pfm.strategy_base import Signal
        from strategies.A_asian_breakout.strategy import breakout_events
        p = {**self.default_params, **(params or {})}
        return [Signal(e.signal_time, -e.direction, e.close + e.direction * e.risk, e.close - e.direction * 2.0 * e.risk, "B")
                for e in breakout_events(bars, p)]


@pytest.fixture
def b_v10():
    return LondonFadeV10()
