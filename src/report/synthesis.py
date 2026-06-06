"""LLM synthesis for the L4 integrated report."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from config.settings import settings
from src.agents.model_retry import DEFAULT_RETRY_DELAYS, make_agent, run_with_retry

SYSTEM_PROMPT = """
You write one Korean paragraph for a disclosure review report.
Use only the provided review_queue, ratio_summary, cross_check, and perspective_assessments.
The review_queue is a reference queue, not the answer.
Use external context only when it is in the external perspective evidence with source URLs.
Do not use model memory, unsourced news, industry memory, or causal claims.
External context is explanatory only and must not weaken internal review candidates.
Do not conclude fraud or accounting manipulation.
You may mention connections outside predefined chains only as possibilities grounded in data.
"""
OPENAI_MODEL_NAME = settings.openai_model


def build_synthesis_agent(model_name: str = OPENAI_MODEL_NAME) -> Agent[None, str]:
    """Create the OpenAI synthesis agent."""

    model = OpenAIModel(model_name, provider=OpenAIProvider(api_key=settings.openai_api_key))
    model_settings = OpenAIModelSettings(timeout=settings.openai_timeout_seconds)
    if settings.openai_reasoning_effort:
        model_settings["openai_reasoning_effort"] = settings.openai_reasoning_effort
    return Agent(
        model,
        output_type=str,
        system_prompt=SYSTEM_PROMPT,
        model_settings=model_settings,
        retries=2,
    )


async def create_integrated_summary(
    payload: dict[str, object],
    agent_factory: Callable[..., Any] = build_synthesis_agent,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> str:
    """Run grounded one-paragraph company-level synthesis."""

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to run the integrated summary")
    prompt = json.dumps(payload, ensure_ascii=False, indent=2)
    return await run_with_retry(
        make_agent(agent_factory, OPENAI_MODEL_NAME),
        prompt,
        OPENAI_MODEL_NAME,
        retry_delays,
    )
