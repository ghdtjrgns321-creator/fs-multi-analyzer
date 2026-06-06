"""Independent L4 perspective assessments."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from config.settings import settings
from src.agents.model_retry import DEFAULT_RETRY_DELAYS, make_agent, run_with_retry
from src.schemas.findings import RiskLevel

PerspectiveName = Literal["numeric", "note", "flow", "change", "external", "industry"]

SYSTEM_PROMPT = """
You are one independent perspective agent for a disclosure review tool.
Use only the provided material_board. Do not read or infer another perspective result.
Do not use external facts, news, industry memory, or causal claims.
The review_queue is only a deterministic reference queue, not the answer.
Do not depend on the queue. Actively review the provided account level time series,
ratio time series, trend, note, flow, change, and benchmark materials.
If an unusual item is not in review_queue but is grounded in the provided material,
raise it as a review candidate.
For industry perspective, use only the provided peer-ratio baseline.
Return risks as review candidates and possibilities only. Do not conclude fraud.
Return Korean only.
"""
OPENAI_MODEL_NAME = settings.openai_model
LLM_TIMEOUT_SECONDS = settings.openai_timeout_seconds


class PerspectiveAssessment(BaseModel):
    perspective: PerspectiveName
    status: Literal["completed", "deferred"] = "completed"
    risk_areas: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    summary: str
    evidence: list[str] = Field(default_factory=list)


def build_perspective_agent(
    model_name: str = OPENAI_MODEL_NAME,
) -> Agent[None, PerspectiveAssessment]:
    """Create one OpenAI perspective agent for internal L4 judgment."""

    model = OpenAIModel(
        model_name,
        provider=OpenAIProvider(api_key=settings.openai_api_key),
    )
    model_settings = OpenAIModelSettings(timeout=settings.openai_timeout_seconds)
    if settings.openai_reasoning_effort:
        model_settings["openai_reasoning_effort"] = settings.openai_reasoning_effort
    return Agent(
        model,
        output_type=PerspectiveAssessment,
        system_prompt=SYSTEM_PROMPT,
        model_settings=model_settings,
        retries=2,
    )


async def create_perspective_assessment(
    perspective: PerspectiveName,
    material_board: dict[str, object],
    agent_factory: Callable[..., Any] = build_perspective_agent,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> PerspectiveAssessment:
    """Run one independent perspective over the shared material board."""

    if not settings.openai_api_key:
        return deferred_assessment(perspective, "OPENAI_API_KEY가 없어 보류했다.")
    prompt = json.dumps(
        {
            "perspective": perspective,
            "rules": [
                "다른 관점의 결론은 입력에 없다.",
                "외부 사실을 단정하지 않는다.",
                "industry 관점은 제공된 피어 지표 baseline만 사용한다.",
                "review_queue는 참고 후보일 뿐 정답이 아니다.",
                "제공된 계정 수준 시계열과 지표 시계열 전체를 능동적으로 검토한다.",
                "큐에 없더라도 제공 material에 근거한 수준 이상이나 추세 이상은 제기할 수 있다.",
                "실제 account_series, ratio_series, queue, ratio, note evidence에 근거한다.",
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
                make_agent(agent_factory, OPENAI_MODEL_NAME),
                prompt,
                OPENAI_MODEL_NAME,
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
