"""온보딩 일괄 실행 오케스트레이터·분석 진입 판정 테스트.

온보딩 = Layer 1 서술추출 + 게이트 + 별칭 제안(3단계). 감사 소견은 Phase2 전담.
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
    """Layer1이 예외를 던져도 뒤 단계(gate·alias)는 그대로 진행(한 단계 실패=전체 중단 금지)."""

    _stub_ok(ob, monkeypatch)

    def boom(c, y):
        raise RuntimeError("api down")

    monkeypatch.setattr(ob, "run_layer1_stage", boom)
    out = ob.run_full_onboarding("00110893", "2024")
    assert out["layer1"]["status"] == "error"  # 실패는 error로 흡수
    assert out["gate"]["gate_passed"] is True  # 뒤 단계 계속
    assert out["alias"]["status"] == "ok"  # 뒤 단계 계속


def test_run_full_onboarding_layer1_runs_before_gate(ob, monkeypatch):
    """실행 순서 계약 — Layer1(준비)은 게이트 앞, alias(보정)는 게이트 뒤.

    Layer1은 게이트 결과를 입력으로 받지 않는 독립 수집이고, alias만 게이트가
    지적한 미매핑 계정을 메우는 보정이다. 순서가 뒤집히면 문서의 국면 구분과 어긋난다.
    """

    calls: list[str] = []
    monkeypatch.setattr(ob, "run_gate", lambda c, y: calls.append("gate") or {"gate_passed": True})
    monkeypatch.setattr(
        ob,
        "run_layer1_stage",
        lambda c, y, on_progress=None: calls.append("layer1") or {"status": "ok", "extracts": []},
    )
    monkeypatch.setattr(
        ob,
        "suggest_aliases",
        lambda c, y: calls.append("alias") or {"status": "ok", "result": None},
    )
    ob.run_full_onboarding("00110893", "2024")
    assert calls == ["layer1", "gate", "alias"]


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


# ── alias 자동 등록 스테이지 배선 — 등록>0이면 재정규화, 0이면 생략 ──────────
def _alias_result_one_suggestion():
    from src.report.alias_suggest import AliasSuggestion, AliasSuggestionResult

    return AliasSuggestionResult(
        suggestions=[AliasSuggestion(alias="확실계정", suggested_canonical="X", confidence=0.9)]
    )


def _wire_autoreg(ob, monkeypatch, registered: int) -> list:
    """suggest_aliases·자동등록·재정규화를 stub — 재정규화 호출 기록 리스트 반환."""

    _stub_ok(ob, monkeypatch)
    monkeypatch.setattr(
        ob,
        "suggest_aliases",
        lambda c, y: {"status": "ok", "result": _alias_result_one_suggestion()},
    )
    monkeypatch.setattr(
        ob, "auto_register_aliases", lambda *a, **k: {"registered": registered, "held": 0}
    )
    monkeypatch.setattr("src.report.prep.raw_present", lambda *a, **k: True)
    renorm_calls: list = []
    monkeypatch.setattr(
        "src.normalize.spike.normalize_company_years",
        lambda *a, **k: renorm_calls.append(a),
    )
    return renorm_calls


def test_autoreg_renormalizes_when_registered(ob, monkeypatch):
    renorm_calls = _wire_autoreg(ob, monkeypatch, registered=2)
    out = ob.run_full_onboarding("00110893", "2024")
    assert out["alias_autoreg"]["registered"] == 2
    assert len(renorm_calls) == 1  # 등록 ≥1 → window 재정규화 1회
    assert out["alias_autoreg"]["renormalized"] == [2020, 2021, 2022, 2023, 2024]


def test_autoreg_skips_renorm_when_nothing_registered(ob, monkeypatch):
    renorm_calls = _wire_autoreg(ob, monkeypatch, registered=0)
    out = ob.run_full_onboarding("00110893", "2024")
    assert out["alias_autoreg"]["registered"] == 0
    assert renorm_calls == []  # 등록 0 → 재정규화 생략(불필요 비용 금지)
