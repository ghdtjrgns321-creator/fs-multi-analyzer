"""External context perspective for L4 multi-agent review."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from config.settings import settings
from src.agents.context_brief import create_context_brief_for_queries
from src.agents.gemini_retry import DEFAULT_RETRY_DELAYS
from src.report.external_agentic import (
    SearchKeywords,
    build_eval_agent,
    build_query_agent,
    evaluate_external_context,
    generate_search_keywords,
)
from src.report.perspectives import PerspectiveAssessment, deferred_assessment
from src.schemas.findings import IssueType
from src.schemas.suspicion import PerspectiveOutput, SuspicionItem


async def create_external_assessment(
    report: dict[str, object],
    context_factory: Callable[..., Any] = create_context_brief_for_queries,
    query_agent_factory: Callable[..., Any] | None = None,
    eval_agent_factory: Callable[..., Any] | None = None,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> PerspectiveAssessment:
    """Generate queries, search with grounding, then evaluate sourced context."""

    keywords = _fallback_keywords(report)
    try:
        keywords = await _keywords(report, query_agent_factory, retry_delays)
        brief = await context_factory(keywords.queries, retry_delays=retry_delays)
        assessment = await _evaluate(brief, eval_agent_factory, retry_delays)
    except TypeError:
        brief = await context_factory(_fallback_keywords(report).queries)
        assessment = _empty_assessment() if not brief.items else _legacy_assessment(brief)
    except Exception as exc:
        return deferred_assessment("external", str(exc) or exc.__class__.__name__)
    assessment.evidence = [f"검색어: {query}" for query in keywords.queries] + assessment.evidence
    return assessment


async def run_external_suspicions(
    report: dict[str, object],
    query_agent_factory: Callable[..., Any] | None = None,
    context_factory: Callable[..., Any] = create_context_brief_for_queries,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> PerspectiveOutput:
    """Phase2 구조화 external — 검색어(Gemini)→구글 grounding 검색→출처 있는 SuspicionItem.

    검색결과(출처 URL 확보된 item)만 company-scope 의심건으로 변환한다. URL 없는 항목은 애초에
    안 만든다(grounding 탈락 유발 방지). 외부는 설명용이라 risk=Low·issue_type=기타(내부위험 안 키움).
    실검색 경로인데 키 없음=deferred, 검색·변환 실패=failed(§9: 0건이 '위험 없음'으로 둔갑 금지)."""

    uses_real_search = context_factory is create_context_brief_for_queries
    if uses_real_search and not settings.google_api_key:
        return PerspectiveOutput(status="deferred")
    try:
        keywords = await generate_search_keywords(
            external_material(report),
            agent_factory=query_agent_factory or build_query_agent,
            retry_delays=retry_delays,
        )
        brief = await context_factory(keywords.queries, retry_delays=retry_delays)
    except Exception:
        return PerspectiveOutput(status="failed")
    year = str(report.get("target_year", ""))
    suspicions = [
        SuspicionItem(
            perspective="external",
            scope="company",
            issue_type=IssueType.OTHER,
            subtype="외부 맥락",
            year=year,
            description=item.claim,
            source_url=str(item.source_url),
            risk_level="Low",
        )
        for item in brief.items
        if item.source_url and str(item.source_url).startswith("http")
    ]
    return PerspectiveOutput(status="completed", suspicions=suspicions)


async def _keywords(
    report: dict[str, object],
    agent_factory: Callable[..., Any] | None,
    retry_delays: tuple[float, ...],
) -> SearchKeywords:
    if not agent_factory and not _has_google_key():
        return _fallback_keywords(report)
    return await generate_search_keywords(
        external_material(report),
        agent_factory=agent_factory or build_query_agent,
        retry_delays=retry_delays,
    )


async def _evaluate(
    brief: Any,
    agent_factory: Callable[..., Any] | None,
    retry_delays: tuple[float, ...],
) -> PerspectiveAssessment:
    if not brief.items:
        return _empty_assessment()
    return await evaluate_external_context(
        brief,
        agent_factory=agent_factory or build_eval_agent,
        retry_delays=retry_delays,
    )


def external_material(report: dict[str, object]) -> dict[str, object]:
    return {
        "company_name": report.get("company_name", report.get("corp_code", "")),
        "business_domain": report.get("business_domain", {}),
        "target_year": report["target_year"],
        "review_queue": report["review_queue"][:5],  # type: ignore[index]
        "ratio_summary": report["ratio_summary"],
        "latest_signal_snapshot": report.get("latest_signal_snapshot", {}),
        "scope": "external query generation only",
    }


def _fallback_keywords(report: dict[str, object]) -> SearchKeywords:
    company = str(report.get("company_name", report.get("corp_code", "")))
    year = str(report["target_year"])
    subjects = [
        str(item["subject"])
        for item in report.get("review_queue", [])[:2]  # type: ignore[index]
        if item.get("subject")  # type: ignore[union-attr]
    ]
    topic = " ".join(subjects) if subjects else "재무지표 변화 원인"
    return SearchKeywords(queries=[f"{company} {year} {topic}"])


def _empty_assessment() -> PerspectiveAssessment:
    return PerspectiveAssessment(
        perspective="external",
        status="completed",
        risk_areas=[],
        risk_level="Low",
        summary="출처가 확인된 관련 외부 맥락 없음. 내부 위험은 그대로 유지한다.",
        evidence=[],
    )


def _legacy_assessment(brief: Any) -> PerspectiveAssessment:
    return PerspectiveAssessment(
        perspective="external",
        status="completed",
        risk_areas=[],
        risk_level="Low",
        summary=" / ".join(item.claim for item in brief.items[:3])
        + " 외부 맥락은 설명용이며 내부 위험을 약화하지 않는다.",
        evidence=[f"{item.source_title}: {item.source_url}" for item in brief.items],
    )


def _has_google_key() -> bool:

    return bool(settings.google_api_key)
