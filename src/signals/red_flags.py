"""Apply configured thresholds to deterministic L2 tables."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.settings import settings
from src.normalize.config import load_canonical_accounts, subtotal_account_names
from src.schemas.findings import EvidenceRef
from src.signals.config import load_l2_config


@dataclass(frozen=True)
class RedFlagSignal:
    id: str
    year: int
    account: str
    signal_type: str
    description: str
    metric_value: float | str
    evidence: list[EvidenceRef]
    track: str | None = None
    magnitude_ratio: float | None = None
    current_amount: float | None = None
    sj_div: str | None = None


def extract_red_flags(
    report: dict[str, object],
    target_year: int,
    include_all: bool = False,
) -> list[RedFlagSignal]:
    """Extract configured red-flag signals for one year."""

    thresholds = report.get("signal_thresholds") or load_l2_config()["signal_thresholds"]
    asset_totals = (
        report.get("asset_totals") if isinstance(report.get("asset_totals"), dict) else {}
    )
    signals: list[RedFlagSignal] = []
    account_statements = _canonical_statement_map()
    signals.extend(
        _growth_divergence_flags(
            report["growth_divergences"],
            target_year,
            thresholds,
            asset_totals,
            account_statements,
        )
    )
    signals.extend(
        _single_yoy_flags(
            report["primary_yoy"],
            target_year,
            thresholds,
            asset_totals,
            account_statements,
        )
    )
    signals.extend(
        _direction_flags(report, target_year, thresholds, asset_totals, account_statements)
    )
    # ② 채점/랭킹(track quota) 제거: 신호를 materiality 순으로 전부 반환(선택·할당 없음).
    return sorted(signals, key=_score, reverse=True)


def _growth_divergence_flags(
    frame: pd.DataFrame,
    year: int,
    thresholds: dict,
    asset_totals: dict,
    account_statements: dict[str, str],
) -> list[RedFlagSignal]:
    required = {
        "year",
        "divergence_pp",
        "id",
        "name",
        "account_a",
        "account_b",
        "current_amount_b",
        "growth_a_pct",
        "growth_b_pct",
    }
    if frame.empty or not required.issubset(frame.columns):
        return []
    divergence = pd.to_numeric(frame["divergence_pp"], errors="coerce")
    flagged = frame[
        (frame["year"] == year) & (divergence.abs() >= float(thresholds["divergence_pp_abs"]))
    ]
    signals = []
    for row in flagged.itertuples():
        current_amount = _numeric_or_none(row.current_amount_b)
        signals.append(
            RedFlagSignal(
                id=f"divergence:{row.id}:{year}",
                year=year,
                account=row.account_b,
                signal_type="growth_divergence",
                description=row.name,
                metric_value=float(row.divergence_pp),
                evidence=[
                    _evidence(row.account_a, year, f"YoY {row.growth_a_pct:.2f}%"),
                    _evidence(row.account_b, year, f"YoY {row.growth_b_pct:.2f}%"),
                    _evidence(row.id, year, f"divergence {row.divergence_pp:.2f}pp"),
                ],
                current_amount=current_amount,
                sj_div=account_statements.get(str(row.account_b)),
            )
        )
    return signals


def _single_yoy_flags(
    frame: pd.DataFrame,
    year: int,
    thresholds: dict,
    asset_totals: dict,
    account_statements: dict[str, str],
) -> list[RedFlagSignal]:
    required = {"year", "canonical", "amount", "yoy_growth_pct"}
    if frame.empty or not required.issubset(frame.columns):
        return []
    growth = pd.to_numeric(frame["yoy_growth_pct"], errors="coerce")
    mask = (frame["year"] == year) & (growth.abs() >= float(thresholds["yoy_pct_abs"]))
    if "sj_div" in frame.columns:
        mask &= frame["sj_div"] != "CF"
    if "valid_yoy_base" in frame.columns:
        mask &= frame["valid_yoy_base"].fillna(False).astype(bool)
    subtotals = subtotal_account_names(settings.config_dir / "canonical_accounts.yaml")
    if subtotals:
        mask &= ~frame["canonical"].isin(subtotals)
    flagged = frame[mask]
    signals = []
    for row in flagged.itertuples():
        current_amount = _numeric_or_none(row.amount)
        signals.append(
            RedFlagSignal(
                id=f"yoy:{row.canonical}:{year}",
                year=year,
                account=row.canonical,
                signal_type="single_account_yoy",
                description=f"{row.canonical} YoY 절대값 기준 초과",
                metric_value=float(row.yoy_growth_pct),
                evidence=[
                    _evidence(row.canonical, year, f"amount {int(row.amount):,}"),
                    _evidence(row.canonical, year, f"YoY {row.yoy_growth_pct:.2f}%"),
                ],
                current_amount=current_amount,
                sj_div=account_statements.get(str(row.canonical), getattr(row, "sj_div", None)),
            )
        )
    return signals


def _direction_flags(
    report: dict[str, object],
    year: int,
    thresholds: dict,
    asset_totals: dict,
    account_statements: dict[str, str],
) -> list[RedFlagSignal]:
    yoy = report["primary_yoy"]
    if not isinstance(yoy, pd.DataFrame) or yoy.empty:
        return []
    if not {"canonical", "year", "yoy_growth_pct"}.issubset(yoy.columns):
        return []
    rows = []
    for rule in thresholds["direction_red_flags"]:
        left = _direction_for(yoy, rule["account_a"], year)
        right = _direction_for(yoy, rule["account_b"], year)
        if left == rule["direction_a"] and right == rule["direction_b"]:
            current_amount = _amount_for(yoy, rule["account_b"], year)
            rows.append(
                RedFlagSignal(
                    id=f"direction:{rule['id']}:{year}",
                    year=year,
                    account=rule["account_b"],
                    signal_type="direction_mismatch",
                    description=rule["name"],
                    metric_value=f"{left}/{right}",
                    evidence=[
                        _evidence(rule["account_a"], year, f"direction {left}"),
                        _evidence(rule["account_b"], year, f"direction {right}"),
                    ],
                    current_amount=current_amount,
                    sj_div=account_statements.get(str(rule["account_b"])),
                )
            )
    return rows


def _direction_for(frame: pd.DataFrame, account: str, year: int) -> str:
    matched = frame[(frame["canonical"] == account) & (frame["year"] == year)]
    if matched.empty:
        return "missing"
    value = matched.iloc[0].yoy_growth_pct
    if pd.isna(value):
        return "missing"
    if value > 0:
        return "increase"
    if value < 0:
        return "decrease"
    return "flat"


def _amount_for(frame: pd.DataFrame, account: str, year: int) -> float | None:
    matched = frame[(frame["canonical"] == account) & (frame["year"] == year)]
    if matched.empty or "amount" not in matched.columns:
        return None
    return _numeric_or_none(matched.iloc[0].amount)


def _canonical_statement_map() -> dict[str, str]:
    return {
        account.name: account.statement
        for account in load_canonical_accounts(settings.config_dir / "canonical_accounts.yaml")
    }


def _numeric_or_none(value: object) -> float | None:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(parsed) else float(parsed)


def _score(signal: RedFlagSignal) -> float:
    if not isinstance(signal.metric_value, int | float):
        return 0.0
    thresholds = load_l2_config()["signal_thresholds"]
    threshold = {
        "single_account_yoy": thresholds.get("yoy_pct_abs"),
        "growth_divergence": thresholds.get("divergence_pp_abs"),
        "direction_mismatch": 1,
    }.get(signal.signal_type)
    if not isinstance(threshold, int | float) or float(threshold) == 0:
        return abs(float(signal.metric_value))
    return abs(float(signal.metric_value)) / float(threshold)


def _evidence(locator: str, year: int, value: str) -> EvidenceRef:
    source = "cash_flow" if "현금흐름" in locator else "financial_statement"
    return EvidenceRef(source=source, locator=locator, year=str(year), value=value)
