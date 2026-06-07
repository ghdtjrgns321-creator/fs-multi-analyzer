"""Universal account-level scans outside configured relationship chains."""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import pandas as pd

from config.settings import settings
from src.normalize.config import load_canonical_accounts, normalize_label, subtotal_account_names
from src.schemas.findings import EvidenceRef
from src.signals.config import load_l2_config
from src.signals.red_flags import RedFlagSignal
from src.signals.sanity import exclude_asset_sanity_years
from src.signals.tracks import apply_track_quota, track_for_amount

MIN_Z_HISTORY = 4
UNIVERSAL_STATEMENTS = ("BS", "IS", "CIS", "CF", "SCE")
CFS_OFS_GAP_STATEMENTS = ("BS", "IS", "CF")


def scan_universal_signals(
    frame: pd.DataFrame,
    target_year: int,
    include_all: bool = False,
    legacy_unified: bool = False,
) -> list[RedFlagSignal]:
    """Scan every account time series on one consistent statement basis."""

    thresholds = load_l2_config()["signal_thresholds"]
    top_n = int(thresholds.get("universal_top_n", 12))
    fs_div = preferred_fs_div(frame, target_year)
    scoped = _scan_frame(frame, fs_div)
    scoped = exclude_asset_sanity_years(scoped, thresholds)
    if scoped.empty:
        return []
    scoped = scoped[scoped["sj_div"].isin(UNIVERSAL_STATEMENTS)].copy()
    if scoped.empty:
        return []
    scoped = _aggregate_series(scoped)
    scale_frame = scoped.copy()
    floors = scale_floors(scale_frame, thresholds, fs_div)
    asset_totals = _asset_totals(scale_frame, fs_div)
    scoped = _exclude_subtotal_rows(scoped)
    if scoped.empty:
        return []
    scoped["mix_pct"] = scoped["abs_amount"] / scoped.groupby(["year", "sj_div"])[
        "abs_amount"
    ].transform("sum") * 100
    grouped = scoped.groupby("scan_key", sort=False)
    signals = _yoy_and_mix(grouped, target_year, thresholds, floors)
    signals.extend(_z_scores(grouped, target_year, thresholds, floors))
    signals = [_with_track(signal, asset_totals, thresholds) for signal in signals]
    ranked = sorted(signals, key=lambda item: _score(item), reverse=True)
    if include_all:
        return ranked
    if legacy_unified:
        return ranked[:top_n]
    quotaed = apply_track_quota(ranked, thresholds, _score)
    return quotaed[:top_n]


def scan_cfs_ofs_gaps(frame: pd.DataFrame, target_year: int) -> list[RedFlagSignal]:
    """Compare same account_id between consolidated and separate statements."""

    thresholds = load_l2_config()["signal_thresholds"]
    min_gap = float(thresholds.get("cfs_ofs_gap_pct_abs", 30))
    top_n = int(thresholds.get("universal_top_n", 12))
    scoped = _scan_frame(frame, None)
    scoped = exclude_asset_sanity_years(scoped, thresholds)
    scoped = scoped[scoped["sj_div"].isin(CFS_OFS_GAP_STATEMENTS)].copy()
    floors = scale_floors(scoped, thresholds)
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
    floor = floors.get(target_year, _abs_min(thresholds))
    pivot = pivot[(pivot["CFS"].abs() >= floor) | (pivot["OFS"].abs() >= floor)].copy()
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
            sj_div=str(row.sj_div),
        )
        for row in flagged.itertuples()
    ][:top_n]


def preferred_fs_div(frame: pd.DataFrame, target_year: int) -> str:
    """Choose CFS when complete; otherwise use OFS without mixing bases."""

    target_year = int(target_year)
    scoped = _scan_frame(frame, None)
    if scoped.empty:
        return "CFS"
    years = set(scoped[scoped["year"] <= target_year]["year"].astype(int))
    if not years:
        return "CFS"
    for fs_div in ("CFS", "OFS"):
        available = set(
            scoped[
                (scoped["fs_div"] == fs_div) & (scoped["year"] <= target_year)
            ]["year"].astype(int)
        )
        if years.issubset(available):
            return fs_div
    target_rows = scoped[scoped["year"] == target_year]
    return "CFS" if "CFS" in set(target_rows["fs_div"]) else "OFS"


def _scan_frame(frame: pd.DataFrame, fs_div: str | None) -> pd.DataFrame:
    scoped = frame.copy()
    if fs_div:
        scoped = scoped[scoped["fs_div"] == fs_div]
    if "sj_div" in scoped.columns:
        scoped = scoped[scoped["sj_div"].isin(UNIVERSAL_STATEMENTS)]
    else:
        scoped["sj_div"] = ""
    scoped = scoped[scoped["amount"].notna()].copy()
    if scoped.empty:
        return scoped
    scoped["year"] = pd.to_numeric(scoped["year"], errors="coerce")
    scoped["amount"] = pd.to_numeric(scoped["amount"], errors="coerce")
    scoped = scoped[scoped["year"].notna() & scoped["amount"].notna()].copy()
    scoped["year"] = scoped["year"].astype(int)
    for column in ("account_id", "label"):
        if column not in scoped.columns:
            scoped[column] = ""
    if "canonical" not in scoped.columns:
        scoped["canonical"] = "기타 중요 계정"
    scoped["account_id"] = scoped["account_id"].fillna("").astype(str)
    scoped["label"] = scoped["label"].fillna("").astype(str)
    scoped["canonical"] = scoped["canonical"].fillna("기타 중요 계정").astype(str)
    scoped["evidence_key"] = scoped["account_id"] + "|" + scoped["label"]
    scoped["scan_key"] = scoped.apply(_series_key, axis=1)
    scoped["abs_amount"] = scoped["amount"].abs()
    scoped = _filter_statement_compatible(scoped)
    return scoped


def _filter_statement_compatible(scoped: pd.DataFrame) -> pd.DataFrame:
    statement_by_account = _canonical_statement_map()
    if not statement_by_account:
        return scoped
    canonical_statement = scoped["canonical"].map(statement_by_account)
    compatible = (
        scoped["canonical"].eq("기타 중요 계정")
        | canonical_statement.isna()
        | canonical_statement.eq(scoped["sj_div"])
    )
    return scoped[compatible].copy()


@lru_cache(maxsize=1)
def _canonical_statement_map() -> dict[str, str]:
    return {
        account.name: account.statement
        for account in load_canonical_accounts(settings.config_dir / "canonical_accounts.yaml")
    }


def _aggregate_series(scoped: pd.DataFrame) -> pd.DataFrame:
    """Collapse rows that represent the same economic account in one year."""

    mapped = scoped[scoped["canonical"] != "기타 중요 계정"]
    unmapped = scoped[scoped["canonical"] == "기타 중요 계정"]
    frames = []
    if not mapped.empty:
        frames.append(
            mapped.groupby(["scan_key", "year", "fs_div", "sj_div"], sort=False)
            .agg(
                amount=("amount", "sum"),
                account_id=("account_id", "first"),
                label=("label", "first"),
                canonical=("canonical", "first"),
                evidence_key=("evidence_key", "first"),
            )
            .reset_index()
        )
    if not unmapped.empty:
        frames.append(
            unmapped.sort_values("abs_amount", ascending=False)
            .drop_duplicates(["scan_key", "year", "fs_div", "sj_div"])
            .copy()
        )
    aggregated = pd.concat(frames, ignore_index=True) if frames else scoped
    aggregated["abs_amount"] = aggregated["amount"].abs()
    return aggregated


def _exclude_subtotal_rows(scoped: pd.DataFrame) -> pd.DataFrame:
    subtotals = subtotal_account_names(settings.config_dir / "canonical_accounts.yaml")
    if not subtotals:
        return scoped
    return scoped[~scoped["canonical"].isin(subtotals)].copy()


def scale_floors(
    frame: pd.DataFrame,
    thresholds: dict[str, Any] | None = None,
    fs_div: str | None = None,
) -> dict[int, float]:
    """Return year-specific materiality floors for universal scans."""

    config = thresholds or load_l2_config()["signal_thresholds"]
    scoped = _scan_frame(frame, None)
    if scoped.empty:
        return {}
    if fs_div:
        scoped = scoped[scoped["fs_div"] == fs_div]
    abs_min = _abs_min(config)
    pct = float(config.get("universal_min_pct_of_assets", 0.0))
    floors: dict[int, float] = {}
    for year, rows in scoped.groupby("year"):
        asset = _asset_total(rows, fs_div)
        relative = abs(asset) * pct / 100 if asset is not None else 0.0
        floors[int(year)] = max(relative, abs_min)
    return floors


def account_above_floor(frame: pd.DataFrame, account: str, year: int) -> bool:
    """Check if a normalized account candidate passes the year floor."""

    fs_div = preferred_fs_div(frame, year)
    scoped = _scan_frame(frame, fs_div)
    if scoped.empty:
        return False
    floor = scale_floors(scoped, fs_div=fs_div).get(
        year,
        _abs_min(load_l2_config()["signal_thresholds"]),
    )
    rows = scoped[(scoped["year"] == year) & _account_mask(scoped, account)]
    return bool(not rows.empty and rows["abs_amount"].max() >= floor)


def _asset_total(rows: pd.DataFrame, fs_div: str | None) -> float | None:
    scoped = rows if fs_div is None else rows[rows["fs_div"] == fs_div]
    sj_mask = scoped["sj_div"] == "BS" if scoped["sj_div"].ne("").any() else True
    assets = scoped[
        sj_mask
        & (
            (scoped["canonical"] == "자산총계")
            | (scoped["account_id"] == "ifrs-full_Assets")
        )
    ]
    if assets.empty:
        return None
    return float(assets.iloc[0].amount)


def _asset_totals(frame: pd.DataFrame, fs_div: str | None) -> dict[int, float]:
    scoped = frame if fs_div is None else frame[frame["fs_div"] == fs_div]
    assets = scoped[
        (scoped["canonical"] == "자산총계") | (scoped["account_id"] == "ifrs-full_Assets")
    ]
    if assets.empty:
        return {}
    return {
        int(row.year): float(row.amount)
        for row in assets.sort_values("abs_amount", ascending=False)
        .drop_duplicates(["year"])
        .itertuples()
    }


def _with_track(
    signal: RedFlagSignal,
    asset_totals: dict[int, float],
    thresholds: dict[str, Any],
) -> RedFlagSignal:
    track, ratio = track_for_amount(
        signal.current_amount,
        asset_totals.get(int(signal.year)),
        thresholds,
    )
    return RedFlagSignal(
        id=signal.id,
        year=signal.year,
        account=signal.account,
        signal_type=signal.signal_type,
        description=signal.description,
        metric_value=signal.metric_value,
        evidence=signal.evidence,
        track=track,
        magnitude_ratio=ratio,
        current_amount=signal.current_amount,
        sj_div=signal.sj_div,
    )


def _series_key(row: pd.Series) -> str:
    canonical = str(row["canonical"])
    if canonical and canonical != "기타 중요 계정":
        return "canonical:" + normalize_label(canonical)
    return "label:" + normalize_label(str(row["label"]))


def _account_mask(frame: pd.DataFrame, account: str) -> pd.Series:
    needle = str(account)
    return (
        frame["canonical"].astype(str).str.contains(needle, regex=False)
        | frame["label"].astype(str).str.contains(needle, regex=False)
        | frame["account_id"].astype(str).str.contains(needle, regex=False)
    )


def _abs_min(thresholds: dict[str, Any]) -> float:
    return float(thresholds.get("universal_min_abs_amount", 100_000_000))


def _yoy_and_mix(
    grouped: Any,
    target_year: int,
    thresholds: dict[str, Any],
    floors: dict[int, float],
) -> list[RedFlagSignal]:
    signals: list[RedFlagSignal] = []
    for _, rows in grouped:
        rows = rows.sort_values("year")
        current = _row_for_year(rows, target_year)
        prior = _row_for_year(rows, target_year - 1)
        floor = floors.get(target_year, _abs_min(thresholds))
        prior_floor = floors.get(target_year - 1, _abs_min(thresholds))
        if current is None or prior is None or abs(float(current.amount)) < floor:
            continue
        if not _valid_yoy_base(current, prior, prior_floor):
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
    floors: dict[int, float],
) -> list[RedFlagSignal]:
    signals: list[RedFlagSignal] = []
    for _, rows in grouped:
        rows = rows.sort_values("year")
        current = _row_for_year(rows, target_year)
        history = rows[rows["year"] < target_year]["amount"]
        floor = floors.get(target_year, _abs_min(thresholds))
        if current is None or abs(float(current.amount)) < floor or len(history) < MIN_Z_HISTORY:
            continue
        std = float(history.std(ddof=0))
        if math.isclose(std, 0.0):
            continue
        z = (float(current.amount) - float(history.mean())) / std
        cap = float(thresholds.get("universal_z_score_cap", 10))
        z = max(-cap, min(cap, z))
        if abs(z) >= float(thresholds.get("z_score_abs", 2)):
            signals.append(_signal("universal_z_score", current, target_year, z))
    return signals


def _row_for_year(rows: pd.DataFrame, year: int) -> Any | None:
    matched = rows[rows["year"] == year]
    return None if matched.empty else next(matched.itertuples())


def _valid_yoy_base(current: Any, prior: Any, prior_floor: float) -> bool:
    current_amount = float(current.amount)
    prior_amount = float(prior.amount)
    return (
        abs(prior_amount) >= prior_floor
        and not math.isclose(prior_amount, 0.0)
        and current_amount * prior_amount > 0
    )


def _signal(signal_type: str, row: Any, year: int, metric: float) -> RedFlagSignal:
    locator = getattr(row, "evidence_key", row.scan_key)
    return RedFlagSignal(
        id=f"{signal_type}:{row.scan_key}:{year}",
        year=year,
        account=_account_name(row),
        signal_type=signal_type,
        description=f"전 계정 보편 스캔: {row.label}",
        metric_value=round(float(metric), 2),
        evidence=[_evidence(locator, year, f"{row.label}: {int(row.amount):,}")],
        current_amount=float(row.amount),
        sj_div=str(row.sj_div),
    )


def _account_name(row: Any) -> str:
    return str(row.label if row.canonical == "기타 중요 계정" else row.canonical)


def _evidence(locator: str, year: int, value: str) -> EvidenceRef:
    return EvidenceRef(source="financial_statement", locator=locator, year=str(year), value=value)


def _score(signal: RedFlagSignal) -> float:
    if not isinstance(signal.metric_value, int | float):
        return 0.0
    thresholds = load_l2_config()["signal_thresholds"]
    threshold = {
        "universal_yoy": thresholds.get("yoy_pct_abs"),
        "universal_mix_shift": thresholds.get("mix_shift_pp_abs"),
        "universal_z_score": thresholds.get("z_score_abs"),
    }.get(signal.signal_type)
    if not isinstance(threshold, int | float) or math.isclose(float(threshold), 0.0):
        return abs(float(signal.metric_value))
    return abs(float(signal.metric_value)) / float(threshold)
