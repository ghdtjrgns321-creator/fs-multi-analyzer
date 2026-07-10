"""의심건 카드 영속화(cards_store) — 왕복 보존·부재·손상 graceful 검증."""

from __future__ import annotations

from pathlib import Path

from src.report.cards_store import load_cards, save_cards
from src.schemas.findings import AccountFinding, Claim, EvidenceRef, IssueType

CARD = AccountFinding(
    account="CFS:무형자산",
    issue_type=IssueType.ASSET_VALUATION,
    subtype="손상 확대",
    materiality_score=1.0,
    anomaly_score=1.0,
    confidence="High",
    risk_level="High",
    vote_count=2,
    internal_total=4,
    claims=[
        Claim(perspective="numeric", description="전기 대비 30% 감소", cited_value="1.96조"),
        Claim(perspective="trend", description="3년 연속 감소"),
    ],
    numeric_evidence=[
        EvidenceRef(
            source="financial_statement", locator="무형자산", year="2024", value="1964277226876"
        )
    ],
)
SERIES = [{"series_key": "CFS:무형자산", "year": 2024, "amount": 1_964_277_226_876.0}]


def test_save_load_roundtrip_preserves_cards(tmp_path: Path) -> None:
    """저장 전 == 로드 후: 계정명·claims 2건·numeric_evidence 1건·시계열·타깃연도 보존."""

    result = {
        "has_findings": True,
        "review_scope": {"accounts_reviewed": 10, "perspectives_run": 6},
        "external_verification": {"status": "deferred", "verified": 0, "found": 0},
        "account_cards": [CARD],
        "relationship_cards": [],
        "company_cards": [],
    }
    save_cards("00000001", 2024, result, SERIES, 2024, root=tmp_path)
    loaded = load_cards("00000001", 2024, root=tmp_path)

    assert loaded is not None and loaded["has_findings"] is True
    assert loaded["external_verification"]["status"] == "deferred"  # deferred 캡션 재현 재료
    [card] = loaded["account_cards"]
    assert card["account"] == "CFS:무형자산"
    assert len(card["claims"]) == 2  # 저장 전 2건 == 로드 후 2건
    assert len(card["numeric_evidence"]) == 1
    assert card["numeric_evidence"][0]["value"] == "1964277226876"
    assert loaded["series_rows"] == SERIES
    assert loaded["target_year"] == 2024
    assert loaded["created_at"]  # 생성시각 스탬프 존재


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    assert load_cards("00000001", 2024, root=tmp_path) is None


def test_load_corrupt_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "00000001" / "2024" / "suspicion_cards.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken json", encoding="utf-8")
    assert load_cards("00000001", 2024, root=tmp_path) is None
