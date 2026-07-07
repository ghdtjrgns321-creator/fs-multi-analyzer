"""해체 엔진 생존물 — subsection 분할(report_parts) + 빈 섹션 판정(section_router).

Plan A의 단일주제 라우팅(route_title·route_report·주제 YAML)은 2-layer 전환으로 은퇴했다.
남은 것: split_subsections(파트 분할), is_empty_section(완결성 앵커 정당제외용). 전부 결정론(LLM 0).
"""

from __future__ import annotations

from src.notes.report_parts import ReportPart, split_subsections
from src.report.section_router import is_empty_section


def test_split_subsections_by_numbered_heading():
    part = ReportPart(
        numeral="I",
        title="I. 회사의 개요",
        text="1. 회사의 개요\n가나다 본문\n2. 회사의 연혁\n라마바 본문\n3. 자본금 변동사항\n사아자",
    )
    subs = split_subsections(part)
    assert [s.index for s in subs] == [1, 2, 3]
    assert subs[0].title == "회사의 개요"
    assert "가나다" in subs[0].text
    assert subs[1].title == "회사의 연혁"
    assert subs[2].numeral == "I"


def test_split_subsections_ignores_table_number_cells():
    part = ReportPart(numeral="X", title="X", text="1. 진짜 제목\n1\n2,000,000\n내용")
    subs = split_subsections(part)
    assert len(subs) == 1
    assert subs[0].title == "진짜 제목"


def test_split_subsections_no_header_single_block():
    part = ReportPart(numeral="Z", title="Z. 제목없음", text="헤더 없는 본문만")
    subs = split_subsections(part)
    assert len(subs) == 1
    assert subs[0].index == 0


def test_is_empty_section_detects_해당없음():
    assert is_empty_section("- 해당사항 없음") is True
    assert is_empty_section("해당사항이 없습니다.") is True
    assert is_empty_section("소송가액 100억원 계류 중") is False
