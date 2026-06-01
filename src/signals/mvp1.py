"""MVP1 deterministic relationship-chain calculations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analysis_tools import account_series, compare_growth, yoy_growth_pct
from src.signals.config import load_l2_config


def account_yoy_table(
    frame: pd.DataFrame,
    accounts: list[str],
    years: list[int],
    fs_div: str,
) -> pd.DataFrame:
    """Calculate YoY growth for configured accounts."""

    rows = []
    for account in accounts:
        values = account_series(frame, account, years, fs_div)
        growth = yoy_growth_pct(values)
        for year in years[1:]:
            rows.append(
                {
                    "fs_div": fs_div,
                    "canonical": account,
                    "year": year,
                    "amount": values[year],
                    "yoy_growth_pct": growth.get(year),
                }
            )
    return pd.DataFrame(rows)


def direction_table(frame: pd.DataFrame, config: dict, fs_div: str) -> pd.DataFrame:
    """Compare configured account growth direction against cash-flow direction."""

    years = [int(year) for year in config["years"]]
    rows = []
    for item in config.get("direction_checks", []):
        growth_values = account_series(frame, item["growth_account"], years, fs_div)
        flow_values = account_series(frame, item["flow_account"], years, fs_div)
        for previous, current in zip(years, years[1:], strict=False):
            growth_delta = _delta(growth_values[previous], growth_values[current])
            flow_delta = _delta(flow_values[previous], flow_values[current])
            rows.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "year": current,
                    "growth_account": item["growth_account"],
                    "growth_direction": _direction(growth_delta),
                    "flow_account": item["flow_account"],
                    "flow_direction": _direction(flow_delta),
                    "direction_same": _direction(growth_delta) == _direction(flow_delta),
                }
            )
    return pd.DataFrame(rows)


def build_mvp1_signal_report(
    frame: pd.DataFrame,
    config_path: Path | None = None,
) -> dict[str, object]:
    """Build deterministic L2 tables from normalized financials."""

    config = load_l2_config(config_path)
    years = [int(year) for year in config["years"]]
    primary = config["primary_fs_div"]
    reference = config["reference_fs_div"]
    divergences = [
        compare_growth(frame, item["account_a"], item["account_b"], years, primary).assign(
            id=item["id"],
            name=item["name"],
        )
        for item in config.get("growth_divergences", [])
    ]
    return {
        "primary_fs_div": primary,
        "reference_fs_div": reference,
        "growth_divergences": pd.concat(divergences, ignore_index=True),
        "direction_checks": direction_table(frame, config, primary),
        "primary_yoy": account_yoy_table(frame, config["yoy_accounts"], years, primary),
        "reference_yoy": account_yoy_table(frame, config["yoy_accounts"], years, reference),
        "deferred_ratios": config.get("deferred_ratios", []),
    }


def _delta(previous: float | None, current: float | None) -> float | None:
    if previous is None or current is None:
        return None
    return current - previous


def _direction(value: float | None) -> str:
    if value is None:
        return "missing"
    if value > 0:
        return "increase"
    if value < 0:
        return "decrease"
    return "flat"
