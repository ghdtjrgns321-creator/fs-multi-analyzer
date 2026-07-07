"""Layer 1 서술 리더 추출물 스키마 (DECOMPOSITION_DESIGN §5).

목차 macro-block별 서술 리더(LLM)가 사업보고서 파트 본문에서 "감사인이 검토할 항목"만
뽑아 구조화한다. 재무 결정론 리더(Phase1)와 달리 계산을 하지 않는다 — 원문 수치는 그대로
인용만 하고, 흐름·비율·증감률 산정은 Layer 2(분석 관점)와 기존 결정론 코드가 담당한다.
프로토타입 scratchpad/reader_proto.py에서 삼성 2사 실측(₩288/최악)으로 검증한 스키마를 승격.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedItem(BaseModel):
    """서술 리더가 뽑은 감사 검토 관심 항목 1개(계산 없는 구조화 인용).

    숫자·서술이 섞인 파트라도 출력 구조는 동일하다 — 리더는 원문 수치를 statement에 옮겨적기만
    하고 계산하지 않는다(계산=코드/발견=LLM 원칙). 부정을 확정하지 않고 검토 후보만 제시한다.
    """

    part: str = Field(description="출처 PART 로마숫자(예: XI)")
    label: str = Field(min_length=1, description="항목명(짧게)")
    statement: str = Field(
        description="핵심 서술 — 원문 수치는 그대로 인용만, 계산·비율·증감률 산정 금지(옮겨적기+요약)"
    )
    evidence: str = Field(description="원문 근거 위치/인용")
    why_relevant: str = Field(description="감사 검토 관심 이유(정상설명 가능 전제)")


class ReaderOutput(BaseModel):
    """서술 리더 1회 실행의 출력 봉투(파트 하나에 대한 추출 항목 묶음)."""

    items: list[ExtractedItem] = Field(default_factory=list)
