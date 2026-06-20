"""온보딩 일괄 실행 오케스트레이터·분석 진입 판정 테스트(결함② 한버튼 필수화)."""

from __future__ import annotations

import pytest


@pytest.fixture
def ob(monkeypatch):
    """dashboard.onboarding 모듈 — 하위 단계는 테스트마다 monkeypatch로 대체."""

    from dashboard import onboarding as module

    return module


def _stub_ok(module, monkeypatch):
    monkeypatch.setattr(
        module, "run_gate", lambda c, y: {"gate_passed": True, "G6_dump": {"dump_path": None}}
    )
    monkeypatch.setattr(
        module, "run_review_chunk_selection", lambda c, y: {"status": "ok", "selection": None}
    )
    monkeypatch.setattr(module, "suggest_aliases", lambda c, y: {"status": "ok", "result": None})
    monkeypatch.setattr(module, "run_llm_holistic", lambda d: {"status": "ok", "findings": "x"})


def test_run_full_onboarding_runs_all_four_stages(ob, monkeypatch):
    _stub_ok(ob, monkeypatch)
    out = ob.run_full_onboarding("00110893", "2024")
    assert {"gate", "review_chunks", "alias", "holistic"} <= set(out)
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


def test_run_full_onboarding_skips_holistic_without_dump(ob, monkeypatch):
    """gate가 dump를 못 만들면(실패/미생성) G6를 빈 입력으로 LLM 호출하지 않는다(P1)."""

    _stub_ok(ob, monkeypatch)  # _stub_ok의 gate는 dump_path=None
    called: list = []
    monkeypatch.setattr(ob, "run_llm_holistic", lambda d: called.append(d) or {"status": "ok"})
    out = ob.run_full_onboarding("00110893", "2024")
    assert out["holistic"]["status"] == "skipped"
    assert called == []  # 빈 dump로 LLM 미호출


def test_can_enter_analysis_reason_marks_which_stage(ob):
    """absent(원문없음)와 error(LLM실패)를 reason에 status로 구분 노출(P2)."""

    verdict = ob.can_enter_analysis({"gate_passed": True}, s7_status="absent", g6_status="ok")
    assert "S7" in verdict["reason"] and "absent" in verdict["reason"]
    assert "G6" not in verdict["reason"]  # G6는 ok라 미언급


def test_can_enter_analysis_gate_fail_blocks(ob):
    verdict = ob.can_enter_analysis({"gate_passed": False}, s7_status="ok", g6_status="ok")
    assert verdict["can_enter"] is False


def test_can_enter_analysis_all_ok_no_override(ob):
    verdict = ob.can_enter_analysis({"gate_passed": True}, s7_status="ok", g6_status="ok")
    assert verdict["can_enter"] is True
    assert verdict["needs_override"] is False


def test_can_enter_analysis_llm_fail_needs_override(ob):
    """게이트는 통과했지만 LLM 단계가 실패하면 경고+사람확인 강행(needs_override)."""

    verdict = ob.can_enter_analysis({"gate_passed": True}, s7_status="error", g6_status="ok")
    assert verdict["needs_override"] is True
