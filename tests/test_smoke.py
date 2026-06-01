"""스캐폴딩 smoke 테스트 — 스키마 import + 최소 구성 검증."""

from src.schemas import AccountFinding, DisclosureChangeFinding, IssueType


def test_account_finding_minimal() -> None:
    finding = AccountFinding(
        account="매출채권",
        issue_type=IssueType.RECEIVABLES_QUALITY,
        materiality_score=0.0,
        anomaly_score=0.0,
        confidence="Low",
        risk_level="Low",
    )
    assert finding.issue_type is IssueType.RECEIVABLES_QUALITY
    assert finding.numeric_evidence == []


def test_disclosure_change_finding_minimal() -> None:
    finding = DisclosureChangeFinding(
        target="우발부채",
        issue_type=IssueType.DISCLOSURE_CHANGE,
        materiality_score=0.0,
        confidence="Low",
        risk_level="Low",
    )
    assert finding.cross_inconsistency is None
