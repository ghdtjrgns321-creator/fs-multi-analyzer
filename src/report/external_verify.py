"""외부 검증 에이전트 — 카드 확정 후 상위 카드를 타깃 검색해 외부 근거를 붙인다 (PLAN §5).

external을 '막연한 발견자'에서 '카드별 검증자'로 재배치: 분해 결론(주도 요인)을 검색
쿼리 재료로 써서 "○○사 2025 영업이익 급감 매출 감소 원인" 같은 좁은 검색을 한다.
검색은 기존 Gemini+구글 grounding 경로(create_context_brief_for_queries) 재사용.
출처 URL 없는 항목은 버린다(환각 차단). 못 찾은 것도 checked=True로 기록(빈손 은폐 금지).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from config.settings import settings
from src.agents.context_brief import create_context_brief_for_queries
from src.schemas.findings import AccountFinding, ExternalRef

# 타깃 검색 기본 카드 수 + High 전수 포함 시 절대 상한(비용 가드). 나머지는 '미수행' 표기.
EXTERNAL_TOP_N = 5
EXTERNAL_HARD_CAP = 10
_RISK_ORDER = {"High": 2, "Medium": 1, "Low": 0}
_MAX_REFS_PER_CARD = 3


def select_top_cards(
    cards: list[AccountFinding], top_n: int = EXTERNAL_TOP_N
) -> list[AccountFinding]:
    """검색 대상 — **High 위험 카드는 전부**(상한 EXTERNAL_HARD_CAP) + 유의성순으로 top_n까지 채움.

    High인데 유의성 정규화 점수가 낮아 밀려나는 사각 방지(High=사람이 반드시 볼 카드 —
    외부 근거도 붙어야 한다). Medium 이하는 top_n 여유분만.
    """

    ranked = sorted(
        cards,
        key=lambda c: (_RISK_ORDER.get(str(c.risk_level), 0), c.materiality_score or 0.0),
        reverse=True,
    )
    highs = [c for c in ranked if str(c.risk_level) == "High"][:EXTERNAL_HARD_CAP]
    selected = list(highs)
    for card in ranked:  # High가 top_n 미만이면 유의성순으로 채움
        if len(selected) >= max(top_n, len(highs)):
            break
        if card not in selected:
            selected.append(card)
    return selected[:EXTERNAL_HARD_CAP]


def card_queries(
    company: str, year: object, card: AccountFinding, decomposition: dict | None = None
) -> list[str]:
    """카드 1장의 타깃 검색 쿼리(≤2) — 계정·부제 + 분해 주도 요인을 검색어로."""

    from dashboard.card_data import split_series_key, waterfall_leaves

    _, account = split_series_key(str(card.account or ""))
    subject = account if account != "(회사 전체)" else ""
    subtype = str(card.subtype or "").strip()
    queries = [" ".join(str(t) for t in (company, year, subject, subtype, "원인") if t)]
    if decomposition:
        leaves = [(n, d) for n, d in waterfall_leaves(decomposition) if n != "미설명 잔차" and d]
        if leaves:
            driver = min(leaves, key=lambda x: x[1])[0]  # 최대 하락 주도 요인
            queries.append(
                " ".join(str(t) for t in (company, year, subject, driver, "감소 원인") if t)
            )
    # 중복 제거(주도 요인이 subject와 같은 경우 등)
    unique: list[str] = []
    for q in queries:
        if q not in unique:
            unique.append(q)
    return unique[:2]


async def verify_cards(
    cards: list[AccountFinding],
    report: dict[str, object],
    decompositions: dict[str, dict] | None = None,
    top_n: int = EXTERNAL_TOP_N,
    context_factory: Callable[..., Any] = create_context_brief_for_queries,
) -> dict:
    """상위 카드 외부 검증 — external_evidence 채움 + checked 마킹. 키 없음은 deferred.

    실패한 카드는 checked=False 유지(미수행으로 표시 — 실패를 '미발견'으로 둔갑 금지).
    """

    uses_real_search = context_factory is create_context_brief_for_queries
    if uses_real_search and not settings.google_api_key:
        return {"status": "deferred", "verified": 0, "found": 0}

    company = str(report.get("company_name", report.get("corp_code", "")))
    year = report.get("target_year", "")
    decompositions = decompositions or {}
    targets = select_top_cards(cards, top_n)

    async def _verify_one(card: AccountFinding) -> bool:
        queries = card_queries(company, year, card, decompositions.get(card.cluster_key or ""))
        try:
            brief = await context_factory(queries)
        except Exception:
            return False  # 실패 — checked 미설정(미수행 표기 유지)
        card.external_evidence = [
            ExternalRef(
                summary=str(item.claim),
                url=str(item.source_url),
                source=str(getattr(item, "source_title", "") or ""),
            )
            for item in (brief.items or [])[:_MAX_REFS_PER_CARD]
            if item.source_url and str(item.source_url).startswith("http")
        ]
        card.external_checked = True
        return True

    results = await asyncio.gather(*[_verify_one(c) for c in targets])
    return {
        "status": "completed",
        "verified": sum(results),
        "found": sum(1 for c in targets if c.external_evidence),
    }


__all__ = ["EXTERNAL_TOP_N", "card_queries", "select_top_cards", "verify_cards"]
