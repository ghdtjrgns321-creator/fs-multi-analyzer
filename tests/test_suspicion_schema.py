"""S1 — 의심건·카드 스키마 검증 (PHASE2_DESIGN §3·§4·§7).

관점이 제출하는 SuspicionItem의 grounding 강제(빈칸·앵커 누락 거부)와
locator 규약 round-trip, cluster_key 분기, AccountFinding 카드 메타 기본값을 고정한다.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.findings import AccountFinding, EvidenceRef, IssueType
from src.schemas.suspicion import (
    INTERNAL_PERSPECTIVES,
    SuspicionItem,
    build_account_locator,
    cluster_key,
    parse_account_locator,
)


def _account_item(**overrides) -> SuspicionItem:
    base = dict(
        perspective="numeric",
        scope="account",
        issue_type=IssueType.REVENUE_RECEIVABLES,
        account_id="ifrs-full_TradeReceivables",
        sj_div="BS",
        year="2024",
        cited_value="123,456,000",
        description="매출채권이 매출 증가율을 크게 상회한다.",
    )
    base.update(overrides)
    return SuspicionItem(**base)


def test_account_item_serializes() -> None:
    item = _account_item()
    dumped = item.model_dump(mode="json")
    assert dumped["account_id"] == "ifrs-full_TradeReceivables"
    assert dumped["cited_value"] == "123,456,000"
    assert dumped["scope"] == "account"


def test_account_scope_requires_account_id() -> None:
    with pytest.raises(ValidationError):
        _account_item(account_id=None)


def test_account_scope_requires_cited_value() -> None:
    with pytest.raises(ValidationError):
        _account_item(cited_value=None)


def test_blank_description_rejected() -> None:
    with pytest.raises(ValidationError):
        _account_item(description="   ")


def test_company_scope_allows_no_account() -> None:
    item = SuspicionItem(
        perspective="external",
        scope="company",
        issue_type=IssueType.CONTINGENCY_RELATED_PARTY,
        account_id=None,
        year="2024",
        cited_value=None,
        description="감사보고서 계속기업 불확실성 문단이 추가됐다.",
        source_url="https://dart.fss.or.kr/x",
    )
    assert item.account_id is None
    assert item.scope == "company"


def test_account_locator_round_trip() -> None:
    locator = build_account_locator("BS", "ifrs-full_TradeReceivables")
    sj_div, account_id = parse_account_locator(locator)
    assert sj_div == "BS"
    assert account_id == "ifrs-full_TradeReceivables"


def test_cluster_key_branches() -> None:
    account = _account_item()
    company = SuspicionItem(
        perspective="industry",
        scope="company",
        issue_type=IssueType.LIABILITY_LIQUIDITY,
        account_id=None,
        year="2024",
        cited_value=None,
        description="동종업계 대비 부채비율 상위 분위수.",
    )
    assert cluster_key(account)
    assert cluster_key(company) is None


def test_internal_perspectives_are_four() -> None:
    assert set(INTERNAL_PERSPECTIVES) == {"numeric", "note", "flow", "trend"}
    assert len(INTERNAL_PERSPECTIVES) == 4


def test_account_finding_card_meta_defaults() -> None:
    finding = AccountFinding(
        account="매출채권",
        issue_type=IssueType.REVENUE_RECEIVABLES,
        materiality_score=0.5,
        anomaly_score=0.4,
        confidence="Medium",
        numeric_evidence=[
            EvidenceRef(source="financial_statement", locator="매출채권", year="2024", value="x")
        ],
        risk_level="Medium",
    )
    assert finding.vote_count == 0
    assert finding.internal_total == 4
    assert finding.reference_badges == []
    assert finding.rebuttal_verdict is None
    assert finding.cluster_key is None


def test_account_finding_card_meta_set() -> None:
    finding = AccountFinding(
        account="매출채권",
        issue_type=IssueType.REVENUE_RECEIVABLES,
        materiality_score=0.5,
        anomaly_score=0.4,
        confidence="High",
        risk_level="High",
        vote_count=2,
        reference_badges=["external", "industry"],
        rebuttal_verdict="suspicion_dominant",
        cluster_key="acct:BS:ifrs-full_TradeReceivables",
    )
    dumped = finding.model_dump(mode="json")
    assert dumped["vote_count"] == 2
    assert dumped["reference_badges"] == ["external", "industry"]
    assert dumped["rebuttal_verdict"] == "suspicion_dominant"
