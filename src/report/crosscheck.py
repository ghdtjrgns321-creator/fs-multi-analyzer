"""Deterministic cross-check for independent L4 perspective assessments."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.report.perspectives import PerspectiveAssessment


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
    shared = set(completed[0].risk_areas)
    for item in completed[1:]:
        shared &= set(item.risk_areas)
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
