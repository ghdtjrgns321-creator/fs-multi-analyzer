"""Task B2 — 파트→블록 focus 배정 전수 대조."""

import pytest
from src.report.reader_assign import load_focus_map, reader_focus

# 설계 §4 전수 배정표: 서술 10파트 focus, III(재무결정론)·XII(제외) None.
_EXPECTED_HAS_FOCUS = ["I", "II", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
_EXPECTED_NONE = ["III", "XII"]


@pytest.mark.parametrize("numeral", _EXPECTED_HAS_FOCUS)
def test_narrative_parts_have_focus(numeral):
    focus = reader_focus(numeral)
    assert focus is not None and focus.strip(), f"{numeral} focus 비어있음"


@pytest.mark.parametrize("numeral", _EXPECTED_NONE)
def test_financial_and_excluded_parts_return_none(numeral):
    assert reader_focus(numeral) is None, f"{numeral}은 서술 리더 미배정이어야 함"


def test_focus_map_covers_all_parts_once():
    fmap = load_focus_map()
    # 배정된 파트는 서술 10개 정확히(중복·누락 0)
    assert sorted(fmap.keys()) == sorted(_EXPECTED_HAS_FOCUS)
    # 한글 focus 로드 정상(allow_unicode)
    assert "특수관계" in fmap["VIII"]
