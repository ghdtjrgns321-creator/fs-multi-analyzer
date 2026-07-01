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


async def build_suspicion_cards(
    report: dict[str, object],
    run_llm: bool = True,
    agent_runner: Callable[..., Awaitable[PerspectiveOutput]] = run_structured_perspective,
    rebuttal_runner: Callable[..., Awaitable[Any]] = run_rebuttal,
    materials: dict[str, dict] | None = None,
    peer_keys: set[str] | None = None,
) -> dict[str, Any]:
    """6관점 병렬 → 근거검증 → 카드 클러스터·집계 → 반박 → 정렬·렌더."""

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
    outputs: list[PerspectiveOutput] = await asyncio.gather(
        *[agent_runner(name, materials.get(name, {})) for name in ALL_PERSPECTIVES]
    )
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
    )
    grounded = verify_suspicions(suspicions, index, peer_keys)
    cards = build_cards(grounded, report)

    # 반박: 정렬 전에 적용해야 normal_dominant 카드가 하단으로 강등된다(S4 정렬).
    all_cards = cards["account_cards"] + cards["company_cards"] + cards["relationship_cards"]
    rebuttal = await rebuttal_runner(all_cards, _rebuttal_context(grounded))
    apply_rebuttal(all_cards, rebuttal)

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
    }


__all__ = ["build_suspicion_cards"]
