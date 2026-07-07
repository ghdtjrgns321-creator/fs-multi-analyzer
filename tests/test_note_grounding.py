"""주석 grounding 사각#3 — 서술형 공시 색인(허위탈락 차단).

담보·특수관계 같은 서술형 공시는 note_sections·report_extracts(Layer 1 추출)에 살고 XBRL fact엔
없다. 이걸 note: 네임스페이스에 색인해, LLM이 라벨을 다르게 앵커링해도 인용 금액이 실제 공시에
있으면 grounded 시킨다(환각가드는 유지 — 공시에 없는 금액은 탈락).
"""

from __future__ import annotations

from src.report.grounding import build_account_index, verify_account_suspicion
from src.schemas.findings import IssueType
from src.schemas.suspicion import SuspicionItem

DISCLOSURES = [
    {
        "tokens": ["담보_보증", "담보", "보증"],
        "text": "담보로 제공된 자산 장부금액 54,345백만원이 은행차입금 담보로 제공되어 있습니다.",
    },
    {
        "tokens": ["특수관계자"],
        "text": "특수관계자 채권에 대해 당기말 대손충당금 233,546천원을 설정했습니다.",
    },
]


def _note_item(account_id: str, cited: str) -> SuspicionItem:
    return SuspicionItem(
        perspective="note",
        scope="account",
        issue_type=IssueType.CONTINGENCY_RELATED_PARTY,
        account_id=account_id,
        year="2024",
        cited_value=cited,
        description="주석 의심.",
    )


def test_disclosure_amount_grounds_even_if_label_mismatch() -> None:
    # LLM이 담보를 라벨 미스로 앵커링해도, 인용 금액이 공시 텍스트에 실재하면 grounded.
    idx = build_account_index([], [], None, None, note_disclosures=DISCLOSURES)
    g = verify_account_suspicion(_note_item("유형자산담보제공", "54,345백만원"), idx)
    assert g.grounded is True
    assert g.value_verified is True


def test_special_related_party_amount_grounds() -> None:
    idx = build_account_index([], [], None, None, note_disclosures=DISCLOSURES)
    g = verify_account_suspicion(_note_item("특수관계자채권대손", "233,546천원"), idx)
    assert g.grounded is True


def test_hallucinated_amount_still_dropped() -> None:
    # 공시에 없는 금액은 여전히 탈락(환각가드 유지).
    idx = build_account_index([], [], None, None, note_disclosures=DISCLOSURES)
    g = verify_account_suspicion(_note_item("담보", "99,999백만원"), idx)
    assert g.grounded is False


def test_note_fact_key_grounding_unchanged() -> None:
    # 기존 note_facts(라벨 키) grounding 무회귀.
    facts = [{"label": "리스보증금의 증가", "category": "리스", "value": "24735"}]
    idx = build_account_index([], [], facts, None)
    g = verify_account_suspicion(_note_item("리스보증금의 증가", "24,735"), idx)
    assert g.grounded is True
