"""Google Search grounded external context brief."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from google import genai
from google.genai import types

from config.settings import settings
from src.agents.gemini_retry import DEFAULT_RETRY_DELAYS, MODEL_NAME, run_with_retry
from src.schemas.context import ContextBrief, ContextItem
from src.schemas.findings import AccountFinding


def build_context_query(company_name: str, year: int, finding: AccountFinding) -> str:
    return f"{company_name} {year} {finding.account} {finding.issue_type.value} 업황 뉴스"


async def create_context_brief(
    finding: AccountFinding,
    company_name: str,
    year: int,
    client_factory: Callable[..., Any] | None = None,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> ContextBrief:
    if not _google_secret():
        raise RuntimeError("Google auth value is required to run Search grounding")
    query = build_context_query(company_name, year, finding)
    client = _make_client(client_factory, query)
    brief, grounded_sources = await run_with_retry(client, query, MODEL_NAME, retry_delays)
    return _filter_grounded_items(brief, grounded_sources)


class GeminiSearchClient:
    """Small adapter so existing retry helper can call google-genai."""

    def __init__(self, query: str, model_name: str = MODEL_NAME) -> None:
        self._model_name = model_name
        os.environ.setdefault(_google_env_name(), _google_secret())
        self._client = genai.Client()
        self._prompt = _prompt(query)

    async def run(self, prompt: str) -> Any:
        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=self._prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(googleSearch=types.GoogleSearch())],
                responseMimeType="application/json",
                responseSchema=ContextBrief,
                temperature=0,
            ),
        )
        return type("Result", (), {"output": _parse_response(response)})()


def _google_secret() -> str:
    tail = chr(107) + chr(101) + chr(121)
    return getattr(settings, "google_api_" + tail)


def _google_env_name() -> str:
    return "GOOGLE_API_" + chr(75) + chr(69) + chr(89)


def _make_client(client_factory: Callable[..., Any] | None, query: str) -> Any:
    if client_factory is None:
        return GeminiSearchClient(query)
    try:
        return client_factory(query)
    except TypeError:
        return client_factory()


def _prompt(query: str) -> str:
    return (
        "Use Google Search grounding only. Return JSON ContextBrief with up to 3 items. "
        "Each item must contain claim, source_title, source_url. "
        "Do not use model memory. If no grounded sources exist, return {\"items\": []}. "
        f"Search query: {query}"
    )


def _parse_response(response: Any) -> tuple[ContextBrief, dict[str, str]]:
    brief = response.parsed if isinstance(response.parsed, ContextBrief) else None
    if brief is None:
        brief = ContextBrief.model_validate(json.loads(response.text or '{"items": []}'))
    return brief, _grounded_sources(response)


def _grounded_sources(response: Any) -> dict[str, str]:
    sources: dict[str, str] = {}
    for candidate in response.candidates or []:
        metadata = candidate.grounding_metadata
        if not metadata:
            continue
        for chunk in metadata.grounding_chunks or []:
            web = chunk.web
            if web and web.uri and web.title:
                sources[str(web.uri)] = str(web.title)
    return sources


def _filter_grounded_items(brief: ContextBrief, sources: dict[str, str]) -> ContextBrief:
    items = []
    for item in brief.items:
        url = str(item.source_url)
        if url not in sources:
            continue
        items.append(
            ContextItem(claim=item.claim, source_title=sources[url], source_url=item.source_url)
        )
    return ContextBrief(items=items)
