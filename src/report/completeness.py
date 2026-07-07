"""완결성(리더 누락 방지) 3중 결정론 앵커 — 설계 §7.

2차 LLM·신호어 목록 없이(자의성 회피) 구조·금액만으로 "리더가 빠뜨렸을 만한 곳"을 경고한다.
1. **섹션 커버리지**: 실질내용 있는 서술 파트가 추출물 0개 → 경고(part 단위).
2. **가/나/다 커버리지**: 가나다 항목을 담은 subsection이 있는데 그 파트 추출 0개 → subsection 단위 경고.
3. **물질 금액 커버리지(핵심, grounding 역방향)**: 원문의 material 금액(materiality 임계↑)이 어떤 추출물의
   statement/evidence에도 없으면 "그 금액 항목 누락 의심" 경고. grounding(§9)과 금액 유틸 공유(양방향).

한계(정직): 추출물은 part 단위 태깅뿐이라 1·2는 파트가 통째 비었을 때만 확실히 잡는다. 금액 없고 구조항목도
아닌 순수 서술의 미세누락은 결정론으로 못 잡는다(의미 판단 필요) — 도구는 후보 제시이지 전수 보장이 아니다.
"""

from __future__ import annotations

import re

from src.notes.report_parts import ReportPart, split_subsections
from src.report.grounding import _AMOUNT_TOKEN, _sig
from src.report.reader_assign import reader_focus
from src.report.section_router import is_empty_section

# 서술 항목 라벨 "가. 나. 다. …" 줄 시작(표 셀·조사 오인 방지: 라벨 뒤 마침표+공백).
_GANADA = re.compile(r"^\s*([가-힣])\.\s+\S")
_GANADA_SET = set("가나다라마바사아자차카타파하")

# 금액 단위 배수(유효숫자 무관하게 물질성 임계 비교용 크기 추정).
_UNITS = (("조", 1e12), ("억", 1e8), ("백만", 1e6))

# 원문 금액 토큰 — 단위(조/억/백만)를 반드시 함께 잡는다(grounding _AMOUNT_TOKEN은 쉼표그룹을
# 먼저 끊어 '1,012억'의 단위를 놓쳐 크기를 오판하므로, 물질성 크기 판정용은 단위우선 정규식을 쓴다).
_SOURCE_AMOUNT = re.compile(r"\d{1,3}(?:,\d{3})*\s*(?:조|억|백만)원?|\d{1,3}(?:,\d{3})+|\d{6,}")


def _token_magnitude(token: str) -> float:
    """금액 토큰의 대략적 절대 크기(원). '100억'→1e10, '12,345'→12345. materiality 비교용."""

    unit = 1.0
    for name, mult in _UNITS:
        if name in token:
            unit = mult
            break
    digits = re.sub(r"[^\d]", "", token)
    if not digits:
        return 0.0
    return float(digits) * unit


def _material_source_sigs(text: str, materiality: float) -> dict[str, str]:
    """원문에서 material(≥materiality) 금액 토큰의 유효숫자→원문토큰 맵."""

    found: dict[str, str] = {}
    for token in _SOURCE_AMOUNT.findall(text or ""):
        if _token_magnitude(token) < materiality:
            continue
        sig = _sig(token)
        if len(sig) >= 3:
            found.setdefault(sig, token)
    return found


def _extract_sigs(items) -> set[str]:
    """추출물 statement+evidence의 금액 유효숫자 집합(역grounding 대조용)."""

    sigs: set[str] = set()
    for it in items:
        for token in _AMOUNT_TOKEN.findall(f"{it.statement} {it.evidence}"):
            sig = _sig(token)
            if len(sig) >= 3:
                sigs.add(sig)
    return sigs


def completeness_warnings(
    parts: list[ReportPart],
    items,
    materiality: float,
) -> list[dict]:
    """서술 리더 추출물의 누락 의심 지점을 3중 결정론 앵커로 경고. list[dict]."""

    warnings: list[dict] = []
    covered_parts = {it.part for it in items}
    extract_sigs = _extract_sigs(items)

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

        # 앵커 3 — 물질 금액 커버리지(역grounding, 파트 커버 여부 무관)
        for sig, token in _material_source_sigs(part.text, materiality).items():
            if sig not in extract_sigs:
                warnings.append(
                    {
                        "anchor": "material_amount",
                        "part": part.numeral,
                        "detail": token,
                        "reason": f"원문 material 금액 '{token}'이 추출물 어디에도 없음 — 금액 항목 누락 의심",
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
