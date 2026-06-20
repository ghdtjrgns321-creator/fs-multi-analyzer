"""온보딩 게이트 G1 판정 — hollow-PASS 차단(BS 검산 0건은 통과 아님) 테스트."""

from __future__ import annotations

from src.normalize.onboarding_gate import _currency_ok, _g1_verdict


def _resid() -> list[dict]:
    return [{"line": "[CFS] 자산 100 = 부채 60+자본 40? 차이 0", "resid_won": 0}]


def test_g1_verdict_normal_passes() -> None:
    # 완결성 OK + BS 검산행 존재 + 이탈 없음 + returncode 0 → 통과
    assert _g1_verdict("OK", _resid(), [], 0) is True


def test_g1_verdict_empty_bs_residuals_fails() -> None:
    """BS 항등식 검산이 0건이면 '검산 못함'이지 통과 아님(hollow-PASS 차단, §9).

    회귀 방지: 자산총계 등 BS 핵심행이 결손되면 검산행 0 → 빈 검사가 통과로 둔갑하던 갭.
    """

    assert _g1_verdict("OK", [], [], 0) is False


def test_g1_verdict_completeness_fail_blocks() -> None:
    assert _g1_verdict("FAIL", _resid(), [], 0) is False


def test_g1_verdict_bs_break_blocks() -> None:
    # BS 항등식 잔차가 tol 초과(bs_breaks 존재) → FAIL
    assert _g1_verdict("OK", _resid(), [{"line": "x", "resid_won": 9_999_999}], 0) is False


def test_g1_verdict_nonzero_returncode_blocks() -> None:
    assert _g1_verdict("OK", _resid(), [], 1) is False


def test_currency_ok_krw_passes() -> None:
    assert _currency_ok({"KRW"}) is True
    assert _currency_ok({"KRW", ""}) is True  # 빈값은 KRW 취급


def test_currency_ok_foreign_blocks() -> None:
    """외화(USD 등) 재무는 원화 환산 없이 분석 불가 → 게이트 차단(silent 1300배 오차 방지)."""

    assert _currency_ok({"USD"}) is False
    assert _currency_ok({"KRW", "USD"}) is False  # 일부라도 외화면 차단


def test_g1_verdict_sce_standardization_fail_blocks() -> None:
    """SCE 표준화 사망(전 행 unmatched, SCE표준화=FAIL)은 완결성 OK라도 통과 아님(BS 바닥과 대칭).

    회귀 방지: sce_equity_components에 행은 있으나 전부 unmatched라 SCE 분석이 무력한데
    completeness=OK·BS검산 정상이면 게이트를 통과하던 갭(SCE-dead hollow-PASS).
    """

    assert _g1_verdict("OK", _resid(), [], 0, sce_std="FAIL") is False
    # SCE 정상이면 통과(기본값 OK와 동일)
    assert _g1_verdict("OK", _resid(), [], 0, sce_std="OK") is True
