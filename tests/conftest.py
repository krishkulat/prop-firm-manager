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
