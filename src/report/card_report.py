"""Phase2 카드 정렬·렌더 — PHASE2_DESIGN §4(정렬·표시).

정렬 기준은 src/report/card_order.py 단일 출처(화면·리포트·외부검증 공용). 여기서는
렌더만 한다. 의심건 0건이면 빈 화면 대신 검토 범위(계정 수·관점 수)를 명시한다
(§9 hollow-PASS 차단).
"""

from __future__ import annotations

from src.report.card_order import order_cards, order_company_cards
from src.schemas.findings import AccountFinding


def order_account_cards(cards: list[AccountFinding]) -> list[AccountFinding]:
    """계정·관계 카드 정렬 — card_order 단일 기준 위임(이름은 기존 호출부 호환)."""

    return order_cards(cards)


def build_card_report(
    cards: dict[str, list[AccountFinding]],
    accounts_reviewed: int,
    perspectives_run: int,
    perspectives_failed: int = 0,
    unaccounted: int = 0,
    derived_blocked: int = 0,
    derived_blocked_amount: float = 0.0,
) -> dict[str, object]:
    """정렬된 카드 섹션 + 검토 범위 + 산출 여부.

    unaccounted = 커버리지 원장의 '이유 없이 빠진 셀' 수(근본구조 C). >0이면 조용한 드롭이
    있다는 뜻 → 렌더에 "미분석 N건"으로 드러낸다(0이면 표시 안 함).
    """

    account_cards = order_account_cards(cards.get("account_cards", []))
    company_cards = order_company_cards(cards.get("company_cards", []))
    # 관계 카드도 금액 앵커(다리 최댓값)가 있어 계정 카드와 같은 정렬(표수→금액).
    relationship_cards = order_account_cards(cards.get("relationship_cards", []))
    return {
        "account_cards": account_cards,
        "company_cards": company_cards,
        "relationship_cards": relationship_cards,
        "review_scope": {
            "accounts_reviewed": accounts_reviewed,
            "perspectives_run": perspectives_run,
            "perspectives_failed": perspectives_failed,
            "unaccounted_cells": unaccounted,
            # 파생층: 표준 이름이 없어 관계사슬·재무비율에 진입 못 한 계정(조용한 드롭 표면화).
            "derived_blocked": derived_blocked,
            "derived_blocked_amount": derived_blocked_amount,
        },
        "has_findings": bool(account_cards or company_cards or relationship_cards),
    }


def _verdict_label(card: AccountFinding) -> str:
    # verdict 없으면 '반박 미수행' 명시(빈칸 숨김 금지, §9).
    return {
        "normal_dominant": "정상설명 우세",
        "mixed": "반반",
        "suspicion_dominant": "의심 우세",
    }.get(card.rebuttal_verdict or "", "반박 미수행")


def _card_row(idx: int, card: AccountFinding, with_materiality: bool) -> str:
    vote = f"{card.vote_count}/{card.internal_total}"
    badges = ", ".join(card.reference_badges) or "-"
    # '기타' 유형은 값만으론 무의미 — subtype을 병기해 실제 성격을 표시(#14).
    issue = f"{card.issue_type.value}({card.subtype})" if card.subtype else card.issue_type.value
    # 변동 카드 전기값 병기(死필드 부활) — 전기→당기를 계정셀에 드러낸다.
    account_cell = card.account
    if card.prior_value or card.prior_year:
        prior = f"전기 {card.prior_year or '?'}: {card.prior_value or '?'}"
        account_cell = f"{account_cell} ({prior})"
    cells = [str(idx), account_cell, issue, vote, card.confidence]
    if with_materiality:
        cells.append(f"{card.materiality_score:.2f}")
    cells.extend([_verdict_label(card), badges])
    return "| " + " | ".join(cells) + " |"


def render_card_markdown(report: dict[str, object]) -> str:
    """카드 목록 markdown. 0건이면 검토 범위 명시."""

    scope = report.get("review_scope", {}) or {}
    accounts = scope.get("accounts_reviewed", 0)  # type: ignore[union-attr]
    perspectives = scope.get("perspectives_run", 0)  # type: ignore[union-attr]
    failed = scope.get("perspectives_failed", 0)  # type: ignore[union-attr]
    unaccounted = scope.get("unaccounted_cells", 0)  # type: ignore[union-attr]
    lines = ["# PHASE2 의심건 카드"]
    # 근본구조 C: 모집단 대조에서 이유 없이 빠진 셀이 있으면 "위험 없음"으로 둔갑 금지.
    coverage_warn = (
        f"⚠ 커버리지 경고: 본문 셀 {unaccounted}건이 이유 없이 분석에서 누락(조용한 드롭). "
        "원장 unaccounted 확인 필요."
        if unaccounted
        else ""
    )
    if coverage_warn:
        lines.extend(["", coverage_warn])
    blocked = int(scope.get("derived_blocked", 0) or 0)  # type: ignore[union-attr]
    if blocked:
        amount = float(scope.get("derived_blocked_amount", 0.0) or 0.0)  # type: ignore[union-attr]
        lines.extend(
            [
                "",
                f"ℹ 관계사슬·재무비율 미진입 {blocked}건(금액 {amount:,.0f}원) — 표준 계정명이 "
                "없어 이름 기반 분석에서 조회되지 않았다. 계정별 지표·카드에는 포함된다.",
            ]
        )

    if not report.get("has_findings"):
        lines.append("")
        # 관점 LLM이 실패했으면 0건을 "위험 없음"으로 둔갑시키지 않는다(hollow-PASS 차단).
        if failed:
            lines.append(
                f"계정 {accounts}개를 대상으로 했으나 관점 {failed}개가 LLM 호출 실패로 "
                f"의심건이 미검증이다(완료 {perspectives}개)."
            )
            lines.append(
                "(빈 결과가 아니라 LLM 실패다 — API 키·크레딧·타임아웃을 확인하고 재실행해야 한다.)"
            )
            return "\n".join(lines)
        lines.append(f"계정 {accounts}개·관점 {perspectives}개를 검토했으나 제기된 의심건 0건이다.")
        lines.append("(빈 결과가 아니라 검토 범위 내에서 위험 후보가 없음을 의미한다.)")
        return "\n".join(lines)

    account_cards: list[AccountFinding] = report.get("account_cards", [])  # type: ignore[assignment]
    company_cards: list[AccountFinding] = report.get("company_cards", [])  # type: ignore[assignment]
    relationship_cards: list[AccountFinding] = report.get("relationship_cards", [])  # type: ignore[assignment]

    lines.append("")
    lines.append(f"검토: 계정 {accounts}개 · 관점 {perspectives}개")
    if account_cards:
        lines.extend(["", "## 계정별 의심건"])
        lines.append("| 순위 | 계정 | 유형 | 표수 | 확신도 | 금액 | 반박 | 참고 |")
        lines.append("|---:|---|---|---|---|---:|---|---|")
        for idx, card in enumerate(account_cards, start=1):
            lines.append(_card_row(idx, card, with_materiality=True))
    if relationship_cards:
        # 흐름 관점 고유 단위 — 계정 쌍·교차재무제표(연결↔별도) 관계 이상.
        lines.extend(["", "## 계정 관계 이상 (흐름)"])
        lines.append("| 순위 | 관계 | 유형 | 표수 | 확신도 | 금액 | 반박 | 참고 |")
        lines.append("|---:|---|---|---|---|---:|---|---|")
        for idx, card in enumerate(relationship_cards, start=1):
            lines.append(_card_row(idx, card, with_materiality=True))
    if company_cards:
        lines.extend(["", "## 회사 전체 이슈"])
        lines.append("| 순위 | 대상 | 유형 | 표수 | 확신도 | 반박 | 참고 |")
        lines.append("|---:|---|---|---|---|---|---|")
        for idx, card in enumerate(company_cards, start=1):
            lines.append(_card_row(idx, card, with_materiality=False))
    return "\n".join(lines)


__all__ = [
    "build_card_report",
    "order_account_cards",
    "order_company_cards",
    "render_card_markdown",
]
