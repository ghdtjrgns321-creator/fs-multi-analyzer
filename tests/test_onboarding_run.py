"""온보딩 일괄 실행 오케스트레이터·분석 진입 판정 테스트.

온보딩 = 게이트 + S7 청크선별 + 별칭 제안(3단계). G6 홀리스틱은 제거(감사 소견=Phase2 전담).
"""

from __future__ import annotations

import pytest


@pytest.fixture
def ob(monkeypatch):
    """dashboard.onboarding 모듈 — 하위 단계는 테스트마다 monkeypatch로 대체."""

    from dashboard import onboarding as module

    return module


def _stub_ok(module, monkeypatch):
    monkeypatch.setattr(module, "run_gate", lambda c, y: {"gate_passed": True})
    monkeypatch.setattr(
        module, "run_review_chunk_selection", lambda c, y: {"status": "ok", "selection": None}
    )
    monkeypatch.setattr(module, "suggest_aliases", lambda c, y: {"status": "ok", "result": None})


def test_run_full_onboarding_runs_three_stages(ob, monkeypatch):
    _stub_ok(ob, monkeypatch)
    out = ob.run_full_onboarding("00110893", "2024")
    assert {"gate", "review_chunks", "alias"} <= set(out)
    assert "holistic" not in out  # G6 제거 — 온보딩은 감사 소견을 내지 않는다
    assert out["gate"]["gate_passed"] is True


def test_run_full_onboarding_graceful_when_stage_raises(ob, monkeypatch):
    """S7이 예외를 던져도 gate 결과는 보존되고 나머지 단계도 진행(한 단계 실패=전체 중단 금지)."""

    _stub_ok(ob, monkeypatch)

    def boom(c, y):
        raise RuntimeError("api down")

    monkeypatch.setattr(ob, "run_review_chunk_selection", boom)
    out = ob.run_full_onboarding("00110893", "2024")
    assert out["gate"]["gate_passed"] is True  # 앞 단계 보존
    assert out["review_chunks"]["status"] == "error"  # 실패는 error로 흡수
    assert out["alias"]["status"] == "ok"  # 뒤 단계 계속


def test_can_enter_analysis_reason_marks_s7_status(ob):
    """absent(원문없음)와 error(LLM실패)를 reason에 status로 구분 노출."""

    verdict = ob.can_enter_analysis({"gate_passed": True}, s7_status="absent")
    assert "S7" in verdict["reason"] and "absent" in verdict["reason"]


def test_can_enter_analysis_gate_fail_blocks(ob):
    verdict = ob.can_enter_analysis({"gate_passed": False}, s7_status="ok")
    assert verdict["can_enter"] is False


def test_can_enter_analysis_s7_ok_no_override(ob):
    verdict = ob.can_enter_analysis({"gate_passed": True}, s7_status="ok")
    assert verdict["can_enter"] is True
    assert verdict["needs_override"] is False


def test_can_enter_analysis_s7_fail_needs_override(ob):
    """게이트는 통과했지만 S7이 실패하면 경고+사람확인 강행(needs_override)."""

    verdict = ob.can_enter_analysis({"gate_passed": True}, s7_status="error")
    assert verdict["needs_override"] is True
