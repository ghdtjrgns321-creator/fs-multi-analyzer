"""완결성(리더 누락 방지) 구조 결정론 앵커 — 설계 §7.

2차 LLM·신호어 목록 없이(자의성 회피) 구조만으로 "리더가 파트/항목을 통째로 건너뛰었나"를 경고한다.
1. **섹션 커버리지**: 실질내용 있는 서술 파트가 추출물 0개 → 경고(part 단위).
2. **가/나/다 커버리지**: 가나다 항목을 담은 subsection이 있는데 그 파트 추출 0개 → subsection 단위 경고.

앵커 3(물질 금액 역grounding)은 폐기했다: 실측(대주·삼성 2사)에서 실제 리더 누락 catch 0·헛경고 198건
(조문번호 '133조'를 133조원으로 오인, 표 셀 원단위 금액 범람). 리더가 표 헤더단위까지 인용하도록 고쳐
(reader.py) 금액 소실이 사라졌고, 원문 금액의 material 판정은 표 헤더-셀 분리 때문에 정규식으로 신뢰 불가.
→ 금액 누락 감지는 리더 품질로 커버하고, 완결성은 구조(파트/가나다 통째 스킵)만 결정론으로 잡는다.

한계(정직): 추출물은 part 단위 태깅뿐이라 1·2는 파트가 통째 비었을 때만 확실히 잡는다. 파트 안에서 특정
금액·서술을 놓친 미세누락은 결정론으로 못 잡는다(의미 판단 필요) — 도구는 후보 제시이지 전수 보장이 아니다.
"""

from __future__ import annotations

import re

from src.notes.report_parts import ReportPart, split_subsections
from src.report.reader_assign import reader_focus
from src.report.section_router import is_empty_section

# 서술 항목 라벨 "가. 나. 다. …" 줄 시작(표 셀·조사 오인 방지: 라벨 뒤 마침표+공백).
_GANADA = re.compile(r"^\s*([가-힣])\.\s+\S")
_GANADA_SET = set("가나다라마바사아자차카타파하")


def completeness_warnings(parts: list[ReportPart], items) -> list[dict]:
    """서술 리더 추출물의 누락 의심 지점을 구조 결정론 앵커로 경고. list[dict]."""

    warnings: list[dict] = []
    covered_parts = {it.part for it in items}

    for part in parts:
        if reader_focus(part.numeral) is None:  # III(재무결정론)·XII(제외)는 대상 아님
            continue
        subs = split_subsections(part)
        substantive = [s for s in subs if not is_empty_section(s.text)]

        # 앵커 1 — 섹션 커버리지(파트 통째 0추출)
        if substantive and part.numeral not in covered_parts:
            warnings.append(
                {
                    "anchor": "section_coverage",
                    "part": part.numeral,
                    "detail": [s.title for s in substantive],
                    "reason": f"PART {part.numeral} 실질 subsection {len(substantive)}개인데 추출물 0개 — 파트 누락 의심",
                }
            )

        # 앵커 2 — 가/나/다 커버리지(0추출 파트의 가나다 구조 subsection)
        if part.numeral not in covered_parts:
            for sub in substantive:
                labels = _ganada_labels(sub.text)
                if labels:
                    warnings.append(
                        {
                            "anchor": "subsection_ganada",
                            "part": part.numeral,
                            "detail": f"{sub.title}: 가나다 항목 {labels}",
                            "reason": f"{sub.title}의 항목({''.join(labels)})이 하나도 추출되지 않음 — 항목 누락 의심",
                        }
                    )
    return warnings


def _ganada_labels(text: str) -> list[str]:
    """subsection 본문에서 줄 시작 '가. 나. …' 라벨 순서대로(중복 제거)."""

    labels: list[str] = []
    for line in text.splitlines():
        m = _GANADA.match(line)
        if m and m.group(1) in _GANADA_SET and m.group(1) not in labels:
            labels.append(m.group(1))
    return labels
