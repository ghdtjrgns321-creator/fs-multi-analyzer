"""신호 유효성 원장 — lift 계산과 계정적중 판정 테스트."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "_signal_validity_ledger", ROOT / "data" / "backtest" / "_signal_validity_ledger.py"
)
assert _spec and _spec.loader
ledger = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ledger)


def _result(pos_fire, ctl_fire, pos_hit=None, pos_cy=20, ctl_cy=200) -> dict:
    return {
        "positives": [],
        "n_positive": 5,
        "n_control": 40,
        "pos_company_years": pos_cy,
        "ctl_company_years": ctl_cy,
        "pos_fire": pos_fire,
        "pos_hit": pos_hit or {},
        "ctl_fire": ctl_fire,
        "definitions": {},
    }


def test_lift_uses_company_year_denominator():
    """분모는 회사연도 — 회사 수로 나누면 관측 연도 차이가 편향을 만든다."""

    # 분식 10/20(50%) vs 대조 20/200(10%) → lift 5.0
    text = ledger.render(_result({"x": 10}, {"x": 20}))
    assert "5.00" in text
    assert "10/20" in text and "20/200" in text


def test_no_discrimination_shows_lift_near_one():
    text = ledger.render(_result({"x": 10}, {"x": 100}))  # 50% vs 50%
    assert "1.00" in text


def test_never_fires_on_fraud_is_zero_lift():
    text = ledger.render(_result({}, {"x": 50}))
    assert "0.00" in text


def test_limits_are_printed_with_every_report():
    """한계를 산출물에 박는다 — 이 표로 '유효함'을 증명하지 않는다는 문구가 항상 나온다."""

    text = ledger.render(_result({"x": 1}, {"x": 1}))
    assert "한계" in text
    assert "unlabeled" in text
    assert "확정 근거로 쓰지 않는다" in text


def test_account_overlap_detects_label_match():
    assert ledger._overlaps({"재고자산"}, ["재고자산", "매출원가"]) is True
    assert ledger._overlaps({"무형자산"}, ["개발비(무형자산)"]) is True  # 부분 문자열
    assert ledger._overlaps({"현금및현금성자산"}, ["재고자산", "매출원가"]) is False


def test_positive_cases_come_from_labels_not_hand_list():
    """모집단은 labels.csv에서 뽑는다. 손으로 만든 목록이면 그 시점에 실패한다."""

    cases = ledger.positive_cases()
    assert cases, "positive 라벨 ∩ 코퍼스가 비었다"
    for case in cases:
        assert case["fraud_years"], f"{case['company']}: 분식 연도가 코퍼스에 없다"
        assert set(case["fraud_years"]) <= set(case["years"])
