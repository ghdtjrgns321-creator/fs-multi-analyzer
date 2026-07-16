"""검사1 수치 골든 하니스 단위 테스트 (설계: golden/DESIGN.md §2).

합성 카드 + 합성 인덱스로 결정론 검증 — LLM 없이 하니스 판정 로직만 본다.
정상 카드는 PASS, 환각/오환산 카드는 각각 value_mismatch/convert_fail을 내야 한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from golden.numeric.check_numeric import (
    check_decomposition_identity,
    convert_ok,
    decode_krw,
    reconcile_cards,
    run_saved_cards,
)

# 합성 원천 인덱스: 계정 식별자 → 그 계정 금액들의 유효숫자 집합(grounding._sig 형식).
INDEX = {
    "CFS:당기순이익": {"85778983809"},  # -85,778,983,809 의 유효숫자
    "당기순이익": {"85778983809"},
    "CFS:매출": {"12534698783"},  # 1,253,469,878,300 규모(예시)
}


def _card(account, evidence, claims=None):
    return {
        "account": account,
        "cluster_key": account,
        "numeric_evidence": evidence,
        "claims": claims or [],
    }


def _ev(locator, value, kind="account"):
    return {"locator": locator, "value": value, "year": "2025", "resolved_kind": kind}


# ---- decode_krw / convert_ok (1b 환산 무결의 원시 함수) ----


def test_decode_krw_handles_jo_eok_and_bare():
    assert decode_krw("1조 2,534.7억") == 1e12 + 2534.7e8
    assert decode_krw("858억") == 858e8
    assert decode_krw("-857.8억") == -857.8e8
    assert decode_krw("-85,778,983,809") == -85_778_983_809.0
    assert decode_krw("") is None


def test_convert_ok_passes_correct_rounds_rejects_tenfold():
    raw = 1_253_469_878_367.0
    assert convert_ok(raw, "1조 2,534.7억") is True  # 정상 환산(반올림 허용)
    assert convert_ok(raw, "1,253.47억") is False  # ÷10 축소(LG결함②) → 거부
    # 억 정수 반올림도 정상 통과(858억 ← -85,778,983,809 절대값)
    assert convert_ok(85_778_983_809.0, "858억") is True


# ---- reconcile_cards: 4 verdict ----


def test_reconcile_match_when_value_in_source():
    cards = [_card("CFS:당기순이익", [_ev("CFS:당기순이익", "-85,778,983,809")])]
    result = reconcile_cards(cards, INDEX)
    assert result["summary"]["value_mismatch"] == 0
    assert result["summary"]["unreconcilable"] == 0
    assert result["summary"]["match"] >= 1


def test_reconcile_flags_hallucinated_value():
    # 계정은 존재하나 인용 금액이 원천에 없음 → value_mismatch(환각).
    cards = [_card("CFS:당기순이익", [_ev("CFS:당기순이익", "-99,999,999,999")])]
    result = reconcile_cards(cards, INDEX)
    assert result["summary"]["value_mismatch"] >= 1


def test_reconcile_flags_convert_fail_with_broken_formatter():
    # -85,778,983,809 ≈ 858억. formatter가 1/10(85.8억)로 표기하면(÷10 회귀) convert_fail.
    cards = [_card("CFS:당기순이익", [_ev("CFS:당기순이익", "-85,778,983,809")])]
    broken = lambda v: "-85.8억"  # noqa: E731  정답 857.8억의 1/10
    result = reconcile_cards(cards, INDEX, formatter=broken)
    assert result["summary"]["convert_fail"] >= 1


def test_reconcile_buckets_unreconcilable_account():
    # 인덱스에 없는 계정 → unreconcilable(조용히 통과 금지, 별도 버킷).
    cards = [_card("CFS:존재하지않는계정", [_ev("CFS:존재하지않는계정", "123,456,789")])]
    result = reconcile_cards(cards, INDEX)
    assert result["summary"]["unreconcilable"] >= 1
    assert result["summary"]["match"] == 0


def test_reconcile_verifies_claim_cited_value():
    # 주장 인용값도 카드 앵커(cluster_key) 계정 풀로 대조한다.
    claims = [{"perspective": "numeric", "description": "적자", "cited_value": "-85,778,983,809"}]
    cards = [_card("CFS:당기순이익", [], claims=claims)]
    result = reconcile_cards(cards, INDEX)
    assert result["summary"]["match"] >= 1
    assert result["summary"]["value_mismatch"] == 0


def test_reconcile_handles_annotated_amount_format():
    # 카드가 '원값(1,253.5억)' 병기 포맷으로 저장되면: 원값은 인덱스 대조, 괄호 안 표기는 1b 검증.
    idx = {"CFS:매출": {"12534698783"}}  # 1,253,469,878,300 규모의 유효숫자
    good = [_card("CFS:매출", [_ev("CFS:매출", "1,253,469,878,300(1조 2,534.7억)")])]
    result = reconcile_cards(good, idx)
    assert result["summary"]["match"] == 1  # 원값 실재 + 병기 환산 정확
    # 병기 표기가 ÷10 오류(125.3억)면 convert_fail(원값은 맞지만 환산 붕괴).
    bad = [_card("CFS:매출", [_ev("CFS:매출", "1,253,469,878,300(125.3억)")])]
    assert reconcile_cards(bad, idx)["summary"]["convert_fail"] == 1


# ---- 분해 산술 항등 ----


def test_decomposition_identity_ok():
    # Σleaves(= children delta) == 부모 delta → 통과.
    decomp = {
        "parent": "CFS:영업이익",
        "delta": -100.0,
        "residual": 0.0,
        "rows": [
            {"account": "매출원가", "delta": -70.0},
            {"account": "판관비", "delta": -30.0},
        ],
    }
    assert check_decomposition_identity(decomp) is True


def test_decomposition_identity_detects_broken_sum():
    # leaf 합이 부모 delta와 1원 넘게 어긋나면 실패.
    decomp = {
        "parent": "CFS:영업이익",
        "delta": -100.0,
        "residual": 0.0,
        "rows": [
            {"account": "매출원가", "delta": -70.0},
            {"account": "판관비", "delta": -10.0},  # 합 -80, 부모 -100 → 20 갭
        ],
    }
    assert check_decomposition_identity(decomp) is False


# ---- 실데이터 회귀 가드(저장 카드 + 정규화 DB 존재 시만) ----

_REAL_CORP, _REAL_YEAR = "00356370", 2025
_HAS_REAL_DATA = Path(f"data/companies/{_REAL_CORP}/{_REAL_YEAR}/suspicion_cards.json").exists()


@pytest.mark.skipif(not _HAS_REAL_DATA, reason="저장 카드/DB 없음(수집 필요)")
def test_real_saved_cards_reconcile_clean():
    # 저장 카드 전 수치가 원천 DART 값과 일치(불일치·대사불능 0). 코드가 카드 수치를
    # 오염시키면(환산·부호·역추적) 여기서 FAIL한다 — 검사1의 실데이터 회귀 가드.
    result = run_saved_cards(_REAL_CORP, _REAL_YEAR)
    summary = result["summary"]
    assert summary["n"] > 0, "대조 대상 수치가 0 — 카드 추출 경로 확인"
    assert summary["value_mismatch"] == 0, f"원값 불일치: {summary}"
    assert summary["convert_fail"] == 0, f"환산 오류: {summary}"
    assert summary["unreconcilable"] == 0, f"대사 불능: {summary}"
