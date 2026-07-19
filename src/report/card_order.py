"""카드 정렬 단일 기준 — 가중합 폐지, 사전식(lexicographic) 비교.

가중치 점수(0.35·유의성 + 0.30·표수 + 0.15·이상 + 0.20·확신도)를 폐지했다. 성분별 가중치는
근거를 댈 수 없고("왜 금액이 표수보다 0.05 무거운가"), 단위가 다른 값을 한 축에 합쳐 "왜 이
카드가 위인가"에 답하지 못한다. 사전식은 기준을 순서대로 비교하므로 각 단계가 그대로 설명이
된다 — "관점 3곳이 겹쳤고, 같은 표수 안에서 금액이 가장 크다".

정렬 기준(순서대로):
  ① 반박 '정상우세' 카드는 하단으로 — 강등이지 제거가 아니다(§9 silent drop 금지)
  ② 표수 내림 — 독립 관점이 겹칠수록 위로
  ③ 금액 내림 — 같은 표수 안에서는 규모가 큰 쪽이 위로

화면·마크다운 리포트·외부검증 대상 선정이 모두 이 함수를 쓴다. 이전에는 화면만 가중합
점수로 정렬해 같은 분석 결과가 보는 곳에 따라 1등 카드가 달라졌다.
"""

from __future__ import annotations

from typing import Any

NORMAL_DOMINANT = "normal_dominant"


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """카드는 AccountFinding 객체로도 저장 dict로도 흐른다 — 양쪽 모두 지원."""

    if isinstance(obj, dict):
        return obj.get(key, default)
    value = getattr(obj, key, default)
    return default if value is None else value


def card_sort_key(card: Any) -> tuple[bool, int, float]:
    """계정·관계 카드 정렬 키 — 정상우세 하단 → 표수 내림 → 금액 내림."""

    return (
        _get(card, "rebuttal_verdict", "") == NORMAL_DOMINANT,
        -int(_get(card, "vote_count", 0) or 0),
        -float(_get(card, "materiality_score", 0.0) or 0.0),
    )


def company_sort_key(card: Any) -> tuple[bool, int, str]:
    """회사 카드 정렬 키 — 금액 앵커가 없어 금액 대신 계정명으로 동점을 깬다."""

    return (
        _get(card, "rebuttal_verdict", "") == NORMAL_DOMINANT,
        -int(_get(card, "vote_count", 0) or 0),
        str(_get(card, "account", "") or ""),
    )


def order_cards(cards: list) -> list:
    """계정·관계 카드 정렬(원본 불변)."""

    return sorted(cards, key=card_sort_key)


def order_company_cards(cards: list) -> list:
    """회사레벨 카드 정렬(원본 불변)."""

    return sorted(cards, key=company_sort_key)


__all__ = [
    "NORMAL_DOMINANT",
    "card_sort_key",
    "company_sort_key",
    "order_cards",
    "order_company_cards",
]
