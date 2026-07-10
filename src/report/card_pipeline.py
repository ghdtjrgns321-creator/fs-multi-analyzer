"""Phase2 카드 파이프라인 — PHASE2_DESIGN §9 (S5 배선).

6관점을 병렬 실행해 구조화 의심건을 모으고, 근거검증(S2)→클러스터·집계(S3)→정렬·렌더(S4)로
의심건 카드 목록을 만든다. 반박(S6)·구경로 제거(S7)는 후속 단계.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from src.report.card_builder import build_cards, cluster_suspicions
from src.report.card_report import build_card_report, render_card_markdown
from src.report.grounding import build_account_index, verify_suspicions
from src.report.investigator import run_investigation
from src.report.perspective_runner import (
    ALL_PERSPECTIVES,
    collect_perspective_materials,
    run_structured_perspective,
)
from src.report.rebuttal import apply_rebuttal, run_rebuttal
from src.schemas.suspicion import PerspectiveOutput, SuspicionItem


def _accounts_reviewed(report: dict[str, object]) -> int:
    rows = report.get("account_level_series", []) or []
    return len({str(row.get("series_key")) for row in rows if row.get("series_key")})  # type: ignore[union-attr]


def _note_disclosures(note_material: dict) -> list[dict]:
    """note material의 서술형 공시(note_sections·report_extracts)를 grounding 색인용으로 정규화.

    각 공시를 {tokens, text}로 — tokens는 앵커 후보(계정·라벨·파트), text는 금액 추출 대상.
    담보·특수관계 등 XBRL fact에 없는 Layer 1 서술 추출을 grounding에 닿게 한다(사각#3)."""

    out: list[dict] = []
    for sec in note_material.get("note_sections", []) or []:
        tokens = [sec.get("account", ""), *(sec.get("matched_keywords", []) or [])]
        text = f"{sec.get('title', '')} {sec.get('excerpt', '')}"
        out.append({"tokens": [t for t in tokens if t], "text": text})
    for item in note_material.get("report_extracts", []) or []:
        tokens = [str(item.get("label", "")), str(item.get("part", ""))]
        text = " ".join(str(item.get(k, "")) for k in ("statement", "evidence", "why_relevant"))
        out.append({"tokens": [t for t in tokens if t], "text": text})
    return out


def _rebuttal_context(grounded: list) -> dict[str, list[dict]]:
    """카드 cluster_key → 그 카드를 만든 의심근거(관점·설명·인용수치). 반박 입력용."""

    context: dict[str, list[dict]] = {}
    for cluster in cluster_suspicions(grounded):
        key = cluster["cluster_key"]
        if not key:
            continue
        context[key] = [
            {
                "perspective": item.perspective,
                "description": item.description,
                "cited_value": item.cited_value,
            }
            for item in cluster["items"]
        ]
    return context


async def _default_external_verifier(
    cards: list[Any], report: dict[str, object], decompositions: dict[str, dict]
) -> dict:
    # external은 발견자가 아니라 카드 확정 후 타깃 검증자 — 상위 카드만 구글검색(PLAN §5).
    from src.report.external_verify import verify_cards

    return await verify_cards(cards, report, decompositions)


async def build_suspicion_cards(
    report: dict[str, object],
    run_llm: bool = True,
    agent_runner: Callable[..., Awaitable[PerspectiveOutput]] = run_structured_perspective,
    rebuttal_runner: Callable[..., Awaitable[Any]] = run_rebuttal,
    investigation_runner: Callable[..., Awaitable[Any]] = run_investigation,
    materials: dict[str, dict] | None = None,
    peer_keys: set[str] | None = None,
    external_verifier: Callable[..., Awaitable[dict]] = _default_external_verifier,
    on_progress: Callable[[dict], None] | None = None,
) -> dict[str, Any]:
    """발견 5관점 병렬 → 근거검증 → 카드 클러스터·집계 → 조사 → 반박 + 외부 검증 → 정렬·렌더.

    on_progress: 진행 표시용 콜백. 관점 완료마다 {phase:'perspective',done,total},
    단계 경계마다 {phase:'grounding'|'cards'|'investigation'|'rebuttal'|'done'}로 호출(선택).
    """

    def _emit(phase: str, done: int | None = None, total: int | None = None) -> None:
        if on_progress:
            on_progress({"phase": phase, "done": done, "total": total})

    accounts = _accounts_reviewed(report)
    ledger = report.get("coverage_ledger", {}) or {}
    unaccounted = len(ledger.get("unaccounted", []))  # type: ignore[union-attr]
    if not run_llm:
        empty = build_card_report(
            {"account_cards": [], "company_cards": [], "relationship_cards": []},
            accounts,
            perspectives_run=0,
            unaccounted=unaccounted,
        )
        return {**empty, "rendered": render_card_markdown(empty), "grounded": [], "dropped": []}

    materials = materials or collect_perspective_materials(report)
    total_p = len(ALL_PERSPECTIVES)
    done_p = 0

    async def _run_one(name: str) -> PerspectiveOutput:
        nonlocal done_p
        # 발견자는 전부 구조화 관점 에이전트(OpenAI). 실검색(external)은 카드 확정 후 검증 단계.
        try:
            return await agent_runner(name, materials.get(name, {}))
        finally:
            done_p += 1
            _emit("perspective", done_p, total_p)

    outputs: list[PerspectiveOutput] = await asyncio.gather(
        *[_run_one(name) for name in ALL_PERSPECTIVES]
    )
    _emit("grounding")
    suspicions: list[SuspicionItem] = []
    completed = 0
    failed = 0
    for output in outputs:
        if output.status == "completed":
            completed += 1
        elif output.status == "failed":
            failed += 1
        suspicions.extend(output.suspicions)

    index = build_account_index(
        report.get("account_level_series", []),  # type: ignore[arg-type]
        report.get("unmapped_material_accounts", []),  # type: ignore[arg-type]
        report.get("note_facts", []),  # type: ignore[arg-type]
        report.get("sce_cells", []),  # type: ignore[arg-type]
        note_disclosures=_note_disclosures(materials.get("note", {})),
    )
    grounded = verify_suspicions(suspicions, index, peer_keys)
    _emit("cards")
    cards = build_cards(grounded, report)

    # 반박: 정렬 전에 적용해야 normal_dominant 카드가 하단으로 강등된다(S4 정렬).
    all_cards = cards["account_cards"] + cards["company_cards"] + cards["relationship_cards"]
    _emit("rebuttal")
    # 변동 분해(PLAN §6.5)를 카드별로 계산해 반박 입력에 공급 — 숫자 없는 추측 반박 방지.
    from src.report.decomposition import decompose_change, load_bridges

    bridges = load_bridges()
    series_rows = report.get("account_level_series") or []
    target_year = int(report.get("target_year") or 0)
    decompositions = {}
    for card in all_cards:
        if not card.cluster_key:
            continue
        decomposed = decompose_change(series_rows, card.account, target_year, bridges)  # type: ignore[arg-type]
        if decomposed:
            decompositions[card.cluster_key] = decomposed

    # 조사 단계(PLAN §5): 카드마다 결론 생성 — 반박·외부검증이 이 결론을 입력으로 받는다.
    _emit("investigation")
    conclusions = await asyncio.gather(
        *[
            investigation_runner(card, report, decompositions.get(card.cluster_key or ""))
            for card in all_cards
        ]
    )
    for card, conclusion in zip(all_cards, conclusions, strict=True):
        card.investigation = conclusion

    # 반박 + 외부 검증(상위 카드 타깃 검색)을 병렬 실행 — 둘 다 카드 확정 후 검증자(PLAN §5).
    rebuttal, external_stats = await asyncio.gather(
        rebuttal_runner(all_cards, _rebuttal_context(grounded), decompositions=decompositions),
        external_verifier(all_cards, report, decompositions),
    )
    apply_rebuttal(all_cards, rebuttal)
    _emit("done")

    card_report = build_card_report(
        cards,
        accounts,
        perspectives_run=completed,
        perspectives_failed=failed,
        unaccounted=unaccounted,
    )
    return {
        **card_report,
        "rendered": render_card_markdown(card_report),
        "grounded": grounded,
        "dropped": [g for g in grounded if not g.grounded],
        "rebuttal_entries": len(rebuttal.entries),
        "investigated": sum(1 for c in conclusions if c is not None),
        "external_verification": external_stats,  # 상위 카드 타깃 검색 결과(관찰용)
    }


__all__ = ["build_suspicion_cards"]
