"""S7 — 사업보고서 원문을 대단원(PART) 단위로 추출.

실측구조: 각 PART는 `<SECTION-1 APARTSOURCE="SOURCE">` 안의 `<TITLE>로마숫자. …</TITLE>`로
시작한다. 목차(표지 TD)에도 같은 문자열이 있으나 TITLE 태그가 아니므로 자연히 걸러진다.

설계: sub-section TITLE은 서식 버전(35종)마다 명칭이 달라 하드코딩 불가 → **로마숫자 PART
경계로만 슬라이스**한다(구11/신12 시대 무관). 논리섹션(감사의견·대주주거래 등) 선택은
시대 드리프트(대주주↔이해관계자)를 다중패턴으로 흡수한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

# 로마숫자(긴 것 우선 — XII가 X·II로 잘리지 않게). 헤더는 "<로마숫자>. " 형태.
_ROMAN = r"XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I"
_PART_TITLE = re.compile(
    rf"<TITLE\b[^>]*>\s*((?:{_ROMAN})\.\s*[^<]+?)\s*</TITLE>",
    re.IGNORECASE,
)
_NUMERAL = re.compile(rf"^({_ROMAN})\.")

# 최상위 subsection 헤더 = 줄 시작 "N. " + 한글/영문 제목(숫자만인 표 셀 제외).
_SUBSECTION_HEADER = re.compile(r"^(\d+)\.\s+([가-힣A-Za-z].*)$")

# 논리섹션 → PART 제목 다중패턴(시대 매핑). PART 레벨만(내용어=Step5 필터 소관).
LOGICAL_PARTS: dict[str, list[str]] = {
    "사업내용": ["사업의 내용"],
    "재무": ["재무에 관한 사항"],
    "경영진단": ["경영진단", "경영진의 검토"],
    "감사의견": ["감사의견"],
    "계열회사": ["계열회사"],
    "대주주거래": ["대주주 등과의 거래", "이해관계자와의 거래", "특수관계자와의 거래"],
    "투자자보호": ["투자자 보호"],
}


@dataclass(frozen=True)
class ReportPart:
    """사업보고서 대단원 한 개."""

    numeral: str
    title: str
    text: str


@dataclass(frozen=True)
class SubSection:
    """PART 하위 subsection 한 개(예: II.2 주요 제품)."""

    numeral: str
    index: int
    title: str
    text: str


def split_subsections(part: ReportPart) -> list[SubSection]:
    """PART 본문을 최상위 'N. 제목' 경계로 subsection 분할.

    헤더 없으면 전체를 index=0 단일 subsection으로(graceful). 표 셀의 순수 숫자는 헤더 아님.
    """

    lines = part.text.splitlines()
    marks: list[tuple[int, int, str]] = []  # (line_idx, sub_index, title)
    last = 0  # 단조증가: top-level 번호만 채택. 중첩 리스트(1.2.3.가 재시작)는 last 이하라 제외.
    for i, line in enumerate(lines):
        m = _SUBSECTION_HEADER.match(line.strip())
        if m:
            num = int(m.group(1))
            if num > last:  # 다음 top-level(증가)만 경계로. 중첩·재시작 번호는 무시.
                marks.append((i, num, m.group(2).strip()))
                last = num
    if not marks:
        return [SubSection(part.numeral, 0, part.title, part.text)]

    subs: list[SubSection] = []
    for k, (line_idx, sub_index, title) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        body = "\n".join(lines[line_idx + 1 : end]).strip()
        subs.append(SubSection(part.numeral, sub_index, title, body))
    return subs


def extract_parts(xml: str) -> list[ReportPart]:
    """사업보고서 XML을 로마숫자 PART 경계로 잘라 텍스트를 추출한다.

    PART 헤더(TITLE)가 하나도 없으면 빈 리스트로 graceful degrade한다.
    """

    headers = list(_PART_TITLE.finditer(xml))
    if not headers:
        return []

    parts: list[ReportPart] = []
    for index, match in enumerate(headers):
        title = _clean_title(match.group(1))
        numeral_match = _NUMERAL.match(title)
        if numeral_match is None:
            continue
        # 이 PART 본문 = 헤더 끝 ~ 다음 PART 헤더 시작(마지막은 문서 끝).
        body_start = match.end()
        body_end = headers[index + 1].start() if index + 1 < len(headers) else len(xml)
        text = _fragment_to_text(xml[body_start:body_end])
        parts.append(ReportPart(numeral=numeral_match.group(1), title=title, text=text))
    return parts


def select_part(parts: list[ReportPart], patterns: list[str]) -> ReportPart | None:
    """제목이 다중패턴 중 하나라도 포함하는 첫 PART를 반환(없으면 None)."""

    for part in parts:
        if any(pattern in part.title for pattern in patterns):
            return part
    return None


def _clean_title(raw: str) -> str:
    """TITLE 내부 잔여 태그·공백 정리."""

    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)).strip()


def _fragment_to_text(fragment: str) -> str:
    """PART 본문 조각(태그 포함)을 평문 텍스트로. 표는 셀이 행 텍스트로 펼쳐진다."""

    text = BeautifulSoup(fragment, "html.parser").get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
