"""Provider-neutral retry for L4 analysis models."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import Any

from pydantic_ai.exceptions import ModelHTTPError

DEFAULT_RETRY_DELAYS = (2.0, 4.0, 8.0, 16.0)


def make_agent(agent_factory: Callable[..., Any], model_name: str) -> Any:
    try:
        return agent_factory(model_name)
    except TypeError:
        return agent_factory()


def is_temporary_model_error(exc: Exception) -> bool:
    if isinstance(exc, ModelHTTPError):
        if exc.status_code == 429 or exc.status_code >= 500:
            return True
        if 400 <= exc.status_code < 500:
            return False
    text = repr(exc).upper()
    temporary = ("TIMEOUT", "TEMPORARY", "UNAVAILABLE", "RATE_LIMIT", "429", "503")
    return any(token in text for token in temporary)


async def run_with_retry(
    agent: Any,
    prompt: str,
    model_name: str,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> Any:
    attempts = len(retry_delays) + 1
    last_error: Exception | None = None
    for index in range(attempts):
        try:
            return (await agent.run(prompt)).output
        except Exception as exc:
            if not is_temporary_model_error(exc):
                raise
            last_error = exc
            if index == attempts - 1:
                break
            delay = retry_delays[index]
            await asyncio.sleep(delay + random.uniform(0, min(1.0, delay * 0.25)))
    raise RuntimeError(
        f"Temporary model error after {attempts} attempts for {model_name}: {last_error}"
    ) from last_error
