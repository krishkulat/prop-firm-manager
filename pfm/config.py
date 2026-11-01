"""Config loaders."""
from __future__ import annotations

import yaml

from . import ROOT


def load_yaml(rel: str) -> dict:
    with open(ROOT / rel, encoding="utf-8") as f:
        return yaml.safe_load(f)


def business() -> dict:
    return load_yaml("config/business.yaml")


def risk_profile(name: str) -> dict:
    return load_yaml(f"config/risk/{name}.yaml")


def firm_product(key: str) -> dict:
    """key = 'the5ers/hs50k_10d'."""
    firm, product = key.split("/")
    cfg = load_yaml(f"config/firms/{firm}.yaml")
    p = dict(cfg["products"][product])
    p["firm"] = cfg["firm"]
    p["key"] = key
    return p


def registry() -> dict:
    return load_yaml("strategies/registry.yaml")["strategies"]
