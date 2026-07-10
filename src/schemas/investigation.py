"""조사원 산출 스키마 — 카드 최상단 '그래서 결론'(PLAN §5 조사 단계 2·3항).

조사원(도구 루프 또는 게이트 요약)이 채우고, 반박·외부검증이 이 결론을 입력으로 받는다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class InvestigationConclusion(BaseModel):
    headline: str = Field(description="핵심 결론 1~2문장 — 원인이 어디까지 좁혀졌는가")
    cause_path: list[str] = Field(
        default_factory=list, description="원인 경로(상위→하위 순 단계 서술, 수치 인용)"
    )
    anomaly_points: list[str] = Field(
        default_factory=list, description="이상 지점 — 데이터로 정상 설명이 안 되는 것"
    )
    open_questions: list[str] = Field(
        default_factory=list, description="남은 확인사항 — 내부 데이터로 못 좁힌 것"
    )
    resolved: bool = Field(description="원인 규명이 내부 데이터에서 완결됐는지")
    # 아래 둘은 LLM이 아니라 코드가 세팅한다(경로·비용 관찰용).
    method: Literal["gate_summary", "tool_loop"] = "tool_loop"
    tool_requests: int = 0


__all__ = ["InvestigationConclusion"]
