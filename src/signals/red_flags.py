"""Apply configured thresholds to deterministic L2 tables."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

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


def extract_red_flags(report: dict[str, object], target_year: int) -> list[RedFlagSignal]:
    """Extract configured red-flag signals for one year."""

    thresholds = report.get("signal_thresholds") or load_l2_config()["signal_thresholds"]
    signals: list[RedFlagSignal] = []
    signals.extend(_growth_divergence_flags(report["growth_divergences"], target_year, thresholds))
    signals.extend(_single_yoy_flags(report["primary_yoy"], target_year, thresholds))
    signals.extend(_direction_flags(report, target_year, thresholds))
    return signals


def _growth_divergence_flags(
    frame: pd.DataFrame,
    year: int,
    thresholds: dict,
) -> list[RedFlagSignal]:
    flagged = frame[
        (frame["year"] == year)
        & (frame["divergence_pp"].abs() >= float(thresholds["divergence_pp_abs"]))
    ]
    return [
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
        )
        for row in flagged.itertuples()
    ]


def _single_yoy_flags(frame: pd.DataFrame, year: int, thresholds: dict) -> list[RedFlagSignal]:
    growth = pd.to_numeric(frame["yoy_growth_pct"], errors="coerce")
    flagged = frame[(frame["year"] == year) & (growth.abs() >= float(thresholds["yoy_pct_abs"]))]
    return [
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
        )
        for row in flagged.itertuples()
    ]


def _direction_flags(report: dict[str, object], year: int, thresholds: dict) -> list[RedFlagSignal]:
    yoy = report["primary_yoy"]
    rows = []
    for rule in thresholds["direction_red_flags"]:
        left = _direction_for(yoy, rule["account_a"], year)
        right = _direction_for(yoy, rule["account_b"], year)
        if left == rule["direction_a"] and right == rule["direction_b"]:
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
                )
            )
    return rows


def _direction_for(frame: pd.DataFrame, account: str, year: int) -> str:
    value = frame[(frame["canonical"] == account) & (frame["year"] == year)].iloc[0].yoy_growth_pct
    if pd.isna(value):
        return "missing"
    if value > 0:
        return "increase"
    if value < 0:
        return "decrease"
    return "flat"


def _evidence(locator: str, year: int, value: str) -> EvidenceRef:
    source = "cash_flow" if "현금흐름" in locator else "financial_statement"
    return EvidenceRef(source=source, locator=locator, year=str(year), value=value)
