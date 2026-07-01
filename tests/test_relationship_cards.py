"""흐름(flow) 관계 출력 — scope="relationship" 3번째 단위 (근본 수리).

대주 실측: flow 고유단위=계정관계(쌍·교차재무제표)인데 출력축이 account/company 2개뿐이라
관계가 단일계정 카드로 붕괴했다. 관계를 정식 scope로 추가해 별도 relationship_cards로 낸다.
정렬 canonical(A↔B==B↔A), 가짜다리 드롭, 별도 리스트, 렌더 섹션을 검증한다.
"""

from __future__ import annotations

import pytest

from src.report.card_builder import build_cards
from src.report.card_report import build_card_report, render_card_markdown
from src.report.grounding import (
    build_account_index,
    verify_relationship_suspicion,
    verify_suspicions,
)
from src.schemas.findings import IssueType
from src.schemas.suspicion import SuspicionItem, cluster_key


def _rel(
    account_id: str = "CFS:매출",
    related: tuple[str, ...] = ("CFS:재고자산",),
    cited: str | None = None,
) -> SuspicionItem:
    return SuspicionItem(
        perspective="flow",
        scope="relationship",
        issue_type=IssueType.REVENUE_RECEIVABLES,
        account_id=account_id,
        related_accounts=list(related),
        sj_div="CF",
        year="2024",
        cited_value=cited,
        description="매출↔재고 관계 괴리.",
        risk_level="Medium",
    )


def _rows() -> list[dict]:
    def row(key: str, amount: float) -> dict:
        return {
            "year": "2024",
            "sj_div": "CF",
            "series_key": key,
            "canonical": key,
            "label": key,
            "amount": amount,
            "mapping_status": "exact",
        }

    return [
        row("CFS:매출", 106_000_000_000.0),
        row("CFS:재고자산", 9_000_000_000.0),
        row("CFS:현금", 11_000_000_000.0),
        row("OFS:현금", 8_000_000_000.0),
    ]


def _index() -> dict[str, set[str]]:
    return build_account_index(_rows())


def _report() -> dict:
    return {
        "target_year": "2024",
        "account_level_series": _rows(),
        "latest_signal_snapshot": {},
    }


def test_relationship_cluster_key_canonical() -> None:
    # A↔B와 B↔A는 정렬 canonical이라 같은 카드로 뭉쳐야 vote가 합산된다.
    a = _rel(account_id="CFS:매출", related=("CFS:재고자산",))
    b = _rel(account_id="CFS:재고자산", related=("CFS:매출",))
    assert cluster_key(a) == cluster_key(b)
    assert cluster_key(a).startswith("rel:")


def test_cross_fs_relationship_same_rule() -> None:
    # 교차재무제표(연결↔별도)도 특수분기 없이 동일 rel 규칙으로 키 생성.
    item = _rel(account_id="CFS:현금", related=("OFS:현금",))
    assert cluster_key(item) == "rel:CFS:현금|OFS:현금"


def test_relationship_requires_related_accounts() -> None:
    with pytest.raises(ValueError):
        _rel(related=())


def test_relationship_fake_leg_dropped() -> None:
    idx = _index()
    real = verify_relationship_suspicion(
        _rel(account_id="CFS:매출", related=("CFS:재고자산",)), idx
    )
    fake = verify_relationship_suspicion(
        _rel(account_id="CFS:매출", related=("CFS:유령계정",)), idx
    )
    assert real.grounded is True
    assert fake.grounded is False


def test_relationship_card_separate_list() -> None:
    grounded = verify_suspicions([_rel()], _index())
    cards = build_cards(grounded, _report())
    assert len(cards["relationship_cards"]) == 1
    assert cards["account_cards"] == []
    assert "↔" in cards["relationship_cards"][0].account
    assert set(cards["relationship_cards"][0].related_accounts) == {"CFS:매출", "CFS:재고자산"}


def test_relationship_section_rendered() -> None:
    grounded = verify_suspicions([_rel()], _index())
    cards = build_cards(grounded, _report())
    card_report = build_card_report(cards, accounts_reviewed=4, perspectives_run=6)
    md = render_card_markdown(card_report)
    assert card_report["has_findings"] is True
    assert "관계" in md
    assert "매출" in md and "재고자산" in md
