"""외부 검증 에이전트 — 카드 확정 후 상위 카드를 타깃 검색해 외부 근거를 붙인다 (PLAN §5).

external을 '막연한 발견자'에서 '카드별 검증자'로 재배치: 분해 결론(주도 요인)을 검색
쿼리 재료로 써서 "○○사 2025 영업이익 급감 매출 감소 원인" 같은 좁은 검색을 한다.
검색은 기존 Gemini+구글 grounding 경로(create_context_brief_for_queries) 재사용.
출처 URL 없는 항목은 버린다(환각 차단). 못 찾은 것도 checked=True로 기록(빈손 은폐 금지).
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from typing import Any

from config.settings import settings
from src.agents.context_brief import create_context_brief_for_queries
from src.schemas.findings import AccountFinding, ExternalRef

# 폭주 방지 안전핀(설정 폴백) — 선정 기준이 아니다. 선정은 목적 기준(조사 미해결 전부).
EXTERNAL_HARD_CAP = 30
_MAX_REFS_PER_CARD = 3


def external_hard_cap(config: dict | None = None) -> int:
    """안전핀 상한 — config/investigation.yaml external.hard_cap(없으면 폴백 30)."""

    from src.report.investigation_config import load_investigation_config

    cfg = config if config is not None else load_investigation_config()
    return int((cfg.get("external") or {}).get("hard_cap", EXTERNAL_HARD_CAP))


def select_external_targets(
    cards: list[AccountFinding],
    hard_cap: int | None = None,
) -> list[AccountFinding]:
    """검색 대상 = 조사 미해결 카드 전부. 조사로 원인이 설명된 카드는 검색하지 않는다.

    조사 실패·미수행(None)은 미확인이라 포함한다 — 확인 못 한 것을 해결로 두지 않는다.
    순서는 화면·리포트와 같은 사전식 정렬(card_order — 표수 → 금액)이고,
    hard_cap은 선정 기준이 아니라 폭주 방지 안전핀이다."""

    from src.report.card_order import order_cards

    cap = hard_cap if hard_cap is not None else external_hard_cap()
    targets = [
        c
        for c in order_cards(cards)
        if not (getattr(c, "investigation", None) is not None and c.investigation.resolved)
    ]
    return targets[: max(cap, 0)]


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


# ── 설계4a: 외부 인용 금액 ↔ 내부 공시값 대사 ─────────────────────────────
# 외부 figures는 "1,478억"·"4조 2,810억" 같은 통제된 금액 표기(structured output).
# 산문 파싱이 아니라 금액 표기의 결정론 해석 — 원 단위로 환산해 유효숫자로 대조한다.
_COMPOSITE_JO = re.compile(r"([\d,]+)\s*조\s*([\d,]+(?:\.\d+)?)\s*억")
_JO_ONLY = re.compile(r"([\d,]+(?:\.\d+)?)\s*조")
_EOK_ONLY = re.compile(r"([\d,]+(?:\.\d+)?)\s*억")
_MILLION = re.compile(r"([\d,]+(?:\.\d+)?)\s*백만")
_PLAIN = re.compile(r"[\d,]{6,}")


def _num(text: str) -> float:
    return float(text.replace(",", ""))


def figure_to_won(figure: str) -> float | None:
    """외부 인용 금액 문자열 → 원 단위. 해석 불가면 None(대조불가)."""

    text = str(figure or "").strip()
    if match := _COMPOSITE_JO.search(text):
        return _num(match.group(1)) * 1e12 + _num(match.group(2)) * 1e8
    if match := _JO_ONLY.search(text):
        return _num(match.group(1)) * 1e12
    if match := _EOK_ONLY.search(text):
        return _num(match.group(1)) * 1e8
    if match := _MILLION.search(text):
        return _num(match.group(1)) * 1e6
    if match := _PLAIN.search(text):
        return _num(match.group(0))
    return None


def internal_amount_sigs(report: dict[str, object]) -> set[str]:
    """내부 공시값(계정 시계열 + 주석 fact) 원 단위 절대값 풀 — 외부 수치 대조의 정답."""

    from src.report.grounding import _note_value_sig, _sig_amount

    sigs: set[str] = set()
    for row in report.get("account_level_series") or []:  # type: ignore[union-attr]
        try:
            sigs.add(_sig_amount(float(row.get("amount"))))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
    for fact in report.get("note_facts") or []:  # type: ignore[union-attr]
        sig = _note_value_sig(fact.get("value"))
        if sig:
            sigs.add(sig)
    return sigs


def check_figures(figures: list[str], internal_sigs: set[str]) -> str:
    """외부 인용 금액 전부가 내부 공시값과 일치하면 match, 하나라도 다르면 mismatch.

    해석 가능한 수치가 없으면 uncheckable. mismatch는 삭제가 아니라 마킹 —
    UI가 "외부 주장(공시와 상이)"로 구분 표시한다(silent 저장 금지, 결함④-a)."""

    from src.report.grounding import _matches_scaled

    # 외부 인용은 '1,478억'처럼 반올림돼 오므로 자릿수는 맞추되 허용오차 안에서 본다
    # (grounding과 같은 기준 — 유효숫자 대조를 쓰면 1,478억과 1,478백만이 같아진다).
    wons = [won for figure in figures or [] if (won := figure_to_won(str(figure))) is not None]
    if not wons:
        return "uncheckable"
    return "match" if all(_matches_scaled([won], internal_sigs) for won in wons) else "mismatch"


async def resolve_final_url(url: str, timeout: float = 5.0) -> str:
    """리다이렉트 URL(vertexaisearch 등)을 원 기사 주소로 해소(설계4c). 실패는 원본 유지."""

    try:
        import httpx

        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            async with client.stream("GET", url) as response:
                final = str(response.url)
        return final or url
    except Exception:
        return url  # 해소 실패 — 현행 URL 유지(출처 도메인은 source 제목에 보존)


async def verify_cards(
    cards: list[AccountFinding],
    report: dict[str, object],
    decompositions: dict[str, dict] | None = None,
    hard_cap: int | None = None,  # None이면 config external.hard_cap(안전핀, 선정 기준 아님)
    context_factory: Callable[..., Any] = create_context_brief_for_queries,
    url_resolver: Callable[[str], Any] | None = None,
) -> dict:
    """상위 카드 외부 검증 — external_evidence 채움 + checked 마킹. 키 없음은 deferred.

    실패한 카드는 checked=False 유지(미수행으로 표시 — 실패를 '미발견'으로 둔갑 금지).
    외부 요약의 인용 금액은 내부 공시값과 대조해 figure_check로 마킹한다(결함④-a).
    """

    uses_real_search = context_factory is create_context_brief_for_queries
    if uses_real_search and not settings.google_api_key:
        return {"status": "deferred", "verified": 0, "found": 0}
    # 리다이렉트 해소는 실검색 경로에서만 기본 활성(단위테스트 stub에 네트워크 금지).
    resolver = (
        url_resolver
        if url_resolver is not None
        else (resolve_final_url if uses_real_search else None)
    )

    company = str(report.get("company_name", report.get("corp_code", "")))
    year = report.get("target_year", "")
    decompositions = decompositions or {}
    targets = select_external_targets(cards, hard_cap)
    internal_sigs = internal_amount_sigs(report)

    async def _external_ref(item: Any) -> ExternalRef:
        url = str(item.source_url)
        if resolver is not None:
            url = str(await resolver(url))
        figures = [str(f) for f in (getattr(item, "figures", []) or [])]
        return ExternalRef(
            summary=str(item.claim),
            url=url,
            source=str(getattr(item, "source_title", "") or ""),
            claimed_figures=figures,
            figure_check=check_figures(figures, internal_sigs),
        )

    async def _verify_one(card: AccountFinding) -> bool:
        queries = card_queries(company, year, card, decompositions.get(card.cluster_key or ""))
        try:
            brief = await context_factory(queries)
        except Exception:
            return False  # 실패 — checked 미설정(미수행 표기 유지)
        card.external_evidence = [
            await _external_ref(item)
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


__all__ = [
    "EXTERNAL_HARD_CAP",
    "card_queries",
    "check_figures",
    "figure_to_won",
    "internal_amount_sigs",
    "resolve_final_url",
    "select_external_targets",
    "verify_cards",
]
