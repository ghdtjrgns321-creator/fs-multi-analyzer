"""External context perspective for L4 multi-agent review."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.agents.context_brief import create_context_brief_for_query
from src.agents.gemini_retry import DEFAULT_RETRY_DELAYS
from src.report.perspectives import PerspectiveAssessment, deferred_assessment
from src.schemas.context import ContextBrief


async def create_external_assessment(
    report: dict[str, object],
    context_factory: Callable[..., Any] = create_context_brief_for_query,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> PerspectiveAssessment:
    """Build external perspective from Google-grounded ContextBrief only."""

    query = _query(report)
    try:
        brief = await context_factory(query, retry_delays=retry_delays)
    except TypeError:
        brief = await context_factory(query)
    except Exception as exc:
        return deferred_assessment("external", str(exc) or exc.__class__.__name__)
    if not brief.items:
        return PerspectiveAssessment(
            perspective="external",
            status="completed",
            risk_areas=[],
            risk_level="Low",
            summary="출처가 확인된 관련 외부 맥락 없음. 내부 위험은 그대로 유지한다.",
            evidence=[],
        )
    return PerspectiveAssessment(
        perspective="external",
        status="completed",
        risk_areas=_risk_areas(brief),
        risk_level="Low",
        summary=" / ".join(item.claim for item in brief.items[:3])
        + " 외부 맥락은 설명용이며 내부 위험을 약화하지 않는다.",
        evidence=[f"{item.source_title}: {item.source_url}" for item in brief.items],
    )


def _query(report: dict[str, object]) -> str:
    subjects = []
    for item in report["review_queue"][:6]:  # type: ignore[index]
        subject = str(item["subject"])  # type: ignore[index]
        if subject not in subjects:
            subjects.append(subject)
    return f"삼성전자 {report['target_year']} {' '.join(subjects)} 업황 뉴스"


def external_material(report: dict[str, object]) -> dict[str, object]:
    return {"query": _query(report), "scope": "external perspective only"}


def _risk_areas(brief: ContextBrief) -> list[str]:
    areas = []
    text = " ".join(item.claim for item in brief.items).lower()
    for area, aliases in {
        "매출채권/수익": ["매출채권", "수익", "revenue", "receivable"],
        "재고": ["재고", "inventory"],
        "현금흐름": ["현금흐름", "cash flow", "cashflow"],
        "유동성/차입": ["차입", "유동성", "borrow", "liquidity"],
    }.items():
        if any(alias in text for alias in aliases):
            areas.append(area)
    return areas
