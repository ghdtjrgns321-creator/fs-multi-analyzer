"""Deterministic cross-check for independent L4 perspective assessments."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.report.perspectives import PerspectiveAssessment

RISK_SYNONYMS = {
    "매출채권/수익": ["매출채권", "수익", "receivable", "revenue"],
    "재고": ["재고", "inventory"],
    "현금흐름": ["현금흐름", "cash flow", "cashflow"],
    "유동성/차입": ["차입", "유동성", "borrow", "liquidity", "short-term financial"],
}


class CrossCheckResult(BaseModel):
    verdict: Literal["agreement", "conflict", "insufficient"]
    risk_area: str
    perspectives: list[str]
    comment: str


def cross_check_assessments(assessments: list[PerspectiveAssessment]) -> list[CrossCheckResult]:
    """Compare independent assessments for explicit agreement/conflict."""

    completed = [item for item in assessments if item.status == "completed"]
    if len(completed) < 2:
        return [
            CrossCheckResult(
                verdict="insufficient",
                risk_area="관점 평가",
                perspectives=[item.perspective for item in assessments],
                comment="완료된 독립 관점이 2개 미만이라 일치/충돌 판정은 보류한다.",
            )
        ]
    normalized = [_normalized_areas(item) for item in completed]
    shared = set(normalized[0])
    for areas in normalized[1:]:
        shared &= set(areas)
    if shared:
        area = sorted(shared)[0]
        return [
            CrossCheckResult(
                verdict="agreement",
                risk_area=area,
                perspectives=[item.perspective for item in completed],
                comment=f"{area}에 대해 독립 관점이 같은 방향을 가리켜 신호 강화로 본다.",
            )
        ]
    risky = [item for item in completed if item.risk_level in {"High", "Medium"}]
    quiet = [item for item in completed if not item.risk_areas or item.risk_level == "Low"]
    if risky and quiet:
        area = risky[0].risk_areas[0] if risky[0].risk_areas else "미특정 위험"
        return [
            CrossCheckResult(
                verdict="conflict",
                risk_area=area,
                perspectives=[item.perspective for item in completed],
                comment=f"{area}는 한 관점에서 위험이나 다른 관점은 주석 잠잠 또는 낮은 위험이다.",
            )
        ]
    return [
        CrossCheckResult(
            verdict="insufficient",
            risk_area="공통 위험 없음",
            perspectives=[item.perspective for item in completed],
            comment="공통 risk_area가 없어 추가 근거 확인이 필요하다.",
        )
    ]


def _normalized_areas(assessment: PerspectiveAssessment) -> list[str]:
    areas = []
    for area in [*assessment.risk_areas, assessment.summary]:
        text = area.lower()
        matched = False
        for canonical, aliases in RISK_SYNONYMS.items():
            if any(alias.lower() in text for alias in aliases):
                areas.append(canonical)
                matched = True
        if not matched:
            areas.append(area)
    return areas
