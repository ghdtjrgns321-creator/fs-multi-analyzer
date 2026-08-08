"""Task B2 — 파트→블록 focus 배정 전수 대조."""

import pytest

from src.report.reader_assign import load_focus_map, reader_focus

# 설계 §4 전수 배정표: 서술 11파트 focus, XII(구조화 API 중복)만 None.
# III은 2026-08 편입 — 결정론(Phase1)이 담당하는 건 재무 수치지 주석 서술이 아니다.
_EXPECTED_HAS_FOCUS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
_EXPECTED_NONE = ["XII"]


@pytest.mark.parametrize("numeral", _EXPECTED_HAS_FOCUS)
def test_narrative_parts_have_focus(numeral):
    focus = reader_focus(numeral)
    assert focus is not None and focus.strip(), f"{numeral} focus 비어있음"


@pytest.mark.parametrize("numeral", _EXPECTED_NONE)
def test_excluded_parts_return_none(numeral):
    assert reader_focus(numeral) is None, f"{numeral}은 서술 리더 미배정이어야 함"


def test_focus_map_covers_all_parts_once():
    fmap = load_focus_map()
    # 배정된 파트는 서술 11개 정확히(중복·누락 0)
    assert sorted(fmap.keys()) == sorted(_EXPECTED_HAS_FOCUS)
    # 한글 focus 로드 정상(allow_unicode)
    assert "특수관계" in fmap["VIII"]


def test_notes_focus_names_the_three_high_value_topics():
    # III focus는 XBRL이 못 담는 3항목을 명시해야 한다(실측 근거: 재무특약·소송·콜옵션 의결).
    focus = reader_focus("III")
    assert focus is not None
    for topic in ("특수관계자", "우발부채", "재무특약"):
        assert topic in focus, f"III focus에 {topic} 누락"
