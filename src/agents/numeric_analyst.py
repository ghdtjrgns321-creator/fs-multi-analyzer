"""PydanticAI numeric analyst agent for the first grounded Finding."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config.settings import settings
from src.agents.guardrails import validate_numeric_finding
from src.schemas.findings import AccountFinding

MODEL_NAME = "gemini-3.5-flash"

SYSTEM_PROMPT = """
You are the numeric analyst for a disclosure review tool.
Use only the provided deterministic signal payload as evidence.
Do not mention external facts, news, industry events, or specific market causes.
Normal explanations must be generic possibilities, not factual assertions.
Every numeric claim must be backed by numeric_evidence or flow_evidence.
Return one AccountFinding in Korean.
"""


def build_numeric_analyst_agent() -> Agent[None, AccountFinding]:
    """Create the Gemini Flash numeric analyst."""

    model = GoogleModel(MODEL_NAME, provider=GoogleProvider(api_key=settings.google_api_key))
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
    agent_factory: Callable[[], Any] = build_numeric_analyst_agent,
) -> AccountFinding:
    """Run the numeric analyst over deterministic signal payload."""

    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is required to run the numeric analyst")
    result = await agent_factory().run(json.dumps(payload, ensure_ascii=False, indent=2))
    return result.output
