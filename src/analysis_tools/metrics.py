"""Deterministic tool DSL metrics for L2 signal calculations."""

from __future__ import annotations

import pandas as pd

from config.settings import settings


def account_series(
    frame: pd.DataFrame,
    account: str,
    years: list[int] | tuple[int, ...],
    fs_div: str = "CFS",
) -> dict[int, float | None]:
    """Return rounded yearly amounts for a canonical account."""

    scoped = frame[(frame["canonical"] == account) & (frame["fs_div"] == fs_div)]
    values: dict[int, float | None] = {}
    for year in years:
        matched = scoped[scoped["year"].astype(str) == str(year)]
        if matched.empty or pd.isna(matched.iloc[0]["amount"]):
            values[int(year)] = None
        else:
            amount = float(matched.iloc[0]["amount"])
            values[int(year)] = round(amount, settings.amount_round_digits)
    return values


def yoy_growth_pct(values: dict[int, float | None], digits: int = 2) -> dict[int, float | None]:
    """Calculate YoY growth percentage using absolute prior-year base."""

    growth: dict[int, float | None] = {}
    ordered = sorted(values)
    for previous, current in zip(ordered, ordered[1:], strict=False):
        prior = values[previous]
        current_value = values[current]
        if prior in (None, 0) or current_value is None:
            growth[current] = None
        else:
            growth[current] = round((current_value - prior) / abs(prior) * 100, digits)
    return growth


def compare_growth(
    frame: pd.DataFrame,
    account_a: str,
    account_b: str,
    years: list[int] | tuple[int, ...],
    fs_div: str = "CFS",
) -> pd.DataFrame:
    """Compare two accounts' YoY growth and return divergence in percentage points."""

    growth_a = yoy_growth_pct(account_series(frame, account_a, years, fs_div))
    growth_b = yoy_growth_pct(account_series(frame, account_b, years, fs_div))
    rows = []
    for year in sorted(growth_a):
        left = growth_a[year]
        right = growth_b.get(year)
        divergence = None if left is None or right is None else round(left - right, 2)
        rows.append(
            {
                "year": year,
                "account_a": account_a,
                "account_b": account_b,
                "growth_a_pct": left,
                "growth_b_pct": right,
                "divergence_pp": divergence,
            }
        )
    return pd.DataFrame(rows)


def compute_ratio(
    frame: pd.DataFrame,
    numerator: str,
    denominator: str,
    years: list[int] | tuple[int, ...],
    fs_div: str = "CFS",
) -> pd.DataFrame:
    """Compute yearly numerator/denominator ratios as percentages."""

    top = account_series(frame, numerator, years, fs_div)
    bottom = account_series(frame, denominator, years, fs_div)
    rows = []
    for year in years:
        num = top[int(year)]
        den = bottom[int(year)]
        ratio = None if num is None or den in (None, 0) else round(num / den * 100, 2)
        rows.append(
            {
                "year": int(year),
                "numerator": numerator,
                "denominator": denominator,
                "ratio_pct": ratio,
            }
        )
    return pd.DataFrame(rows)
