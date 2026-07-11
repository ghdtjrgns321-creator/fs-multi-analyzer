"""어휘 게이트 — 재료 키 자동 추출·서술 필드 위반 검출·구조 필드 면제."""

from __future__ import annotations

from src.report.vocab_guard import banned_identifiers, find_violations
from src.schemas.suspicion import PerspectiveOutput, SuspicionItem


def test_banned_identifiers_collects_nested_internal_keys():
    material = {
        "benchmark": [{"target_value": 2.69, "peer_median": 11.08, "roe": 1.0}],
        "ratio_time_series": [{"operating_margin": 3}],
        "queue": [{"delta_score": 0.5, "amount": 1, "trend": 0.1}],
    }
    banned = banned_identifiers(material)
    assert {"target_value", "peer_median", "ratio_time_series", "delta_score"} <= banned
    # 5자 이하 일반 단어·정당한 감사 약어는 금지하지 않는다(오탐 방지)
    assert "roe" not in banned and "trend" not in banned


def test_banned_identifiers_includes_long_single_word_keys():
    # 'decomposition상 residual이 0.0%' 재발 차단 — '_' 없는 단일단어 키(6자+)도 금지
    banned = banned_identifiers({"decomposition": {"residual": 0.0, "rows": []}})
    assert {"decomposition", "residual"} <= banned
    assert "rows" not in banned  # 5자 이하 제외


def test_find_violations_scans_prose_but_exempts_structural_fields():
    banned = {"target_value", "peer_median", "series_key"}
    output = PerspectiveOutput(
        status="completed",
        suspicions=[
            SuspicionItem(
                perspective="numeric",
                scope="account",
                description="target_value 2.69로 peer_median 대비 낮음",  # 위반 2
                issue_type="earnings_tax",
                account_id="CFS:영업이익",
                sj_div="IS",
                year="2025",
                cited_value="170,688,596,929",
                risk_level="High",
            )
        ],
    )
    hits = find_violations(output, banned)
    assert hits == ["peer_median", "target_value"]


def test_find_violations_clean_output_empty():
    banned = {"target_value"}
    output = {"description": "영업이익이 동종 대비 하위 22% 수준입니다", "locator": "target_value"}
    assert find_violations(output, banned) == []  # locator는 구조 필드 — 면제
