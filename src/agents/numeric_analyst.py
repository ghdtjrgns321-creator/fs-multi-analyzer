"""PydanticAI numeric analyst agent for the first grounded Finding."""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config.settings import settings
from src.agents.guardrails import validate_numeric_finding
from src.schemas.findings import AccountFinding

MODEL_NAME = "gemini-3.5-flash"
DEFAULT_RETRY_DELAYS = (2.0, 4.0, 8.0, 16.0)

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


def _is_temporary_gemini_error(exc: Exception) -> bool:
    if isinstance(exc, ModelHTTPError):
        if 400 <= exc.status_code < 500:
            return False
        if exc.status_code >= 500:
            return True

    text = repr(exc).upper()
    return "UNAVAILABLE" in text or "503" in text or "HIGH DEMAND" in text


def _fallback_model() -> str | None:
    fallback = settings.gemini_fallback_model.strip()
    if not fallback:
        return None
    if not fallback.startswith("gemini-"):
        raise RuntimeError("Gemini fallback model must stay within the Gemini family")
    if fallback == MODEL_NAME:
        return None
    return fallback


def _make_agent(agent_factory: Callable[..., Any], model_name: str) -> Any:
    try:
        return agent_factory(model_name)
    except TypeError:
        return agent_factory()


async def _run_with_retry(
    agent: Any,
    prompt: str,
    model_name: str,
    retry_delays: tuple[float, ...],
) -> AccountFinding:
    attempts = len(retry_delays) + 1
    last_error: Exception | None = None

    for index in range(attempts):
        try:
            result = await agent.run(prompt)
            return result.output
        except Exception as exc:
            if not _is_temporary_gemini_error(exc):
                raise
            last_error = exc
            if index == attempts - 1:
                break
            delay = retry_delays[index]
            await asyncio.sleep(delay + random.uniform(0, min(1.0, delay * 0.25)))

    raise RuntimeError(
        f"Gemini temporary error after {attempts} attempts for {model_name}: {last_error}"
    ) from last_error


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
        return await _run_with_retry(
            _make_agent(agent_factory, MODEL_NAME), prompt, MODEL_NAME, retry_delays
        )
    except RuntimeError:
        fallback = _fallback_model()
        if not fallback:
            raise
        return await _run_with_retry(
            _make_agent(agent_factory, fallback), prompt, fallback, retry_delays
        )
