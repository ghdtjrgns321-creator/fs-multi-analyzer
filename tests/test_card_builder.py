"""S3 — 클러스터·집계·점수 카드조립 (PHASE2_DESIGN §4 ②③·§7 S3).

grounded 의심건을 계정별로 묶어(회사레벨은 별도 버킷) N/4 표수·점수·확신도를 코드가 매겨
AccountFinding 카드를 만든다. 외부·동종은 표수 미가산(참고배지), 점수는 결정론.
"""

from __future__ import annotations

from src.report.card_builder import build_cards, cluster_suspicions
from src.report.grounding import GroundedSuspicion
from src.schemas.findings import IssueType
from src.schemas.suspicion import SuspicionItem, build_account_locator


def _g(
    perspective: str,
    account_id: str | None,
    *,
    scope: str = "account",
    value_verified: bool = True,
    grounded: bool = True,
    risk: str = "Medium",
    issue: IssueType = IssueType.REVENUE_RECEIVABLES,
    cited: str | None = "100,000,000",
    subtype: str = "",
    prior_value: str | None = None,
    prior_year: str | None = None,
) -> GroundedSuspicion:
    item = SuspicionItem(
        perspective=perspective,
        scope=scope,
        issue_type=issue,
        subtype=subtype,
        account_id=account_id,
        sj_div="BS" if scope == "account" else None,
        year="2024",
        cited_value=cited if scope == "account" else None,
        description=f"{perspective} 의심.",
        source_url="https://x" if perspective == "external" else None,
        risk_level=risk,
        prior_value=prior_value,
        prior_year=prior_year,
    )
    return GroundedSuspicion(
        item=item, grounded=grounded, value_verified=value_verified, reason="t"
    )


def test_change_prior_propagated_to_card() -> None:
    # change 死필드 부활: change 의심건의 전기값/전기연도가 카드로 전파돼야 한다.
    grounded = [
        _g("trend", "매출채권", prior_value="90,000,000", prior_year="2023"),
    ]
    card = build_cards(grounded, _report())["account_cards"][0]
    assert card.prior_value == "90,000,000"
    assert card.prior_year == "2023"


def _report(rows=None):
    return {
        "target_year": "2024",
        "account_level_series": rows
        or [
            {
                "year": "2024",
                "sj_div": "BS",
                "series_key": "매출채권",
                "canonical": "매출채권",
                "label": "매출채권",
                "amount": 100_000_000.0,
                "mapping_status": "exact",
            },
            {
                "year": "2024",
                "sj_div": "BS",
                "series_key": "재고자산",
                "canonical": "재고자산",
                "label": "재고자산",
                "amount": 900_000_000.0,
                "mapping_status": "exact",
            },
        ],
    }


def test_same_account_one_card_votes() -> None:
    grounded = [_g("numeric", "매출채권"), _g("flow", "매출채권")]
    cards = build_cards(grounded, _report())["account_cards"]
    assert len(cards) == 1
    assert cards[0].vote_count == 2


def test_dedup_same_perspective_counts_once() -> None:
    grounded = [_g("numeric", "매출채권"), _g("numeric", "매출채권")]
    cards = build_cards(grounded, _report())["account_cards"]
    assert cards[0].vote_count == 1


def test_different_accounts_split() -> None:
    grounded = [_g("numeric", "매출채권"), _g("numeric", "재고자산")]
    cards = build_cards(grounded, _report())["account_cards"]
    assert len(cards) == 2


def test_external_industry_not_in_votes() -> None:
    grounded = [_g("numeric", "매출채권"), _g("industry", "매출채권", value_verified=False)]
    card = build_cards(grounded, _report())["account_cards"][0]
    assert card.vote_count == 1
    assert "industry" in card.reference_badges


def test_ungrounded_excluded() -> None:
    grounded = [_g("numeric", "매출채권", grounded=False)]
    cards = build_cards(grounded, _report())["account_cards"]
    assert cards == []


def test_company_scope_separate_bucket() -> None:
    grounded = [
        _g(
            "external",
            None,
            scope="company",
            value_verified=False,
            issue=IssueType.CONTINGENCY_RELATED_PARTY,
        )
    ]
    result = build_cards(grounded, _report())
    assert result["account_cards"] == []
    assert len(result["company_cards"]) == 1


def test_materiality_orders_by_amount() -> None:
    grounded = [_g("numeric", "매출채권"), _g("numeric", "재고자산")]
    cards = {c.account: c for c in build_cards(grounded, _report())["account_cards"]}
    assert cards["재고자산"].materiality_score >= cards["매출채권"].materiality_score


def test_confidence_high_and_low() -> None:
    high = [
        _g("numeric", "매출채권", value_verified=True),
        _g("flow", "매출채권", value_verified=True),
    ]
    card_high = build_cards(high, _report())["account_cards"][0]
    assert card_high.confidence == "High"
    low = [
        _g(
            "external",
            None,
            scope="company",
            value_verified=False,
            issue=IssueType.CONTINGENCY_RELATED_PARTY,
        )
    ]
    card_low = build_cards(low, _report())["company_cards"][0]
    assert card_low.confidence == "Low"


def test_risk_level_is_max() -> None:
    grounded = [_g("numeric", "매출채권", risk="Low"), _g("flow", "매출채권", risk="High")]
    card = build_cards(grounded, _report())["account_cards"][0]
    assert card.risk_level == "High"


def test_cluster_key_set_on_card() -> None:
    grounded = [_g("numeric", "매출채권")]
    card = build_cards(grounded, _report())["account_cards"][0]
    assert card.cluster_key == build_account_locator("BS", "매출채권")


def test_other_issue_type_card_carries_subtype() -> None:
    # '기타'(OTHER)로 제출된 비-분식 이상변화는 subtype에 실제 성격이 보존돼야 한다(#14).
    grounded = [
        _g("numeric", "유형자산취득", issue=IssueType.OTHER, subtype="설비투자급증"),
        _g("trend", "유형자산취득", issue=IssueType.OTHER, subtype="설비투자급증"),
    ]
    card = build_cards(grounded, _report())["account_cards"][0]
    assert card.issue_type is IssueType.OTHER
    assert card.subtype == "설비투자급증"


def test_subtype_empty_when_not_provided() -> None:
    grounded = [_g("numeric", "매출채권")]
    card = build_cards(grounded, _report())["account_cards"][0]
    assert card.subtype == ""


def test_cluster_suspicions_groups() -> None:
    grounded = [_g("numeric", "매출채권"), _g("flow", "매출채권"), _g("numeric", "재고자산")]
    clusters = cluster_suspicions(grounded)
    account_clusters = [c for c in clusters if c["scope"] == "account"]
    assert len(account_clusters) == 2
