"""연속 우선순위 점수 — priority.py (PLAN §5 조사 단계 4항, High/Medium/Low 라벨 폐지)."""

from __future__ import annotations

from src.report.priority import apply_priority, compute_priority

from src.schemas.findings import AccountFinding, IssueType

WEIGHTS = {"materiality": 0.35, "votes": 0.30, "anomaly": 0.15, "confidence": 0.20}


def _card(**kw) -> AccountFinding:
    base = dict(
        account="CFS:영업이익",
        issue_type=IssueType.EARNINGS_TAX,
        materiality_score=1.0,
        anomaly_score=1.0,
        confidence="High",
        vote_count=4,
        internal_total=4,
    )
    base.update(kw)
    return AccountFinding(**base)


def test_full_signals_score_one():
    assert compute_priority(_card(), WEIGHTS) == 1.0


def test_zero_signals_score_zero():
    card = _card(materiality_score=0.0, anomaly_score=0.0, confidence="Low", vote_count=0)
    assert compute_priority(card, WEIGHTS) == 0.0


def test_monotonic_in_votes():
    low = compute_priority(_card(vote_count=1), WEIGHTS)
    high = compute_priority(_card(vote_count=3), WEIGHTS)
    assert high > low


def test_apply_priority_sets_field():
    cards = [_card(vote_count=0), _card(vote_count=4)]
    apply_priority(cards, WEIGHTS)
    assert cards[1].priority_score > cards[0].priority_score


def test_risk_level_now_optional_default_none():
    assert _card().risk_level is None
