"""MVP1 deterministic relationship-chain calculations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analysis_tools import account_series, compare_growth, yoy_growth_pct
from src.signals.config import load_l2_config
from src.signals.sanity import exclude_asset_sanity_years
from src.signals.universal import scale_floors

GROWTH_COLUMNS = [
    "year",
    "account_a",
    "account_b",
    "current_amount_a",
    "current_amount_b",
    "growth_a_pct",
    "growth_b_pct",
    "divergence_pp",
]
YOY_COLUMNS = [
    "fs_div",
    "sj_div",
    "canonical",
    "year",
    "amount",
    "prior_amount",
    "valid_yoy_base",
    "yoy_growth_pct",
]
DIRECTION_COLUMNS = [
    "id",
    "name",
    "year",
    "growth_account",
    "growth_direction",
    "flow_account",
    "flow_direction",
    "direction_same",
]


def account_yoy_table(
    frame: pd.DataFrame,
    accounts: list[str],
    years: list[int],
    fs_div: str,
    floors: dict[int, float] | None = None,
) -> pd.DataFrame:
    """Calculate YoY growth for configured accounts."""

    rows = []
    for account in accounts:
        values = account_series(frame, account, years, fs_div)
        growth = yoy_growth_pct(values)
        sj_div = _account_sj_div(frame, account, fs_div)
        for year in years[1:]:
            previous = int(year) - 1
            rows.append(
                {
                    "fs_div": fs_div,
                    "sj_div": sj_div,
                    "canonical": account,
                    "year": year,
                    "amount": values[year],
                    "prior_amount": values.get(previous),
                    "valid_yoy_base": _valid_growth_base(
                        values.get(previous),
                        values[year],
                        (floors or {}).get(int(year), 100_000_000),
                    ),
                    "yoy_growth_pct": growth.get(year),
                }
            )
    return pd.DataFrame(rows, columns=YOY_COLUMNS)


def direction_table(
    frame: pd.DataFrame,
    config: dict,
    fs_div: str,
    years: list[int],
) -> pd.DataFrame:
    """Compare configured account growth direction against cash-flow direction."""

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
    return pd.DataFrame(rows, columns=DIRECTION_COLUMNS)


def build_mvp1_signal_report(
    frame: pd.DataFrame,
    config_path: Path | None = None,
    years: list[int] | None = None,
) -> dict[str, object]:
    """Build deterministic L2 tables from normalized financials."""

    frame = _ensure_input_columns(frame)
    config = load_l2_config(config_path)
    primary = config["primary_fs_div"]
    reference = config["reference_fs_div"]
    thresholds = config.get("signal_thresholds", {})
    frame = exclude_asset_sanity_years(frame, thresholds)
    analysis_years = _analysis_years(frame, years)
    floors = scale_floors(frame, thresholds, primary)
    divergences = [
        _guarded_compare_growth(
            frame,
            item["account_a"],
            item["account_b"],
            analysis_years,
            primary,
            floors,
        ).assign(
            id=item["id"],
            name=item["name"],
        )
        for item in config.get("growth_divergences", [])
    ]
    growth_divergences = (
        pd.concat(divergences, ignore_index=True)
        if divergences
        else pd.DataFrame(
            columns=[*GROWTH_COLUMNS, "id", "name"]
        )
    )
    return {
        "primary_fs_div": primary,
        "reference_fs_div": reference,
        "growth_divergences": growth_divergences,
        "asset_totals": _asset_totals(frame, primary),
        "direction_checks": direction_table(frame, config, primary, analysis_years),
        "primary_yoy": account_yoy_table(
            frame,
            config["yoy_accounts"],
            analysis_years,
            primary,
            floors,
        ),
        "reference_yoy": account_yoy_table(
            frame,
            config["yoy_accounts"],
            analysis_years,
            reference,
        ),
        "deferred_ratios": config.get("deferred_ratios", []),
        "signal_thresholds": config.get("signal_thresholds", {}),
    }


def _guarded_compare_growth(
    frame: pd.DataFrame,
    account_a: str,
    account_b: str,
    years: list[int],
    fs_div: str,
    floors: dict[int, float],
) -> pd.DataFrame:
    result = compare_growth(frame, account_a, account_b, years, fs_div)
    for column in GROWTH_COLUMNS:
        if column not in result.columns:
            result[column] = pd.Series(dtype=object)
    result = result[GROWTH_COLUMNS]
    if result.empty:
        return result
    values_a = account_series(frame, account_a, years, fs_div)
    values_b = account_series(frame, account_b, years, fs_div)
    result["current_amount_a"] = result["year"].map(values_a)
    result["current_amount_b"] = result["year"].map(values_b)
    for idx, row in result.iterrows():
        year = int(row["year"])
        previous = year - 1
        floor = floors.get(previous, 100_000_000)
        valid = _valid_growth_base(values_a.get(previous), values_a.get(year), floor) and (
            _valid_growth_base(values_b.get(previous), values_b.get(year), floor)
        )
        if not valid:
            result.loc[idx, ["growth_a_pct", "growth_b_pct", "divergence_pp"]] = None
    return result


def _asset_totals(frame: pd.DataFrame, fs_div: str) -> dict[int, float]:
    matched = frame[
        (frame["fs_div"] == fs_div)
        & (frame["canonical"] == "자산총계")
        & (frame["amount"].notna())
    ].copy()
    if matched.empty:
        return {}
    matched["year"] = pd.to_numeric(matched["year"], errors="coerce")
    matched["amount"] = pd.to_numeric(matched["amount"], errors="coerce").abs()
    matched = matched[matched["year"].notna() & matched["amount"].notna()]
    return {
        int(row.year): float(row.amount)
        for row in matched.sort_values("amount", ascending=False)
        .drop_duplicates(["year"])
        .itertuples()
    }


def _account_sj_div(frame: pd.DataFrame, account: str, fs_div: str) -> str | None:
    matched = frame[(frame["canonical"] == account) & (frame["fs_div"] == fs_div)]
    if matched.empty or "sj_div" not in matched.columns:
        return None
    return str(matched.iloc[0]["sj_div"])


def _valid_growth_base(
    prior: float | None,
    current: float | None,
    floor: float,
) -> bool:
    if prior is None or current is None:
        return False
    return abs(float(prior)) >= floor and float(prior) * float(current) > 0


def _analysis_years(frame: pd.DataFrame, years: list[int] | None) -> list[int]:
    if years is not None:
        return sorted({int(year) for year in years})
    if frame.empty or "year" not in frame.columns:
        return []
    return sorted(int(year) for year in frame["year"].dropna().unique())


def _ensure_input_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in ("year", "fs_div", "sj_div", "canonical", "account_id", "label", "amount"):
        if column not in result.columns:
            result[column] = pd.Series(dtype=object)
    return result


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
