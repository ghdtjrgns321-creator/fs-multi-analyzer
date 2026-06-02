"""Deterministic financial ratio calculations from ratio playbooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from config.settings import settings
from src.analysis_tools import load_normalized_financials

DEFAULT_CONFIG = settings.config_dir / "playbooks" / "financial_ratios.yaml"
DEFAULT_YEARS = [2022, 2023, 2024, 2025]


def load_ratio_config(path: Path | None = None) -> list[dict[str, Any]]:
    """Load ratio definitions from YAML."""

    with (path or DEFAULT_CONFIG).open(encoding="utf-8") as file:
        return list((yaml.safe_load(file) or {}).get("ratios", []))


def build_ratio_report(
    frame: pd.DataFrame,
    years: list[int] | tuple[int, ...],
    config_path: Path | None = None,
    fs_div: str = "CFS",
) -> pd.DataFrame:
    """Calculate configured financial ratios for each year."""

    rows = []
    for item in load_ratio_config(config_path):
        for year in years:
            result = _calculate(item, frame, int(year), fs_div)
            rows.append(
                {
                    "id": item["id"],
                    "category": item["category"],
                    "name": item["name"],
                    "year": int(year),
                    **result,
                }
            )
    return pd.DataFrame(rows)


def _calculate(
    item: dict[str, Any],
    frame: pd.DataFrame,
    year: int,
    fs_div: str,
) -> dict[str, object]:
    ratio_id = str(item["id"])
    accounts = list(item.get("accounts", []))
    if ratio_id == "roi":
        return _missing("투자원가 계정이 없다.")
    avg_den = {
        "roe": 100,
        "roa": 100,
        "receivable_turnover": 1,
        "inventory_turnover": 1,
        "total_asset_turnover": 1,
    }
    cur_den = {
        "operating_margin": 100,
        "debt_to_equity": 100,
        "current_ratio": 1,
        "interest_coverage": 1,
        "ocf_to_net_income": 1,
    }
    try:
        if ratio_id == "gross_profit_margin":
            revenue = _value(frame, accounts[0], year, fs_div)
            return _ratio(revenue - _value(frame, accounts[1], year, fs_div), revenue, 100)
        if ratio_id in avg_den:
            den, basis = _avg(frame, accounts[1], year, fs_div)
            num = _value(frame, accounts[0], year, fs_div)
            return _ratio(num, den, avg_den[ratio_id], basis)
        if ratio_id in {"dso", "dio"}:
            num, basis = _avg(frame, accounts[0], year, fs_div)
            den = _value(frame, accounts[1], year, fs_div)
            return _ratio(num, den, 365, basis)
        if ratio_id in cur_den:
            num = _value(frame, accounts[0], year, fs_div)
            den = _value(frame, accounts[1], year, fs_div)
            return _ratio(num, den, cur_den[ratio_id])
        if ratio_id == "accruals_ratio":
            den, basis = _avg(frame, accounts[2], year, fs_div)
            numerator = _value(frame, accounts[0], year, fs_div) - _value(
                frame, accounts[1], year, fs_div
            )
            return _ratio(numerator, den, 100, basis)
    except (IndexError, KeyError, TypeError):
        return _missing("필요 계정이 없거나 값이 결측이다.")
    return _missing("지원하지 않는 지표 id다.")


def _value(frame: pd.DataFrame, account: str, year: int, fs_div: str) -> float:
    matched = frame[
        (frame["canonical"] == account)
        & (frame["fs_div"] == fs_div)
        & (frame["year"].astype(str) == str(year))
    ]
    if matched.empty or pd.isna(matched.iloc[0]["amount"]):
        raise KeyError(account)
    return round(float(matched.iloc[0]["amount"]), settings.amount_round_digits)


def _avg(frame: pd.DataFrame, account: str, year: int, fs_div: str) -> tuple[float, str]:
    current = _value(frame, account, year, fs_div)
    try:
        prior = _value(frame, account, year - 1, fs_div)
    except KeyError:
        return current, "ending_value_proxy"
    return round((prior + current) / 2, settings.amount_round_digits), "average_prior_current"


def _ratio(
    numerator: float,
    denominator: float,
    multiplier: float,
    basis: str = "current_year",
) -> dict[str, object]:
    if denominator == 0:
        return _missing("분모가 0이다.")
    return {
        "value": round(numerator / denominator * multiplier, 2),
        "status": "computed",
        "basis": basis,
    }


def _missing(reason: str) -> dict[str, object]:
    return {"value": None, "status": "not_computed", "reason": reason}


def main() -> None:
    frame = load_normalized_financials("00126380", DEFAULT_YEARS)
    print(build_ratio_report(frame, DEFAULT_YEARS).to_string(index=False))


if __name__ == "__main__":
    main()
