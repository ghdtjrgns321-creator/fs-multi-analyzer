"""S7 Step2 — 사업보고서 PART 추출기 테스트.

TITLE 로마숫자 헤더로 PART 슬라이스(목차 TD 무시)·표→행 텍스트·시대무관 논리섹션 선택.
"""

from src.notes.report_parts import extract_parts, select_part

# 신시대(2018+): 목차 TD 노이즈 + 본문 SECTION-1 3파트(I·X·XII).
_NEW_ERA_XML = """<DOCUMENT>
<SECTION-1>
<TITLE>표지</TITLE>
<TABLE><TBODY>
<TR><TD>I. 회사의 개요</TD><TD>2</TD></TR>
<TR><TD>X. 대주주 등과의 거래내용</TD><TD>50</TD></TR>
</TBODY></TABLE>
</SECTION-1>
<SECTION-1 ACLASS="MANDATORY" APARTSOURCE="SOURCE">
<TITLE ATOC="Y" ATOCID="3">I. 회사의 개요</TITLE>
<P>당사는 전자제품을 제조한다.</P>
</SECTION-1>
<SECTION-1 ACLASS="MANDATORY" APARTSOURCE="SOURCE">
<TITLE ATOC="Y" ATOCID="40">X. 대주주 등과의 거래내용</TITLE>
<P>대주주에게 자금을 대여하였다.</P>
<TABLE><TBODY>
<TR><TD>항목</TD><TD>금액</TD></TR>
<TR><TD>대여금</TD><TD>100</TD></TR>
</TBODY></TABLE>
</SECTION-1>
<SECTION-1 ACLASS="MANDATORY" APARTSOURCE="SOURCE">
<TITLE ATOC="Y" ATOCID="60">XII. 상세표</TITLE>
<P>상세표 내용</P>
</SECTION-1>
</DOCUMENT>"""

# 구시대(~2017): X이 "이해관계자와의 거래"로 명칭 다름, XII 없음.
_OLD_ERA_XML = """<DOCUMENT>
<SECTION-1 APARTSOURCE="SOURCE">
<TITLE>I. 회사의 개요</TITLE>
<P>구 양식 회사 개요.</P>
</SECTION-1>
<SECTION-1 APARTSOURCE="SOURCE">
<TITLE>X. 이해관계자와의 거래</TITLE>
<P>특수관계자와 거래가 있다.</P>
</SECTION-1>
</DOCUMENT>"""


def test_extract_parts_new_era_finds_three_parts_ignoring_toc() -> None:
    parts = extract_parts(_NEW_ERA_XML)

    # 목차 TD(2개)는 TITLE이 아니므로 무시 → 본문 3파트만.
    assert [p.numeral for p in parts] == ["I", "X", "XII"]
    assert parts[0].title == "I. 회사의 개요"


def test_extract_parts_captures_body_text_stripping_tags() -> None:
    parts = extract_parts(_NEW_ERA_XML)

    assert "전자제품을 제조" in parts[0].text
    # 다음 PART 본문이 섞이지 않는다(슬라이스 경계).
    assert "대주주" not in parts[0].text


def test_extract_parts_table_becomes_row_text() -> None:
    parts = extract_parts(_NEW_ERA_XML)
    x_part = next(p for p in parts if p.numeral == "X")

    assert "대주주에게 자금" in x_part.text
    assert "대여금" in x_part.text
    assert "100" in x_part.text


def test_extract_parts_old_era_different_title_still_extracted() -> None:
    parts = extract_parts(_OLD_ERA_XML)

    # 시대무관: 제목 하드코딩 없이 로마숫자로 슬라이스.
    assert [p.numeral for p in parts] == ["I", "X"]
    assert parts[1].title == "X. 이해관계자와의 거래"


def test_select_part_is_era_robust_for_relationship_dealings() -> None:
    # 동일 다중패턴이 신(대주주)·구(이해관계자) 두 시대 모두 PART X을 찾는다.
    patterns = ["대주주 등과의 거래", "이해관계자와의 거래"]

    new_hit = select_part(extract_parts(_NEW_ERA_XML), patterns)
    old_hit = select_part(extract_parts(_OLD_ERA_XML), patterns)

    assert new_hit is not None and new_hit.numeral == "X"
    assert old_hit is not None and old_hit.numeral == "X"


def test_select_part_returns_none_when_no_pattern_matches() -> None:
    assert select_part(extract_parts(_NEW_ERA_XML), ["존재하지않는섹션"]) is None


def test_extract_parts_graceful_when_no_part_title() -> None:
    assert extract_parts("<DOCUMENT><P>대단원 헤더 없음</P></DOCUMENT>") == []
