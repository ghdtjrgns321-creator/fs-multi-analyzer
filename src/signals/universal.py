"""Universal account-level scans outside configured relationship chains."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from src.schemas.findings import EvidenceRef
from src.signals.config import load_l2_config
from src.signals.red_flags import RedFlagSignal


def scan_universal_signals(frame: pd.DataFrame, target_year: int) -> list[RedFlagSignal]:
    """Scan every CFS account_id for YoY, z-score, and composition changes."""

    thresholds = load_l2_config()["signal_thresholds"]
    top_n = int(thresholds.get("universal_top_n", 12))
    min_abs = float(thresholds.get("universal_min_abs_amount", 1_000_000_000_000))
    scoped = _scan_frame(frame, "CFS")
    if scoped.empty:
        return []
    scoped["mix_pct"] = scoped["abs_amount"] / scoped.groupby(["year", "sj_div"])[
        "abs_amount"
    ].transform("sum") * 100
    grouped = scoped.groupby("scan_key", sort=False)
    signals = _yoy_and_mix(grouped, target_year, thresholds, min_abs)
    signals.extend(_z_scores(grouped, target_year, thresholds, min_abs))
    return sorted(signals, key=lambda item: _score(item), reverse=True)[:top_n]


def scan_cfs_ofs_gaps(frame: pd.DataFrame, target_year: int) -> list[RedFlagSignal]:
    """Compare same account_id between consolidated and separate statements."""

    thresholds = load_l2_config()["signal_thresholds"]
    min_abs = float(thresholds.get("universal_min_abs_amount", 1_000_000_000_000))
    min_gap = float(thresholds.get("cfs_ofs_gap_pct_abs", 30))
    top_n = int(thresholds.get("universal_top_n", 12))
    scoped = _scan_frame(frame, None)
    scoped = scoped[(scoped["year"] == target_year) & (scoped["fs_div"].isin(["CFS", "OFS"]))]
    if scoped.empty:
        return []
    pivot = scoped.pivot_table(
        index=["scan_key", "label", "account_id", "canonical", "sj_div"],
        columns="fs_div",
        values="amount",
        aggfunc="sum",
    ).reset_index()
    if not {"CFS", "OFS"}.issubset(pivot.columns):
        return []
    pivot = pivot[(pivot["CFS"].abs() >= min_abs) | (pivot["OFS"].abs() >= min_abs)].copy()
    pivot["gap_pct"] = (
        (pivot["CFS"] - pivot["OFS"]) / pivot[["CFS", "OFS"]].abs().max(axis=1) * 100
    )
    flagged = pivot[pivot["gap_pct"].abs() >= min_gap].sort_values(
        "gap_pct",
        key=abs,
        ascending=False,
    )
    return [
        RedFlagSignal(
            id=f"cfs-ofs-gap:{row.scan_key}:{target_year}",
            year=target_year,
            account=_account_name(row),
            signal_type="cfs_ofs_gap",
            description="연결(CFS) vs 별도(OFS) 금액 괴리",
            metric_value=round(float(row.gap_pct), 2),
            evidence=[
                _evidence(row.scan_key, target_year, f"CFS {int(row.CFS):,}"),
                _evidence(row.scan_key, target_year, f"OFS {int(row.OFS):,}"),
            ],
        )
        for row in flagged.itertuples()
    ][:top_n]


def _scan_frame(frame: pd.DataFrame, fs_div: str | None) -> pd.DataFrame:
    scoped = frame.copy()
    if fs_div:
        scoped = scoped[scoped["fs_div"] == fs_div]
    if "sj_div" in scoped.columns:
        scoped = scoped[scoped["sj_div"].isin(["BS", "IS", "CF"])]
    scoped = scoped[scoped["amount"].notna()].copy()
    if scoped.empty:
        return scoped
    scoped["year"] = pd.to_numeric(scoped["year"], errors="coerce")
    scoped["amount"] = pd.to_numeric(scoped["amount"], errors="coerce")
    scoped = scoped[scoped["year"].notna() & scoped["amount"].notna()].copy()
    scoped["year"] = scoped["year"].astype(int)
    scoped["account_id"] = scoped["account_id"].fillna("").astype(str)
    scoped["label"] = scoped["label"].fillna("").astype(str)
    scoped["canonical"] = scoped["canonical"].fillna("기타 중요 계정").astype(str)
    scoped["scan_key"] = scoped["account_id"] + "|" + scoped["label"]
    scoped["abs_amount"] = scoped["amount"].abs()
    return scoped


def _yoy_and_mix(
    grouped: Any,
    target_year: int,
    thresholds: dict[str, Any],
    min_abs: float,
) -> list[RedFlagSignal]:
    signals: list[RedFlagSignal] = []
    for _, rows in grouped:
        rows = rows.sort_values("year")
        current = _row_for_year(rows, target_year)
        prior = _row_for_year(rows, target_year - 1)
        if current is None or prior is None or abs(float(current.amount)) < min_abs:
            continue
        if prior.amount and not math.isclose(float(prior.amount), 0.0):
            yoy = (float(current.amount) - float(prior.amount)) / abs(float(prior.amount)) * 100
            if abs(yoy) >= float(thresholds.get("yoy_pct_abs", 50)):
                signals.append(_signal("universal_yoy", current, target_year, yoy))
        mix_pp = float(current.mix_pct) - float(prior.mix_pct)
        if abs(mix_pp) >= float(thresholds.get("mix_shift_pp_abs", 5)):
            signals.append(_signal("universal_mix_shift", current, target_year, mix_pp))
    return signals


def _z_scores(
    grouped: Any,
    target_year: int,
    thresholds: dict[str, Any],
    min_abs: float,
) -> list[RedFlagSignal]:
    signals: list[RedFlagSignal] = []
    for _, rows in grouped:
        rows = rows.sort_values("year")
        current = _row_for_year(rows, target_year)
        history = rows[rows["year"] < target_year]["amount"]
        if current is None or abs(float(current.amount)) < min_abs or len(history) < 2:
            continue
        std = float(history.std(ddof=0))
        if math.isclose(std, 0.0):
            continue
        z = (float(current.amount) - float(history.mean())) / std
        if abs(z) >= float(thresholds.get("z_score_abs", 2)):
            signals.append(_signal("universal_z_score", current, target_year, z))
    return signals


def _row_for_year(rows: pd.DataFrame, year: int) -> Any | None:
    matched = rows[rows["year"] == year]
    return None if matched.empty else next(matched.itertuples())


def _signal(signal_type: str, row: Any, year: int, metric: float) -> RedFlagSignal:
    return RedFlagSignal(
        id=f"{signal_type}:{row.scan_key}:{year}",
        year=year,
        account=_account_name(row),
        signal_type=signal_type,
        description=f"전 계정 보편 스캔: {row.label}",
        metric_value=round(float(metric), 2),
        evidence=[_evidence(row.scan_key, year, f"{row.label}: {int(row.amount):,}")],
    )


def _account_name(row: Any) -> str:
    return str(row.label if row.canonical == "기타 중요 계정" else row.canonical)


def _evidence(locator: str, year: int, value: str) -> EvidenceRef:
    return EvidenceRef(source="financial_statement", locator=locator, year=str(year), value=value)


def _score(signal: RedFlagSignal) -> float:
    return abs(float(signal.metric_value)) if isinstance(signal.metric_value, int | float) else 0.0
