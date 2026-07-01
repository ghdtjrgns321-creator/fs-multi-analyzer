"""model_retry — 일시적 vs 영구 모델 오류 분류.

핵심: 429라도 크레딧 소진(insufficient_quota)은 재시도해도 영구 실패이므로 일시적이
아니다(헛재시도 방지). 일반 429(rate_limit)는 일시적으로 유지한다.
"""

from __future__ import annotations

from pydantic_ai.exceptions import ModelHTTPError

from src.agents.model_retry import is_temporary_model_error


def _http_error(status: int, body: object) -> ModelHTTPError:
    return ModelHTTPError(status_code=status, model_name="gpt-5.4", body=body)


def test_insufficient_quota_is_permanent() -> None:
    # 크레딧 소진 — 재시도해도 영구 실패. 일시적 아님(False).
    exc = _http_error(
        429,
        {"type": "insufficient_quota", "code": "insufficient_quota", "message": "quota exceeded"},
    )
    assert is_temporary_model_error(exc) is False


def test_plain_429_rate_limit_is_temporary() -> None:
    # 일반 속도제한 429 — 잠시 후 풀림. 일시적(True) 유지.
    exc = _http_error(429, {"type": "rate_limit_exceeded", "message": "slow down"})
    assert is_temporary_model_error(exc) is True


def test_server_5xx_is_temporary() -> None:
    exc = _http_error(503, {"message": "service unavailable"})
    assert is_temporary_model_error(exc) is True


def test_client_4xx_is_permanent() -> None:
    exc = _http_error(400, {"message": "bad request"})
    assert is_temporary_model_error(exc) is False
