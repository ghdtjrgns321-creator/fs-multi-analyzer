"""설계2 — 금액 환산은 코드가 한다: format_krw·annotate_amounts.

LG생건 감사 결함②(LLM이 1조2,534.7억을 1,253.47억으로 오환산) 근본 해결:
LLM 입력 경계에서 코드가 환산 표기를 병기해 LLM이 나누기할 일 자체를 제거한다.
"""

from __future__ import annotations

from src.report.amounts import annotate_amounts, format_krw


class TestFormatKrw:
    def test_jo_unit_13_digits(self):
        # 결함② 실제 사례: 현금및현금성자산 1조 2,534.7억
        assert format_krw(1_253_469_878_367) == "1조 2,534.7억"

    def test_eok_unit_12_digits(self):
        # 투자활동 현금유출 1,665.6억
        assert format_krw(166_561_468_949) == "1,665.6억"

    def test_negative(self):
        assert format_krw(-190_475_674_544) == "-1,904.8억"

    def test_eok_unit_11_digits_round_integer(self):
        assert format_krw(38_700_000_000) == "387억"

    def test_small_eok(self):
        assert format_krw(843_000_000) == "8.4억"

    def test_exact_jo(self):
        assert format_krw(2_000_000_000_000) == "2조"


class TestAnnotateAmounts:
    def test_annotates_large_numbers_in_nested_dict(self):
        board = {"amounts": {2025: 1_253_469_878_367, 2024: -190_475_674_544}}
        out = annotate_amounts(board)
        assert out["amounts"][2025] == "1,253,469,878,367(1조 2,534.7억)"
        assert out["amounts"][2024] == "-190,475,674,544(-1,904.8억)"

    def test_leaves_small_values_and_ratios_untouched(self):
        board = {"yoy_pct": -62.8, "year": 2025, "zero": 0, "flag": True, "name": "매출"}
        out = annotate_amounts(board)
        assert out == board

    def test_annotates_inside_lists(self):
        rows = [{"delta": 42_810_000_000_000}]
        out = annotate_amounts(rows)
        assert out[0]["delta"] == "42,810,000,000,000(42조 8,100억)"

    def test_does_not_mutate_input(self):
        board = {"amounts": {2025: 1_000_000_000}}
        annotate_amounts(board)
        assert board["amounts"][2025] == 1_000_000_000
