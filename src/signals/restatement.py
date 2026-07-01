"""Detect comparative-period restatements from preserved prior amounts."""

from __future__ import annotations

from typing import Any

import pandas as pd

from config.settings import settings
from src.normalize.config import normalize_label, subtotal_account_names
from src.schemas.findings import EvidenceRef
from src.signals.config import load_l2_config
from src.signals.red_flags import RedFlagSignal


def scan_restatement_signals(
    frame: pd.DataFrame,
    target_year: int | None = None,
) -> list[RedFlagSignal]:
    """Compare N report prior_amount with N-1 report original amount."""

    thresholds = load_l2_config()["signal_thresholds"]
    abs_min = float(thresholds.get("restatement_abs_amount", 100_000_000))
    rel_min = float(thresholds.get("restatement_rel_pct", 1.0))
    rel_max = float(thresholds.get("restatement_rel_pct_max", 1000.0))
    scale_max = float(thresholds.get("restatement_scale_multiple_max", 100.0))
    scoped = _scan_frame(frame)
    if scoped.empty:
        return []
    # SCE 2D 격자는 메인 프레임에서 구성요소 열이 소실돼 합계·member 셀이 label만으로 뭉개진다.
    # 평면 비교 시 자본잉여금 셀을 자본총계 전기값으로 오인해 거짓 재작성 신호를 낸다.
    # 자본 계정 재작성은 BS(자본총계 등)의 prior_amount로 정상 탐지된다 → SCE는 제외.
    scoped = scoped[scoped["sj_div"] != "SCE"]
    if scoped.empty:
        return []
    if target_year is not None:
        scoped = scoped[scoped["year"].isin([int(target_year), int(target_year) - 1])]
    floors = _asset_floors(scoped, thresholds, abs_min)
    scoped = _exclude_subtotal_rows(scoped)
    if scoped.empty:
        return []
    signals: list[RedFlagSignal] = []
    grouped = scoped.groupby(["scan_key", "fs_div", "sj_div"], sort=False)
    for _, rows in grouped:
        rows = rows.sort_values("year")
        for current in rows.itertuples():
            year = int(current.year)
            if target_year is not None and year != int(target_year):
                continue
            if pd.isna(current.prior_amount):
                continue
            original = _row_for_year(rows, year - 1)
            if original is None:
                continue
            diff = float(current.prior_amount) - float(original.amount)
            floor = floors.get((int(current.year), str(current.fs_div)), abs_min)
            if abs(diff) < floor:
                continue
            rel_pct = abs(diff) / max(abs(float(original.amount)), 1.0) * 100
            if rel_pct < rel_min or rel_pct >= rel_max:
                continue
            if _scale_multiple(current.prior_amount, original.amount) >= scale_max:
                continue
            signals.append(_signal(current, original, diff, rel_pct))
    return _dedupe_signals(
        sorted(signals, key=lambda item: abs(float(item.metric_value)), reverse=True)
    )


def _scan_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"year", "fs_div", "sj_div", "amount", "prior_amount"}
    if frame.empty or not required.issubset(frame.columns):
        return pd.DataFrame()
    scoped = frame.copy()
    for column in ("account_id", "label", "canonical"):
        if column not in scoped.columns:
            scoped[column] = ""
    scoped["year"] = pd.to_numeric(scoped["year"], errors="coerce")
    scoped["amount"] = pd.to_numeric(scoped["amount"], errors="coerce")
    scoped["prior_amount"] = pd.to_numeric(scoped["prior_amount"], errors="coerce")
    scoped = scoped[
        scoped["year"].notna()
        & scoped["amount"].notna()
        & scoped["fs_div"].notna()
        & scoped["sj_div"].notna()
    ].copy()
    if scoped.empty:
        return scoped
    scoped["year"] = scoped["year"].astype(int)
    scoped["fs_div"] = scoped["fs_div"].astype(str)
    scoped["sj_div"] = scoped["sj_div"].astype(str)
    scoped["account_id"] = scoped["account_id"].fillna("").astype(str)
    scoped["label"] = scoped["label"].fillna("").astype(str)
    scoped["canonical"] = scoped["canonical"].fillna("기타 중요 계정").astype(str)
    scoped["scan_key"] = scoped.apply(_series_key, axis=1)
    scoped["evidence_key"] = scoped["account_id"] + "|" + scoped["label"]
    return scoped


def _series_key(row: pd.Series) -> str:
    account_id = str(row["account_id"]).strip()
    label = normalize_label(str(row["label"]))
    if account_id and account_id != "-표준계정코드 미사용-":
        return "account_id_label:" + account_id + "|" + label
    return "label:" + label


def _exclude_subtotal_rows(scoped: pd.DataFrame) -> pd.DataFrame:
    subtotals = subtotal_account_names(settings.config_dir / "canonical_accounts.yaml")
    if not subtotals:
        return scoped
    return scoped[~scoped["canonical"].isin(subtotals)].copy()


def _asset_floors(
    scoped: pd.DataFrame,
    thresholds: dict[str, Any],
    abs_min: float,
) -> dict[tuple[int, str], float]:
    pct = float(
        thresholds.get(
            "restatement_min_pct_of_assets",
            thresholds.get("universal_min_pct_of_assets", 0.0),
        )
    )
    if pct <= 0:
        return {}
    assets = scoped[
        (scoped["canonical"] == "자산총계") | (scoped["account_id"] == "ifrs-full_Assets")
    ].copy()
    if assets.empty:
        return {}
    assets["abs_amount"] = assets["amount"].abs()
    floors = {}
    for row in (
        assets.sort_values("abs_amount", ascending=False)
        .drop_duplicates(["year", "fs_div"])
        .itertuples()
    ):
        floors[(int(row.year), str(row.fs_div))] = max(abs_min, abs(float(row.amount)) * pct / 100)
    return floors


def _scale_multiple(left: object, right: object) -> float:
    values = [abs(float(left)), abs(float(right))]
    high = max(values)
    low = min(value for value in values if value > 0) if any(value > 0 for value in values) else 0
    if low == 0:
        return float("inf") if high > 0 else 1.0
    return high / low


def _dedupe_signals(signals: list[RedFlagSignal]) -> list[RedFlagSignal]:
    seen = set()
    deduped = []
    for signal in signals:
        key = (
            signal.account,
            _fs_div_from_id(signal.id),
            signal.year,
            round(float(signal.metric_value), 2),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(signal)
    return deduped


def _fs_div_from_id(signal_id: str) -> str:
    parts = signal_id.rsplit(":", 3)
    return parts[1] if len(parts) >= 3 else ""


def _row_for_year(rows: pd.DataFrame, year: int) -> Any | None:
    matched = rows[rows["year"] == year]
    return None if matched.empty else next(matched.itertuples())


def _signal(current: Any, original: Any, diff: float, rel_pct: float) -> RedFlagSignal:
    account = _account_name(current)
    return RedFlagSignal(
        id=f"restatement:{current.scan_key}:{current.fs_div}:{current.sj_div}:{int(current.year)}",
        year=int(current.year),
        account=account,
        signal_type="restatement",
        description="전기 비교표시 금액과 전년도 공시 당기 금액 괴리",
        metric_value=round(float(diff), 2),
        evidence=[
            _evidence(
                str(current.evidence_key),
                int(current.year),
                f"prior_amount {int(float(current.prior_amount)):,}; "
                f"diff {int(float(diff)):,}; rel {rel_pct:.2f}%",
            ),
            _evidence(
                str(original.evidence_key),
                int(original.year),
                f"amount {int(float(original.amount)):,}",
            ),
        ],
        current_amount=float(current.prior_amount),
    )


def _account_name(row: Any) -> str:
    return str(row.label if row.canonical == "기타 중요 계정" else row.canonical)


def _evidence(locator: str, year: int, value: str) -> EvidenceRef:
    return EvidenceRef(source="financial_statement", locator=locator, year=str(year), value=value)
