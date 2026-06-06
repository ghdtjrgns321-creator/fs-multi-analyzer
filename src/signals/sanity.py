"""Sanity guards for statement data before signal calculations."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)


def exclude_asset_sanity_years(
    frame: pd.DataFrame,
    thresholds: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Drop years where asset totals jump by an obvious scale error."""

    if frame.empty or "canonical" not in frame.columns:
        return frame
    multiple = float((thresholds or {}).get("asset_sanity_jump_multiple", 100))
    if multiple <= 1:
        return frame
    bad_years = suspicious_asset_years(frame, multiple)
    if not bad_years:
        return frame
    LOGGER.warning("Excluding suspicious asset-total years from signals: %s", bad_years)
    return frame[~frame["year"].astype(int).isin(bad_years)].copy()


def suspicious_asset_years(frame: pd.DataFrame, multiple: float = 100) -> set[int]:
    """Find years whose asset total is >= multiple times adjacent/median scale."""

    scoped = frame.copy()
    if "sj_div" in scoped.columns:
        scoped = scoped[scoped["sj_div"].fillna("").isin(["", "BS"])]
    assets = scoped[scoped["canonical"] == "자산총계"].copy()
    if assets.empty:
        return set()
    assets["year"] = pd.to_numeric(assets["year"], errors="coerce")
    assets["amount"] = pd.to_numeric(assets["amount"], errors="coerce").abs()
    assets = assets[assets["year"].notna() & assets["amount"].notna()]
    bad: set[int] = set()
    for fs_div, rows in assets.groupby("fs_div", dropna=False):
        del fs_div
        yearly = rows.groupby("year")["amount"].max().sort_index()
        if len(yearly) < 3:
            continue
        for year, amount in yearly.items():
            peers = _adjacent_or_median(yearly, year)
            if peers and amount >= max(peers) * multiple:
                bad.add(int(year))
    return bad


def _adjacent_or_median(series: pd.Series, year: float) -> list[float]:
    peers = [
        float(series.loc[item])
        for item in (year - 1, year + 1)
        if item in series.index and float(series.loc[item]) > 0
    ]
    if peers:
        return peers
    median = float(series[series.index != year].median())
    return [median] if median > 0 else []
