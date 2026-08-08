"""긴 PART를 리더 투입 단위로 자르고, 청크 산물의 진짜 중복만 걷어낸다.

III(재무·주석)은 실측 최대 412,372 토큰(약 66만 자)이라 한 번에 못 던진다. 자를 때 정규식
subsection 분할을 쓰지 않는다 — 서식 35종마다 표제가 달라 그 길은 폐기된 이력이 있다(주석뷰어
파이프, c681b7d). 대신 글자 수로만 자르고 줄 경계에 스냅한다: 서식이 어떻게 생겼든 동작한다.

중복 제거는 최소로만 한다. III에서 이름이 겹치는 항목의 대부분은 중복이 아니라 연결/별도
두 축이고(삼성 2024 재고자산 연결 56.7조 vs 별도 32.3조, 인용 숫자 자카드 0%), 병합하면
별도재무제표 주석이 통째로 사라진다. 같은 축에서 인용 숫자가 사실상 동일한 쌍만 제거한다.
"""

from __future__ import annotations

import re

from src.notes.report_parts import ReportPart
from src.schemas.extract import ExtractedItem

CHUNK_CHARS = 60_000  # 청크당 약 32,000 토큰(실측) — 어떤 모델 컨텍스트에도 들어간다
OVERLAP_CHARS = 3_000  # 경계에서 잘린 항목 방어. 실측상 이것이 만든 가짜 중복은 없었다
_NUM = re.compile(r"\d{1,3}(?:,\d{3})+")  # 금액(콤마 표기)만 — 연도·비율은 동일성 근거가 못 된다


def _snap_to_line(text: str, pos: int) -> int:
    """pos 이후 첫 줄바꿈으로 스냅(표 행 중간 절단 완화). 없으면 원위치."""

    nl = text.find("\n", pos)
    return nl + 1 if nl != -1 else pos


def chunk_part(part: ReportPart, chunk_chars: int = CHUNK_CHARS) -> list[ReportPart]:
    """PART를 리더 투입 단위로 분할. 짧으면 원본 그대로 1개(정상 경로 무영향)."""

    text = part.text
    if len(text) <= chunk_chars:
        return [part]

    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = _snap_to_line(text, min(start + chunk_chars, len(text)))
        pieces.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - OVERLAP_CHARS, start + 1)

    total = len(pieces)
    return [
        ReportPart(numeral=part.numeral, title=f"{part.title} ({i}/{total})", text=body)
        for i, body in enumerate(pieces, 1)
    ]


def _amounts(item: ExtractedItem) -> frozenset[str]:
    return frozenset(_NUM.findall(f"{item.statement} {item.evidence}"))


def _same_fact(a: ExtractedItem, b: ExtractedItem, threshold: float) -> bool:
    """같은 축이고 인용 금액이 사실상 동일하면 같은 사실로 본다.

    금액을 안 낀 서술 항목(자카드 계산 불가)은 병합하지 않는다 — 연결·별도의 같은 문구가
    서로 다른 재무제표 사실인 경우를 지울 수 없다.
    """

    if a.fs_div != b.fs_div:
        return False
    x, y = _amounts(a), _amounts(b)
    if not x or not y:
        return False
    return len(x & y) / len(x | y) >= threshold


def dedupe_items(items: list[ExtractedItem], threshold: float = 0.9) -> list[ExtractedItem]:
    """청크 경계가 만든 진짜 중복만 제거(먼저 나온 항목을 남긴다).

    threshold를 낮추지 말 것: 0.5 수준이면 총괄 항목과 품목별 상세 항목이 병합되어 상세가
    사라진다(삼성 2024 재고자산 총괄 ↔ 품목별 자카드 50%).
    """

    kept: list[ExtractedItem] = []
    for item in items:
        if not any(_same_fact(item, k, threshold) for k in kept):
            kept.append(item)
    return kept
