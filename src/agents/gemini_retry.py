"""Shared Gemini agent retry policy."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import Any

from pydantic_ai.exceptions import ModelHTTPError

from config.settings import settings

MODEL_NAME = "gemini-3.5-flash"
DEFAULT_RETRY_DELAYS = (2.0, 4.0, 8.0, 16.0)


def is_temporary_gemini_error(exc: Exception) -> bool:
    if isinstance(exc, ModelHTTPError):
        if 400 <= exc.status_code < 500:
            return False
        if exc.status_code >= 500:
            return True
    text = repr(exc).upper()
    return "UNAVAILABLE" in text or "503" in text or "HIGH DEMAND" in text


def fallback_model() -> str | None:
    fallback = settings.gemini_fallback_model.strip()
    if not fallback:
        return None
    if not fallback.startswith("gemini-"):
        raise RuntimeError("Gemini fallback model must stay within the Gemini family")
    if fallback == MODEL_NAME:
        return None
    return fallback


def make_agent(agent_factory: Callable[..., Any], model_name: str) -> Any:
    try:
        return agent_factory(model_name)
    except TypeError:
        return agent_factory()


async def run_with_retry(
    agent: Any,
    prompt: str,
    model_name: str,
    retry_delays: tuple[float, ...],
) -> Any:
    attempts = len(retry_delays) + 1
    last_error: Exception | None = None
    for index in range(attempts):
        try:
            return (await agent.run(prompt)).output
        except Exception as exc:
            if not is_temporary_gemini_error(exc):
                raise
            last_error = exc
            if index == attempts - 1:
                break
            delay = retry_delays[index]
            await asyncio.sleep(delay + random.uniform(0, min(1.0, delay * 0.25)))
    raise RuntimeError(
        f"Gemini temporary error after {attempts} attempts for {model_name}: {last_error}"
    ) from last_error
