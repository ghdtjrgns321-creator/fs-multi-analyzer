"""의심건 카드 영속화(cards_store) — 왕복 보존·부재·손상 graceful 검증."""

from __future__ import annotations

from pathlib import Path

from src.report.cards_store import load_cards, save_cards
from src.schemas.findings import AccountFinding, Claim, EvidenceRef, IssueType
from src.schemas.investigation import InvestigationConclusion

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


def test_store_roundtrip_preserves_investigation(tmp_path: Path) -> None:
    """조사 결론·연속 우선순위·병합 자식 — 저장 전 == 로드 후(신규 필드 3종 왕복)."""

    card = CARD.model_copy(
        update={
            "priority_score": 0.87,
            "merged_children": ["CFS:영업권", "CFS:특허권"],
            "investigation": InvestigationConclusion(
                headline="무형자산 손상이 주도",
                cause_path=["손상차손 인식", "회수가능액 재평가"],
                anomaly_points=["동종 대비 손상률 이례적"],
                open_questions=["감액 근거 문서 미확인"],
                resolved=True,
                method="tool_loop",
                tool_requests=3,
            ),
        }
    )
    result = {
        "has_findings": True,
        "review_scope": {},
        "external_verification": {},
        "account_cards": [card],
        "relationship_cards": [],
        "company_cards": [],
    }
    save_cards("00000002", 2024, result, SERIES, 2024, root=tmp_path)
    loaded = load_cards("00000002", 2024, root=tmp_path)

    [loaded_card] = loaded["account_cards"]
    assert loaded_card["priority_score"] == 0.87
    assert loaded_card["merged_children"] == ["CFS:영업권", "CFS:특허권"]
    assert loaded_card["investigation"]["headline"] == "무형자산 손상이 주도"
    assert loaded_card["investigation"]["resolved"] is True
    assert loaded_card["investigation"]["tool_requests"] == 3


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    assert load_cards("00000001", 2024, root=tmp_path) is None


def test_load_corrupt_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "00000001" / "2024" / "suspicion_cards.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken json", encoding="utf-8")
    assert load_cards("00000001", 2024, root=tmp_path) is None


def test_save_refuses_empty_result_from_failed_perspectives(tmp_path):
    """관점 실패로 빈손이면 저장 거부 — 이전 정상 카드를 빈 파일로 덮는 사고 방지(429 실사례)."""

    from src.report.cards_store import load_cards, save_cards

    good = {
        "account_cards": [{"account": "CFS:재고자산"}],
        "relationship_cards": [],
        "company_cards": [],
        "review_scope": {"perspectives_run": 5, "perspectives_failed": 0},
        "has_findings": True,
    }
    assert save_cards("00000001", 2024, good, [], 2024, root=tmp_path) is not None

    failed_empty = {
        "account_cards": [],
        "relationship_cards": [],
        "company_cards": [],
        "review_scope": {"perspectives_run": 0, "perspectives_failed": 5},
        "has_findings": False,
    }
    assert save_cards("00000001", 2024, failed_empty, [], 2024, root=tmp_path) is None
    # 이전 정상 저장분이 보존됐다
    loaded = load_cards("00000001", 2024, root=tmp_path)
    assert loaded is not None and len(loaded["account_cards"]) == 1


def test_save_allows_genuine_zero_findings(tmp_path):
    """전 관점 완주 후 진짜 0건은 저장한다 — '실행됐고 0건'의 증거."""

    from src.report.cards_store import save_cards

    clean = {
        "account_cards": [],
        "relationship_cards": [],
        "company_cards": [],
        "review_scope": {"perspectives_run": 5, "perspectives_failed": 0},
        "has_findings": False,
    }
    assert save_cards("00000002", 2024, clean, [], 2024, root=tmp_path) is not None
