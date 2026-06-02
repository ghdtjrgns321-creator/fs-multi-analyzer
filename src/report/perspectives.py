"""Independent L4 perspective assessments."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config.settings import settings
from src.agents.gemini_retry import DEFAULT_RETRY_DELAYS, MODEL_NAME, make_agent, run_with_retry
from src.schemas.findings import RiskLevel

PerspectiveName = Literal["numeric", "note", "flow", "change"]

SYSTEM_PROMPT = """
You are one independent perspective agent for a disclosure review tool.
Use only the provided material_board. Do not read or infer another perspective result.
Do not use external facts, news, industry memory, or causal claims.
Return risks as review candidates and possibilities only. Do not conclude fraud.
Return Korean only.
"""
LLM_TIMEOUT_SECONDS = 45.0


class PerspectiveAssessment(BaseModel):
    perspective: PerspectiveName
    status: Literal["completed", "deferred"] = "completed"
    risk_areas: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    summary: str
    evidence: list[str] = Field(default_factory=list)


def build_perspective_agent(model_name: str = MODEL_NAME) -> Agent[None, PerspectiveAssessment]:
    """Create one Gemini Flash perspective agent."""

    model = GoogleModel(model_name, provider=GoogleProvider(api_key=settings.google_api_key))
    return Agent(model, output_type=PerspectiveAssessment, system_prompt=SYSTEM_PROMPT, retries=2)


async def create_perspective_assessment(
    perspective: PerspectiveName,
    material_board: dict[str, object],
    agent_factory: Callable[..., Any] = build_perspective_agent,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> PerspectiveAssessment:
    """Run one independent perspective over the shared material board."""

    if not settings.google_api_key:
        return deferred_assessment(perspective, "GOOGLE_API_KEY가 없어 보류했다.")
    prompt = json.dumps(
        {
            "perspective": perspective,
            "rules": [
                "다른 관점의 결론은 입력에 없다.",
                "외부 사실을 단정하지 않는다.",
                "실제 queue, ratio, note evidence에 근거한다.",
                "주석 발췌는 일부일 수 있으므로 발췌 누락을 공시 누락으로 판단하지 않는다.",
                "출력은 한국어로 작성한다.",
            ],
            "material_board": material_board,
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        return await asyncio.wait_for(
            run_with_retry(
                make_agent(agent_factory, MODEL_NAME),
                prompt,
                MODEL_NAME,
                retry_delays,
            ),
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        reason = str(exc) or exc.__class__.__name__
        return deferred_assessment(perspective, reason)


def deferred_assessment(perspective: PerspectiveName, reason: str) -> PerspectiveAssessment:
    return PerspectiveAssessment(
        perspective=perspective,
        status="deferred",
        risk_areas=[],
        risk_level="Low",
        summary=reason,
        evidence=[],
    )
