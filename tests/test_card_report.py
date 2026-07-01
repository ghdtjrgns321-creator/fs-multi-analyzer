"""S4 — 정렬·표시·렌더 (PHASE2_DESIGN §4 정렬·표시·§7 S4).

카드 정렬(표수 내림 → 동점 시 금액 내림, 정상우세 플래그는 하단), 회사레벨 분리,
의심건 0건 검토범위 명시(빈 화면 금지), markdown 렌더를 고정한다.
"""

from __future__ import annotations

from src.report.card_report import (
    build_card_report,
    order_account_cards,
    render_card_markdown,
)
from src.schemas.findings import AccountFinding, IssueType


def _card(
    account,
    votes,
    materiality,
    *,
    verdict=None,
    conf="Medium",
    issue=IssueType.REVENUE_RECEIVABLES,
    subtype="",
) -> AccountFinding:
    return AccountFinding(
        account=account,
        issue_type=issue,
        subtype=subtype,
        materiality_score=materiality,
        anomaly_score=0.0,
        confidence=conf,
        risk_level="Medium",
        vote_count=votes,
        rebuttal_verdict=verdict,
        cluster_key=f"acct:BS:{account}",
    )


def test_change_prior_rendered_in_account_cell() -> None:
    # change 死필드 부활: 전기값 보유 카드는 계정셀에 "(전기 …)"로 병기돼야 한다.
    card = _card("운전자본변동", 2, 0.5)
    card.prior_value = "1,696,615,727"
    card.prior_year = "2023"
    report = build_card_report({"account_cards": [card]}, 10, perspectives_run=6)
    md = render_card_markdown(report)
    assert "전기" in md
    assert "1,696,615,727" in md


def test_order_by_votes_desc() -> None:
    cards = order_account_cards([_card("A", 1, 0.9), _card("B", 3, 0.1)])
    assert [c.account for c in cards] == ["B", "A"]


def test_tie_break_by_materiality() -> None:
    cards = order_account_cards([_card("A", 2, 0.2), _card("B", 2, 0.8)])
    assert [c.account for c in cards] == ["B", "A"]


def test_normal_dominant_sinks() -> None:
    cards = order_account_cards([_card("A", 4, 0.9, verdict="normal_dominant"), _card("B", 1, 0.1)])
    assert cards[-1].account == "A"


def test_company_cards_separate() -> None:
    report = build_card_report(
        {"account_cards": [_card("A", 2, 0.5)], "company_cards": [_card("(회사 전체)", 0, 0.0)]},
        accounts_reviewed=10,
        perspectives_run=6,
    )
    assert [c.account for c in report["account_cards"]] == ["A"]
    assert len(report["company_cards"]) == 1
    assert report["has_findings"] is True


def test_zero_findings_scope_shown() -> None:
    report = build_card_report(
        {"account_cards": [], "company_cards": []},
        accounts_reviewed=42,
        perspectives_run=6,
    )
    assert report["has_findings"] is False
    text = render_card_markdown(report)
    assert "의심건" in text and "0" in text
    assert "42" in text and "6" in text


def test_zero_findings_all_failed_warns_not_clean() -> None:
    # 6관점 전부 LLM 실패(0 완료)면 "위험 후보 없음"이 아니라 "실패·미검증"으로 표면화해야 한다.
    report = build_card_report(
        {"account_cards": [], "company_cards": []},
        accounts_reviewed=467,
        perspectives_run=0,
        perspectives_failed=6,
    )
    assert report["has_findings"] is False
    assert report["review_scope"]["perspectives_failed"] == 6
    text = render_card_markdown(report)
    # 거짓 안심 문구가 떠선 안 됨
    assert "위험 후보가 없음" not in text
    # 실패를 명시
    assert "실패" in text and "미검증" in text


def test_zero_findings_no_failure_stays_clean() -> None:
    # 6관점 정상 완료·0건이면 기존 "위험 후보 없음" 유지(과교정 금지).
    report = build_card_report(
        {"account_cards": [], "company_cards": []},
        accounts_reviewed=42,
        perspectives_run=6,
        perspectives_failed=0,
    )
    text = render_card_markdown(report)
    assert "위험 후보가 없음" in text
    assert "LLM 실패" not in text


def test_render_shows_votes_confidence_materiality() -> None:
    report = build_card_report(
        {"account_cards": [_card("매출채권", 3, 0.7, conf="High")], "company_cards": []},
        accounts_reviewed=10,
        perspectives_run=6,
    )
    text = render_card_markdown(report)
    assert "3/4" in text
    assert "High" in text
    assert "0.7" in text
    assert "매출채권" in text


def test_render_shows_subtype_inline() -> None:
    # '기타'(OTHER) 카드는 유형 셀에 subtype을 병기해 실제 성격을 보여야 한다(#14).
    report = build_card_report(
        {
            "account_cards": [
                _card("유형자산취득", 1, 0.2, issue=IssueType.OTHER, subtype="설비투자급증")
            ],
            "company_cards": [],
        },
        accounts_reviewed=10,
        perspectives_run=6,
    )
    text = render_card_markdown(report)
    assert "설비투자급증" in text


def test_render_company_section_present() -> None:
    report = build_card_report(
        {"account_cards": [], "company_cards": [_card("(회사 전체)", 0, 0.0)]},
        accounts_reviewed=5,
        perspectives_run=6,
    )
    text = render_card_markdown(report)
    assert "회사" in text
