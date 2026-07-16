"""금액 환산 표기 — 계산은 코드(PLAN §3), LLM은 베껴 쓰기만 한다.

LLM에게 원 단위 → 억/조 나누기를 시키면 자릿수를 오독한다(LG생건 감사 결함②:
1조2,534.7억을 1,253.47억으로 축소). LLM 입력 경계(json.dumps 직전)에서
annotate_amounts로 원값에 환산 표기를 병기해 환산 작업 자체를 제거한다.
"""

from __future__ import annotations

# 병기 대상 최소 금액(1억) — 비율·연도·건수 등 소수치를 금액으로 오인하지 않는 임계.
ANNOTATE_THRESHOLD = 1e8
_EOK = 1e8
_JO_IN_EOK = 10_000


def _trim(text: str) -> str:
    return text.removesuffix(".0")


def format_krw(value: float) -> str:
    """원 단위 금액 → 사람용 억/조 표기. 예: 1_253_469_878_367 → '1조 2,534.7억'."""

    amount = round(float(value))
    sign = "-" if amount < 0 else ""
    eok = abs(amount) / _EOK
    jo, rem = divmod(eok, _JO_IN_EOK)
    if jo >= 1:
        head = f"{sign}{int(jo):,}조"
        return f"{head} {_trim(f'{rem:,.1f}')}억" if round(rem, 1) else head
    return f"{sign}{_trim(f'{eok:,.1f}')}억"


def annotate_amounts(obj: object, threshold: float = ANNOTATE_THRESHOLD) -> object:
    """LLM 입력 구조 안의 큰 금액에 환산 표기를 병기한 새 구조를 반환(원본 불변).

    숫자 리프(|v| ≥ threshold)만 '1,253,469,878,367(1조 2,534.7억)' 문자열로 바꾼다.
    원값이 앞에 남으므로 grounding 유효숫자 대조는 그대로 통과한다.
    """

    if isinstance(obj, dict):
        return {key: annotate_amounts(value, threshold) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [annotate_amounts(value, threshold) for value in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)) and abs(obj) >= threshold:
        return f"{int(round(obj)):,}({format_krw(obj)})"
    return obj


__all__ = ["ANNOTATE_THRESHOLD", "annotate_amounts", "format_krw"]
