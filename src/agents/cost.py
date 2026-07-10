"""LLM 비용 추정(가정단가) — 화면에 띄우지 않고 서버 콘솔 로그·관찰용.

토큰 사용량을 원화로 근사한다. 실제 청구액이 아니라 진행 관찰·감사추적용 추정치다(단가는 가정).
관점·반박·리더 등 모든 agent 호출이 run_with_retry를 지나므로, 거기서 log_usage를 부르면
전 호출의 토큰·원화가 콘솔에 남는다(관통 배선 불필요).
"""

from __future__ import annotations

import logging
import warnings

# LLM 비용 추정 단가(가정 — gpt-5.4 기준, 실단가 확정 시 조정). 입력/출력 $/token · 환율.
_PRICE_IN = 2.5 / 1e6
_PRICE_OUT = 10 / 1e6
_KRW_PER_USD = 1380


def estimate_krw(input_tokens: int, output_tokens: int) -> float:
    """토큰 사용량 → 원화 추정(가정단가). 관찰·표시용이며 청구액이 아니다."""

    return (input_tokens * _PRICE_IN + output_tokens * _PRICE_OUT) * _KRW_PER_USD


def extract_tokens(usage) -> tuple[int, int]:
    """pydantic-ai usage(속성 또는 메서드)에서 (input, output) 토큰. 실패는 (0,0) graceful."""

    try:
        u = usage
        if callable(u):
            # 구 pydantic-ai는 usage가 메서드(호출 시 deprecation 경고) — 경고만 눌러 콘솔 잡음 방지.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                u = u()
    except Exception:  # noqa: BLE001 — 비용 로깅이 본 호출을 깨지 않게
        return 0, 0
    if u is None:
        return 0, 0
    # pydantic-ai 신 이름(input/output) 우선, 구 이름(request/response) 폴백.
    in_tok = getattr(u, "input_tokens", None)
    out_tok = getattr(u, "output_tokens", None)
    if in_tok is None:
        in_tok = getattr(u, "request_tokens", 0)
    if out_tok is None:
        out_tok = getattr(u, "response_tokens", 0)
    return (in_tok or 0, out_tok or 0)


def log_usage(label: str, usage, logger: logging.Logger | None = None) -> tuple[int, int]:
    """토큰·원화를 콘솔 로그(화면 아님). (input, output) 반환. 실패해도 조용히 넘어간다."""

    in_tok, out_tok = extract_tokens(usage)
    if in_tok or out_tok:
        (logger or logging.getLogger("cost")).info(
            "%s: 토큰 in %d/out %d · ~₩%.0f", label, in_tok, out_tok, estimate_krw(in_tok, out_tok)
        )
    return in_tok, out_tok
