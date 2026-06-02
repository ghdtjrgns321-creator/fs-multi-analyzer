"""LLM synthesis for the L4 integrated report."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config.settings import settings
from src.agents.gemini_retry import DEFAULT_RETRY_DELAYS, MODEL_NAME, make_agent, run_with_retry

SYSTEM_PROMPT = """
You write one Korean paragraph for a disclosure review report.
Use only the provided review_queue, ratio_summary, cross_check, and perspective_assessments.
Use external context only when it is in the external perspective evidence with source URLs.
Do not use model memory, unsourced news, industry memory, or causal claims.
External context is explanatory only and must not weaken internal review candidates.
Do not conclude fraud or accounting manipulation.
You may mention connections outside predefined chains only as possibilities grounded in data.
"""


def build_synthesis_agent(model_name: str = MODEL_NAME) -> Agent[None, str]:
    """Create the Gemini Flash synthesis agent."""

    model = GoogleModel(model_name, provider=GoogleProvider(api_key=settings.google_api_key))
    return Agent(model, output_type=str, system_prompt=SYSTEM_PROMPT, retries=2)


async def create_integrated_summary(
    payload: dict[str, object],
    agent_factory: Callable[..., Any] = build_synthesis_agent,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> str:
    """Run grounded one-paragraph company-level synthesis."""

    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is required to run the integrated summary")
    prompt = json.dumps(payload, ensure_ascii=False, indent=2)
    return await run_with_retry(
        make_agent(agent_factory, MODEL_NAME),
        prompt,
        MODEL_NAME,
        retry_delays,
    )
