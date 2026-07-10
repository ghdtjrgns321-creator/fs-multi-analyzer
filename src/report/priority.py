"""연속 우선순위 점수 — High/Medium/Low 라벨 폐지(PLAN §5 조사 단계 4항).

성분은 전부 코드 산정값: 유의성(0..1 정규화 금액)·표수 비율·이상신호·확신도.
임계로 자르지 않는다 — 정렬·외부검증 대상 선정에만 쓴다(등급 컷 금지, 문제⑤).
"""

from __future__ import annotations

from src.schemas.findings import AccountFinding

_CONFIDENCE_NUM = {"High": 1.0, "Medium": 0.5, "Low": 0.0}


def compute_priority(card: AccountFinding, weights: dict[str, float]) -> float:
    votes = card.vote_count / card.internal_total if card.internal_total else 0.0
    parts = {
        "materiality": min(max(card.materiality_score, 0.0), 1.0),
        "votes": min(max(votes, 0.0), 1.0),
        "anomaly": min(max(card.anomaly_score, 0.0), 1.0),
        "confidence": _CONFIDENCE_NUM.get(str(card.confidence), 0.0),
    }
    total = sum(weights.values()) or 1.0
    return round(sum(weights.get(k, 0.0) * v for k, v in parts.items()) / total, 4)


def apply_priority(cards: list[AccountFinding], weights: dict[str, float]) -> None:
    for card in cards:
        card.priority_score = compute_priority(card, weights)


__all__ = ["apply_priority", "compute_priority"]
