"""온보딩 일괄 실행 오케스트레이터·분석 진입 판정 테스트.

온보딩 = 게이트 + Layer 1 서술추출 + 별칭 제안(3단계). 감사 소견은 Phase2 전담.
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
        module, "run_layer1_stage", lambda c, y: {"status": "ok", "extracts": [], "warnings": []}
    )
    monkeypatch.setattr(module, "suggest_aliases", lambda c, y: {"status": "ok", "result": None})


def test_run_full_onboarding_runs_three_stages(ob, monkeypatch):
    _stub_ok(ob, monkeypatch)
    out = ob.run_full_onboarding("00110893", "2024")
    assert {"gate", "layer1", "alias"} <= set(out)
    assert "holistic" not in out  # 온보딩은 감사 소견을 내지 않는다
    assert out["gate"]["gate_passed"] is True


def test_run_full_onboarding_graceful_when_stage_raises(ob, monkeypatch):
    """Layer1이 예외를 던져도 gate 결과는 보존되고 나머지 단계도 진행(한 단계 실패=전체 중단 금지)."""

    _stub_ok(ob, monkeypatch)

    def boom(c, y):
        raise RuntimeError("api down")

    monkeypatch.setattr(ob, "run_layer1_stage", boom)
    out = ob.run_full_onboarding("00110893", "2024")
    assert out["gate"]["gate_passed"] is True  # 앞 단계 보존
    assert out["layer1"]["status"] == "error"  # 실패는 error로 흡수
    assert out["alias"]["status"] == "ok"  # 뒤 단계 계속


def test_can_enter_analysis_reason_marks_layer1_status(ob):
    """empty(추출0)·absent(원문없음)·error(LLM실패)를 reason에 status로 구분 노출."""

    verdict = ob.can_enter_analysis({"gate_passed": True}, layer1_status="empty")
    assert "Layer1" in verdict["reason"] and "empty" in verdict["reason"]


def test_can_enter_analysis_gate_fail_blocks(ob):
    verdict = ob.can_enter_analysis({"gate_passed": False}, layer1_status="ok")
    assert verdict["can_enter"] is False


def test_can_enter_analysis_layer1_ok_no_override(ob):
    verdict = ob.can_enter_analysis({"gate_passed": True}, layer1_status="ok")
    assert verdict["can_enter"] is True
    assert verdict["needs_override"] is False


def test_can_enter_analysis_layer1_empty_needs_override(ob):
    """게이트는 통과했지만 Layer1 추출이 비면 경고+사람확인 강행(needs_override)."""

    verdict = ob.can_enter_analysis({"gate_passed": True}, layer1_status="empty")
    assert verdict["needs_override"] is True
