"""PydanticAI note analyst for receivables note grounding."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent, ModelRetry
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config.settings import settings
from src.agents.gemini_retry import DEFAULT_RETRY_DELAYS, MODEL_NAME, fallback_model, run_with_retry
from src.agents.guardrails import validate_numeric_finding
from src.notes.indexer import NoteSection
from src.schemas.findings import AccountFinding

SYSTEM_PROMPT = """
You are the note analyst for a disclosure review tool.
Use only the provided note_sections and existing AccountFinding.
Extract actual mentions relevant to the account, such as credit risk, overdue, impairment,
allowance, collection, inventory valuation loss, net realizable value, or cost recognition.
Fill note_evidence with note locators and exact short Korean snippets from note_sections.
Set note_cross_check to explain whether numeric signals align with or diverge from note text.
Do not use external facts. If the note is insufficient, ask confirm_question.
Return one AccountFinding in Korean.
"""


def build_note_analyst_agent(
    model_name: str = MODEL_NAME,
    note_sections: list[NoteSection] | None = None,
) -> Agent[None, AccountFinding]:
    model = GoogleModel(model_name, provider=GoogleProvider(api_key=settings.google_api_key))
    agent = Agent(model, output_type=AccountFinding, system_prompt=SYSTEM_PROMPT, retries=2)

    @agent.output_validator
    def _validate(output: AccountFinding) -> AccountFinding:
        output = validate_numeric_finding(output)
        if note_sections is not None:
            return _validate_note_grounding(output, note_sections)
        return output

    return agent


async def create_note_enriched_finding(
    finding: AccountFinding,
    note_sections: list[NoteSection],
    agent_factory: Callable[..., Any] = build_note_analyst_agent,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> AccountFinding:
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is required to run the note analyst")
    prompt = json.dumps(_payload(finding, note_sections), ensure_ascii=False, indent=2)
    try:
        result = await run_with_retry(
            _make_note_agent(agent_factory, MODEL_NAME, note_sections),
            prompt,
            MODEL_NAME,
            retry_delays,
        )
    except RuntimeError:
        fallback = fallback_model()
        if not fallback:
            raise
        result = await run_with_retry(
            _make_note_agent(agent_factory, fallback, note_sections), prompt, fallback, retry_delays
        )
    return _merge_note_fields(finding, _validate_note_grounding(result, note_sections))


def _payload(finding: AccountFinding, note_sections: list[NoteSection]) -> dict[str, object]:
    return {
        "finding": finding.model_dump(mode="json"),
        "note_sections": [
            {
                "locator": section.locator,
                "title": section.title,
                "year": section.current_year,
                "prior_year": section.prior_year,
                "matched_keywords": section.matched_keywords,
                "text": section.text[:4000],
            }
            for section in note_sections
        ],
    }


def _make_note_agent(
    agent_factory: Callable[..., Any],
    model_name: str,
    note_sections: list[NoteSection],
) -> Any:
    for args in ((model_name, note_sections), (model_name,), ()):
        try:
            return agent_factory(*args)
        except TypeError:
            continue
    raise RuntimeError("Unable to create note analyst agent")


def _validate_note_grounding(
    finding: AccountFinding,
    note_sections: list[NoteSection],
) -> AccountFinding:
    texts = {section.locator: section.text for section in note_sections}
    if not finding.note_evidence:
        raise ModelRetry("note_evidence is required for the note analyst")
    for evidence in finding.note_evidence:
        if evidence.source != "note" or evidence.locator not in texts:
            raise ModelRetry(f"Invalid note evidence locator: {evidence.locator}")
        if evidence.value and evidence.value not in texts[evidence.locator]:
            raise ModelRetry("note_evidence value must be copied from the note section")
    if not finding.note_cross_check:
        raise ModelRetry("note_cross_check is required")
    return finding


def _merge_note_fields(base: AccountFinding, note_result: AccountFinding) -> AccountFinding:
    merged = base.model_copy(deep=True)
    merged.note_evidence = note_result.note_evidence
    merged.note_cross_check = note_result.note_cross_check
    return merged
