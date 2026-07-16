"""External context brief schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContextItem(BaseModel):
    """One sourced external context item."""

    claim: str = Field(min_length=1)
    source_title: str = ""
    source_url: str = ""
    # claim에 인용된 금액 문자열(원문 그대로, 예: "1,478억") — 코드가 내부 공시값과
    # 대조하기 위한 구조화 출력(설계4a: 요약문 정규식 파싱 대신 structured output).
    figures: list[str] = Field(default_factory=list)


class ContextBrief(BaseModel):
    """Reference-only external context, kept separate from Finding judgment."""

    items: list[ContextItem] = Field(default_factory=list)
