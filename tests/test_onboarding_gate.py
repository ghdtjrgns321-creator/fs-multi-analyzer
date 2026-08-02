"""온보딩 게이트 G1 판정 — hollow-PASS 차단(BS 검산 0건은 통과 아님) 테스트."""

from __future__ import annotations

from src.normalize.onboarding_gate import _currency_ok, _g1_verdict


def _resid() -> list[dict]:
    return [{"line": "[CFS] 자산 100 = 부채 60+자본 40? 차이 0", "resid_won": 0}]


def test_g1_verdict_normal_passes() -> None:
    # BS 검산행 존재 + 이탈 없음 + returncode 0 → 통과
    assert _g1_verdict(_resid(), [], 0) is True


def test_g1_verdict_empty_bs_residuals_fails() -> None:
    """BS 항등식 검산이 0건이면 '검산 못함'이지 통과 아님(hollow-PASS 차단, §9).

    회귀 방지: 자산총계 등 BS 핵심행이 결손되면 검산행 0 → 빈 검사가 통과로 둔갑하던 갭.
    """

    assert _g1_verdict([], [], 0) is False


def test_g1_verdict_bs_break_blocks() -> None:
    # BS 항등식 잔차가 tol 초과(bs_breaks 존재) → FAIL
    assert _g1_verdict(_resid(), [{"line": "x", "resid_won": 9_999_999}], 0) is False


def test_g1_verdict_nonzero_returncode_blocks() -> None:
    assert _g1_verdict(_resid(), [], 1) is False


def test_currency_ok_krw_passes() -> None:
    assert _currency_ok({"KRW"}) is True
    assert _currency_ok({"KRW", ""}) is True  # 빈값은 KRW 취급


def test_currency_ok_foreign_blocks() -> None:
    """외화(USD 등) 재무는 원화 환산 없이 분석 불가 → 게이트 차단(silent 1300배 오차 방지)."""

    assert _currency_ok({"USD"}) is False
    assert _currency_ok({"KRW", "USD"}) is False  # 일부라도 외화면 차단


def test_currency_ok_shares_unit_passes() -> None:
    """SHARES(주당이익·주식수 단위)는 통화가 아니라 단위 표기 → 외화 오판 차단 금지.

    원본 XBRL 유래 as-filed 데이터의 주당이익 행이 currency=SHARES로 실림(정상 수집은 KRW).
    SHARES는 환율 오차 위험이 없으므로 KRW와 함께 있어도 통과해야 한다(USD 등 실외화는 여전히 차단).
    """

    assert _currency_ok({"SHARES"}) is True
    assert _currency_ok({"KRW", "SHARES"}) is True
    assert _currency_ok({"KRW", "SHARES", "USD"}) is False  # 실외화는 SHARES와 무관하게 차단


def test_g1_verdict_sce_standardization_fail_blocks() -> None:
    """SCE 표준화 사망(전 행 unmatched, SCE표준화=FAIL)은 검산이 정상이어도 통과 아님.

    회귀 방지: sce_equity_components에 셀은 있으나 전부 unmatched라 SCE 분석이 무력한데
    BS검산이 정상이면 게이트를 통과하던 갭(SCE-dead hollow-PASS). 이관 원장은 셀이 있으면
    '이관됨'으로 세므로 표준화 사망은 이 판정이 잡아야 한다.
    """

    assert _g1_verdict(_resid(), [], 0, sce_std="FAIL") is False
    # SCE 정상이면 통과(기본값 OK와 동일)
    assert _g1_verdict(_resid(), [], 0, sce_std="OK") is True
