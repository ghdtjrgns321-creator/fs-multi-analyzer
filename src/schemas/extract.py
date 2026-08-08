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
    # 연결/별도 축. III(재무·주석)은 같은 주제가 연결·별도 두 번 실려 이름이 겹치므로, 축이 없으면
    # 서로 다른 사실이 중복으로 오인된다(삼성 2024 재고자산: 연결 56.7조 vs 별도 32.3조).
    # 판정 근거는 원문에 있다 — 주석 표제("연결재무제표 주석")와 본문 주어("연결회사는"/"회사는").
    # 서술 파트(I·II·IV~XI)는 구분이 없으므로 빈 문자열이 정상이다.
    fs_div: str = Field(default="", description="CFS(연결)/OFS(별도)/빈값(구분없음)")
    label: str = Field(min_length=1, description="항목명(짧게)")
    statement: str = Field(
        description="핵심 서술 — 원문 수치는 그대로 인용만, 계산·비율·증감률 산정 금지(옮겨적기+요약)"
    )
    evidence: str = Field(description="원문 근거 위치/인용")
    why_relevant: str = Field(description="감사 검토 관심 이유(정상설명 가능 전제)")


class ReaderOutput(BaseModel):
    """서술 리더 1회 실행의 출력 봉투(파트 하나에 대한 추출 항목 묶음)."""

    items: list[ExtractedItem] = Field(default_factory=list)
