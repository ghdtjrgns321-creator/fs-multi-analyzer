"""사업보고서 subsection의 "해당없음"(빈 섹션) 판정 — 완결성 앵커 정당제외용.

Plan A의 단일주제 라우팅(route_title·주제 YAML·route_report/장부)은 2-layer 전환으로 은퇴했다
(rich section을 뭉개는 문제, 설계 §3·§12). subsection 분할은 report_parts.split_subsections가,
파트→리더 배정은 reader_assign이 담당한다. 이 모듈에는 완결성(completeness)이 쓰는 빈 섹션 판정만 남는다.
"""

from __future__ import annotations

import re

# 본문이 사실상 비었다고 볼 "해당없음" 문구(공백제거·소문자 비교).
_EMPTY_PATTERNS = (
    "해당사항 없음",
    "해당사항이 없습니다",
    "해당 사항 없음",
    "해당사항없음",
    "해당없음",
)


def _norm(text: str) -> str:
    """공백 제거·소문자 — 부분문자열 비교용."""

    return re.sub(r"\s+", "", text).lower()


def is_empty_section(text: str) -> bool:
    """본문이 사실상 '해당없음'이면 True(정당제외 대상). 짧고 해당없음 문구면 빈 섹션."""

    stripped = text.strip()
    if not stripped:
        return True
    compact = _norm(stripped)
    return len(compact) < 40 and any(_norm(p) in compact for p in _EMPTY_PATTERNS)
