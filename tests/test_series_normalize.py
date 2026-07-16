"""설계1 — 시계열 표기변경 정규화(cross-report 대조).

LG생건 감사 결함①: 회사가 표기 방식만 바꾼 것(유출액 양수→유출 음수)을 연도별
당기값 스티칭이 '부호 반전 사건'으로 둔갑시켰다. 다음 해 보고서의 재표시 전기값
(이미 DB에 저장된 prior_amount/prior2_amount)을 권위로 부호를 정규화한다.
"""

from __future__ import annotations

import pandas as pd
from src.report.series_normalize import normalize_presentation


def _frame(rows: list[dict]) -> pd.DataFrame:
    base = {
        "fs_div": "CFS",
        "sj_div": "CF",
        "canonical": "투자활동현금유출",
        "label": "투자활동으로부터의 현금유출",
        "prior_amount": None,
        "prior2_amount": None,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


class TestSignNormalization:
    def test_lg_hh_sign_flip_normalized_to_latest_presentation(self):
        # 실사례: 2024까지 유출을 양수로, 2025부터 음수로 표기. 2025 보고서의 재표시
        # 전기(-1666)·전전기(-2105)가 권위 — 2023·2024 부호를 음수로 정규화한다.
        frame = _frame(
            [
                {"year": 2023, "amount": 2105.0, "prior_amount": 2900.0},
                {"year": 2024, "amount": 1666.0, "prior_amount": 2105.0, "prior2_amount": 2900.0},
                {
                    "year": 2025,
                    "amount": -1905.0,
                    "prior_amount": -1666.0,
                    "prior2_amount": -2105.0,
                },
            ]
        )
        out, changes = normalize_presentation(frame)
        amounts = dict(zip(out["year"], out["amount"]))
        assert amounts == {2023: -2105.0, 2024: -1666.0, 2025: -1905.0}
        flagged = dict(zip(out["year"], out["presentation_change"]))
        assert flagged == {2023: True, 2024: True, 2025: False}
        assert {c["kind"] for c in changes} == {"sign_normalized"}
        assert {c["year"] for c in changes} == {2023, 2024}

    def test_latest_report_wins_over_adjacent(self):
        # 2023은 2024 보고서(prior=+2105)와 2025 보고서(prior2=-2105)가 다르게 재표시 —
        # 최신(2025) 표기가 권위다(인접만 보면 2023·2024 사이에 새 아티팩트가 생긴다).
        frame = _frame(
            [
                {"year": 2023, "amount": 2105.0},
                {"year": 2024, "amount": 1666.0, "prior_amount": 2105.0},
                {
                    "year": 2025,
                    "amount": -1905.0,
                    "prior_amount": -1666.0,
                    "prior2_amount": -2105.0,
                },
            ]
        )
        out, _ = normalize_presentation(frame)
        assert dict(zip(out["year"], out["amount"]))[2023] == -2105.0


class TestRestatementFlag:
    def test_abs_mismatch_flags_restatement_without_touching_amount(self):
        # 절대값 자체가 다르면 표기변경이 아니라 재표시 후보 — 값은 안 건드리고 신호만.
        frame = _frame(
            [
                {"year": 2024, "amount": 1666.0},
                {"year": 2025, "amount": -1905.0, "prior_amount": 1500.0},
            ]
        )
        out, changes = normalize_presentation(frame)
        assert dict(zip(out["year"], out["amount"]))[2024] == 1666.0
        assert dict(zip(out["year"], out["restated_later"]))[2024] is True
        assert changes[0]["kind"] == "restated_later"

    def test_one_won_tolerance_is_presentation_not_restatement(self):
        frame = _frame(
            [
                {"year": 2024, "amount": 1666.0},
                {"year": 2025, "amount": -1905.0, "prior_amount": -1665.0},
            ]
        )
        out, _ = normalize_presentation(frame)
        assert dict(zip(out["year"], out["amount"]))[2024] == -1666.0


class TestNoFalsePositives:
    def test_same_sign_untouched(self):
        frame = _frame(
            [
                {"year": 2024, "amount": 1666.0},
                {"year": 2025, "amount": 1905.0, "prior_amount": 1666.0},
            ]
        )
        out, changes = normalize_presentation(frame)
        assert not out["presentation_change"].any()
        assert not out["restated_later"].any()
        assert changes == []

    def test_missing_prior_and_zero_untouched(self):
        frame = _frame(
            [
                {"year": 2024, "amount": 0.0},
                {"year": 2025, "amount": 1905.0},
            ]
        )
        out, changes = normalize_presentation(frame)
        assert dict(zip(out["year"], out["amount"])) == {2024: 0.0, 2025: 1905.0}
        assert changes == []

    def test_duplicate_year_rows_skipped_conservatively(self):
        # 같은 계정-연도가 복수 행이면 어느 행의 전기값인지 확정 불가 — 정규화 생략.
        frame = _frame(
            [
                {"year": 2024, "amount": 1000.0},
                {"year": 2024, "amount": 666.0},
                {"year": 2025, "amount": -1905.0, "prior_amount": -1666.0},
            ]
        )
        out, changes = normalize_presentation(frame)
        assert sorted(out[out["year"] == 2024]["amount"]) == [666.0, 1000.0]
        assert changes == []

    def test_different_accounts_do_not_cross_match(self):
        # 다른 계정(canonical)끼리는 대조하지 않는다(2+ 케이스 검증).
        frame = pd.DataFrame(
            [
                {
                    "fs_div": "CFS",
                    "sj_div": "CF",
                    "canonical": "영업활동현금흐름",
                    "label": "영업활동현금흐름",
                    "year": 2024,
                    "amount": 1666.0,
                    "prior_amount": None,
                    "prior2_amount": None,
                },
                {
                    "fs_div": "CFS",
                    "sj_div": "CF",
                    "canonical": "투자활동현금유출",
                    "label": "투자활동으로부터의 현금유출",
                    "year": 2025,
                    "amount": -1905.0,
                    "prior_amount": -1666.0,
                    "prior2_amount": None,
                },
            ]
        )
        out, changes = normalize_presentation(frame)
        assert dict(zip(out["year"], out["amount"]))[2024] == 1666.0
        assert changes == []
