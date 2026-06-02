"""PydanticAI numeric analyst agent for the first grounded Finding."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config.settings import settings
from src.agents.gemini_retry import (
    DEFAULT_RETRY_DELAYS,
    MODEL_NAME,
    fallback_model,
    make_agent,
    run_with_retry,
)
from src.agents.guardrails import validate_numeric_finding
from src.schemas.findings import AccountFinding

SYSTEM_PROMPT = """
You are the numeric analyst for a disclosure review tool.
Use only the provided deterministic signal payload as evidence.
Do not mention external facts, news, industry events, or specific market causes.
Normal explanations must be generic possibilities, not factual assertions.
Every numeric claim must be backed by numeric_evidence or flow_evidence.
Return one AccountFinding in Korean.
"""


def build_numeric_analyst_agent(model_name: str = MODEL_NAME) -> Agent[None, AccountFinding]:
    """Create the Gemini Flash numeric analyst."""

    model = GoogleModel(model_name, provider=GoogleProvider(api_key=settings.google_api_key))
    agent = Agent(
        model,
        output_type=AccountFinding,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
    )

    @agent.output_validator
    def _validate(output: AccountFinding) -> AccountFinding:
        return validate_numeric_finding(output)

    return agent


async def create_numeric_finding(
    payload: dict[str, object],
    agent_factory: Callable[..., Any] = build_numeric_analyst_agent,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> AccountFinding:
    """Run the numeric analyst over deterministic signal payload."""

    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is required to run the numeric analyst")
    prompt = json.dumps(payload, ensure_ascii=False, indent=2)

    try:
        return await run_with_retry(
            make_agent(agent_factory, MODEL_NAME), prompt, MODEL_NAME, retry_delays
        )
    except RuntimeError:
        fallback = fallback_model()
        if not fallback:
            raise
        return await run_with_retry(
            make_agent(agent_factory, fallback), prompt, fallback, retry_delays
        )
