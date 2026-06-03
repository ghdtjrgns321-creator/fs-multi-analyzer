"""Deterministic L4 integrated report assembly."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from src.schemas.findings import AccountFinding
from src.signals.red_flags import RedFlagSignal

RISK_ORDER = {"High": 3, "Medium": 2, "Low": 1}
CATEGORY_LABELS = {
    "profitability": "수익성",
    "activity": "활동성",
    "stability": "안정성",
    "earnings_quality": "이익의 질",
}


@dataclass(frozen=True)
class ReviewItem:
    subject: str
    item_type: str
    issue: str
    risk_level: str
    materiality_score: float
    key_evidence: str
    audit_basis: list[str]
    source_url: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_review_queue(
    findings: list[AccountFinding],
    ratios: pd.DataFrame,
    ratio_config: list[dict[str, Any]],
    target_year: int,
    red_flags: list[RedFlagSignal] | None = None,
    unmapped_rows: list[dict[str, object]] | None = None,
) -> list[ReviewItem]:
    """Collect account findings, relationship signals, and ratios into one queue."""

    items = [_finding_item(finding) for finding in findings]
    items.extend(_red_flag_item(signal) for signal in red_flags or [])
    items.extend(_unmapped_item(row) for row in unmapped_rows or [])
    items.extend(_ratio_items(ratios, ratio_config, target_year))
    return sorted(
        items,
        key=lambda item: (RISK_ORDER.get(item.risk_level, 0), item.materiality_score),
        reverse=True,
    )


def summarize_ratio_categories(
    ratios: pd.DataFrame,
    target_year: int,
) -> dict[str, dict[str, float]]:
    """Return latest computed ratios grouped by category."""

    latest = ratios[(ratios["year"] == target_year) & (ratios["value"].notna())]
    summary: dict[str, dict[str, float]] = {}
    for row in latest.itertuples():
        category = CATEGORY_LABELS.get(str(row.category), str(row.category))
        summary.setdefault(category, {})[str(row.name)] = float(row.value)
    return summary


def payload_for_summary(
    queue: list[ReviewItem],
    ratio_summary: dict[str, dict[str, float]],
) -> dict[str, object]:
    """Serialize deterministic report inputs for the LLM summary."""

    return {
        "rules": [
            "외부 사실을 단정하지 않는다.",
            "분식 또는 부정을 확정하지 않는다.",
            "사슬 밖 연결은 실제 데이터에 근거한 가능성으로만 표현한다.",
        ],
        "review_queue": [item.to_dict() for item in queue[:8]],
        "ratio_summary": ratio_summary,
    }


def _finding_item(finding: AccountFinding) -> ReviewItem:
    evidence = finding.numeric_evidence or finding.flow_evidence or finding.note_evidence
    key = evidence[0].value if evidence else "근거 위치 확인 필요"
    basis = ["ISA/KSA 315", "ISA/KSA 500", "ISA/KSA 520"]
    return ReviewItem(
        subject=finding.account,
        item_type="account_finding",
        issue=finding.issue_type.value,
        risk_level=finding.risk_level,
        materiality_score=round(float(finding.materiality_score), 2),
        key_evidence=str(key),
        audit_basis=basis,
    )


def _red_flag_item(signal: RedFlagSignal) -> ReviewItem:
    metric = signal.metric_value
    score = abs(float(metric)) if isinstance(metric, int | float) else 1.0
    return ReviewItem(
        subject=signal.account,
        item_type="relationship_signal",
        issue=signal.description,
        risk_level="Medium" if score >= 15 else "Low",
        materiality_score=round(score, 2),
        key_evidence=f"{signal.signal_type}: {metric}",
        audit_basis=["ISA/KSA 315", "ISA/KSA 520"],
    )


def _unmapped_item(row: dict[str, object]) -> ReviewItem:
    amount = abs(float(row.get("amount") or 0.0))
    return ReviewItem(
        subject=str(row.get("label") or "기타 중요 계정"),
        item_type="unmapped_material_account",
        issue="미등록 중요 계정",
        risk_level="Low",
        materiality_score=round(amount, 2),
        key_evidence=f"{row.get('year')}: {int(float(row.get('amount') or 0.0)):,}",
        audit_basis=["ISA/KSA 315", "ISA/KSA 500"],
    )


def _ratio_items(
    ratios: pd.DataFrame,
    ratio_config: list[dict[str, Any]],
    target_year: int,
) -> list[ReviewItem]:
    config = {str(item["id"]): item for item in ratio_config}
    latest = ratios[(ratios["year"] == target_year) & (ratios["value"].notna())]
    items = []
    for row in latest.itertuples():
        item = config.get(str(row.id), {})
        source = item.get("source") or {}
        items.append(
            ReviewItem(
                subject=str(row.name),
                item_type="financial_ratio",
                issue=f"{CATEGORY_LABELS.get(str(row.category), row.category)} 지표",
                risk_level="Low",
                materiality_score=round(abs(float(row.value)), 2),
                key_evidence=f"{target_year}: {float(row.value):.2f}",
                audit_basis=list(item.get("audit_basis", ["ISA/KSA 520"])),
                source_url=source.get("url") if isinstance(source, dict) else None,
            )
        )
    return items
