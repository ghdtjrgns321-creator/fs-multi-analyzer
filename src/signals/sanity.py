"""Sanity guards for statement data before signal calculations."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)


def exclude_foreign_currency_years(
    frame: pd.DataFrame,
    target_year: int | None = None,
) -> pd.DataFrame:
    """통화전환 회사의 cross-year 가짜 점프 차단.

    target_year(없으면 최신연도)의 보고 통화와 다른 통화로 보고된 연도를 신호 계산에서 제외한다.
    예: 두산밥캣 2020~2022 KRW → 2023~2025 USD. 2024 신호는 USD 연도끼리만 비교하고 KRW 연도는
    제외해 약 1,300배 통화전환 점프를 거짓신호로 잡지 않는다. 통화 컬럼이 없거나(구 DB) 단일
    통화면 no-op(하위호환).
    """

    if frame.empty or "currency" not in frame.columns:
        return frame
    cur = frame["currency"].astype(str).str.strip().replace({"nan": "", "None": "", "NaN": ""})
    if cur.eq("").all():
        return frame  # 통화정보 없음 → 손대지 않음
    years = pd.to_numeric(frame["year"], errors="coerce")
    ref_year = target_year if target_year is not None else years.max()
    if pd.isna(ref_year):
        return frame
    ref_cur = cur[years == ref_year]
    ref_cur = ref_cur[ref_cur != ""]
    modes = ref_cur.mode()
    if modes.empty:
        return frame
    base = modes.iloc[0]
    drop = (cur != base) & (cur != "")  # 다른 통화만 제외, 결측은 보존
    if not drop.any():
        return frame
    LOGGER.warning("Excluding foreign-currency years (base=%s) from signals", base)
    return frame[~drop].copy()


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
