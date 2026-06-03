"""Agentic query generation and evaluation for the external L4 perspective."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config.settings import settings
from src.agents.gemini_retry import DEFAULT_RETRY_DELAYS, make_agent, run_with_retry
from src.report.perspectives import PerspectiveAssessment
from src.schemas.context import ContextBrief


class SearchKeywords(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=3)


EXTERNAL_MODEL_NAME = settings.gemini_external_model

QUERY_PROMPT = """
You generate Korean Google Search queries for disclosure review context.
Use only the supplied company_name, business_domain, target_year, review_queue, ratio_summary,
and signals.
Return 1 to 3 concise search queries. Each query must include company_name and target_year.
Use internal facts only.
Search for possible cause events behind the internal anomalies.
Do not copy metric acronyms such as DIO, DSO, ROE, ROA, ROI, or CFO into queries.
Do not use speculative words like fraud, manipulation, scandal, or misconduct.
"""

EVAL_PROMPT = """
You are the external perspective for a disclosure review tool.
Use only the supplied sourced ContextBrief items. Do not use memory or internal analysis.
If no sourced items exist, return Low risk and say there is no sourced external context.
External context is explanatory only and must not weaken internal review candidates.
Return Korean only.
"""


def build_query_agent(model_name: str = EXTERNAL_MODEL_NAME) -> Agent[None, SearchKeywords]:
    model = GoogleModel(model_name, provider=GoogleProvider(api_key=settings.google_api_key))
    return Agent(model, output_type=SearchKeywords, system_prompt=QUERY_PROMPT, retries=2)


def build_eval_agent(model_name: str = EXTERNAL_MODEL_NAME) -> Agent[None, PerspectiveAssessment]:
    model = GoogleModel(model_name, provider=GoogleProvider(api_key=settings.google_api_key))
    return Agent(model, output_type=PerspectiveAssessment, system_prompt=EVAL_PROMPT, retries=2)


async def generate_search_keywords(
    material: dict[str, object],
    agent_factory: Callable[..., Any] = build_query_agent,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> SearchKeywords:
    prompt = json.dumps(material, ensure_ascii=False, indent=2)
    keywords = await run_with_retry(
        make_agent(agent_factory, EXTERNAL_MODEL_NAME),
        prompt,
        EXTERNAL_MODEL_NAME,
        retry_delays,
    )
    return _sanitize_keywords(keywords, material)


async def evaluate_external_context(
    brief: ContextBrief,
    agent_factory: Callable[..., Any] = build_eval_agent,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> PerspectiveAssessment:
    prompt = json.dumps({"context_brief": brief.model_dump()}, ensure_ascii=False, indent=2)
    result = await run_with_retry(
        make_agent(agent_factory, EXTERNAL_MODEL_NAME),
        prompt,
        EXTERNAL_MODEL_NAME,
        retry_delays,
    )
    result.perspective = "external"
    result.evidence = [f"{item.source_title}: {item.source_url}" for item in brief.items]
    if not brief.items:
        result.risk_level = "Low"
        result.risk_areas = []
    return result


def _sanitize_keywords(keywords: SearchKeywords, material: dict[str, object]) -> SearchKeywords:
    company = str(material["company_name"])
    year = str(material["target_year"])
    banned = (
        "분식",
        "부정",
        "fraud",
        "manipulation",
        "scandal",
        "misconduct",
        "dio",
        "dso",
        "roe",
        "roa",
        "roi",
        "cfo",
    )
    queries = []
    for query in keywords.queries:
        lowered = query.lower()
        if any(word in lowered for word in banned):
            continue
        text = " ".join(str(query).split())
        if company not in text:
            text = f"{company} {text}"
        if year not in text:
            text = f"{text} {year}"
        if text not in queries:
            queries.append(text)
    if not queries:
        subjects = [
            str(item["subject"])
            for item in material.get("review_queue", [])[:2]  # type: ignore[index]
            if item.get("subject")  # type: ignore[union-attr]
        ]
        topic = " ".join(subjects) if subjects else "재무지표 변화 원인"
        queries = [f"{company} {year} {topic}"]
    return SearchKeywords(queries=queries[:3])
