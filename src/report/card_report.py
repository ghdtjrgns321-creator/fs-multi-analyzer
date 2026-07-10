"""Phase2 카드 정렬·렌더 — PHASE2_DESIGN §4(정렬·표시).

계정 카드는 표수 내림 → 동점 시 금액(materiality) 내림으로 정렬하고, 반박이 '정상우세'로
판정한 카드는 표수가 높아도 하단으로 강등한다(제거 아님, §9). 회사레벨 카드는 별도 섹션.
의심건 0건이면 빈 화면 대신 검토 범위(계정 수·관점 수)를 명시한다(§9 hollow-PASS 차단).
"""

from __future__ import annotations

from src.schemas.findings import AccountFinding

NORMAL_DOMINANT = "normal_dominant"


def order_account_cards(cards: list[AccountFinding]) -> list[AccountFinding]:
    """표수 내림 → 금액 내림. 단 '정상우세' 카드는 항상 하단으로."""

    return sorted(
        cards,
        key=lambda c: (
            c.rebuttal_verdict == NORMAL_DOMINANT,  # False(0) 먼저, 정상우세(True) 뒤로
            -c.vote_count,
            -c.materiality_score,
        ),
    )


def order_company_cards(cards: list[AccountFinding]) -> list[AccountFinding]:
    """회사레벨은 금액 앵커가 없어 표수 내림 → 정상우세 하단 → 계정명 순."""

    return sorted(
        cards,
        key=lambda c: (c.rebuttal_verdict == NORMAL_DOMINANT, -c.vote_count, c.account),
    )


def build_card_report(
    cards: dict[str, list[AccountFinding]],
    accounts_reviewed: int,
    perspectives_run: int,
    perspectives_failed: int = 0,
    unaccounted: int = 0,
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
    cells.extend([f"{card.priority_score:.2f}", _verdict_label(card), badges])
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
        lines.append("| 순위 | 계정 | 유형 | 표수 | 확신도 | 금액 | 점수 | 반박 | 참고 |")
        lines.append("|---:|---|---|---|---|---:|---|---|---|")
        for idx, card in enumerate(account_cards, start=1):
            lines.append(_card_row(idx, card, with_materiality=True))
    if relationship_cards:
        # 흐름 관점 고유 단위 — 계정 쌍·교차재무제표(연결↔별도) 관계 이상.
        lines.extend(["", "## 계정 관계 이상 (흐름)"])
        lines.append("| 순위 | 관계 | 유형 | 표수 | 확신도 | 금액 | 점수 | 반박 | 참고 |")
        lines.append("|---:|---|---|---|---|---:|---|---|---|")
        for idx, card in enumerate(relationship_cards, start=1):
            lines.append(_card_row(idx, card, with_materiality=True))
    if company_cards:
        lines.extend(["", "## 회사 전체 이슈"])
        lines.append("| 순위 | 대상 | 유형 | 표수 | 확신도 | 점수 | 반박 | 참고 |")
        lines.append("|---:|---|---|---|---|---|---|---|")
        for idx, card in enumerate(company_cards, start=1):
            lines.append(_card_row(idx, card, with_materiality=False))
    return "\n".join(lines)


__all__ = [
    "build_card_report",
    "order_account_cards",
    "order_company_cards",
    "render_card_markdown",
]
