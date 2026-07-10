"""Contract 34 — LLM 비용 추정·토큰 추출."""

from src.agents.cost import estimate_krw, extract_tokens


def test_estimate_krw_matches_assumed_pricing():
    # 입력 1e6 tok · 출력 0 → 1e6 × 2.5/1e6 × 1380 = ₩3450
    assert estimate_krw(1_000_000, 0) == 3450.0


class _FakeUsage:
    request_tokens = 1200
    response_tokens = 300


def test_extract_tokens_from_method_and_attr():
    # 메서드형(usage())·속성형 둘 다 지원
    assert extract_tokens(lambda: _FakeUsage()) == (1200, 300)
    assert extract_tokens(_FakeUsage()) == (1200, 300)
    # None·실패는 (0,0) graceful
    assert extract_tokens(None) == (0, 0)
