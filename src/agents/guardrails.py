"""Hallucination guardrails for LLM Finding output."""

from __future__ import annotations

from pydantic_ai import ModelRetry

from src.schemas.findings import AccountFinding

BANNED_EXTERNAL_FACTS = ["반도체 불황", "뉴스", "시장점유율", "금리 인상으로", "AI 수요"]


def validate_numeric_finding(output: AccountFinding) -> AccountFinding:
    """Reject empty evidence and common external-fact leakage."""

    if not output.numeric_evidence and not output.flow_evidence:
        raise ModelRetry("numeric_evidence or flow_evidence is required")
    if not output.confirm_question:
        raise ModelRetry("confirm_question is required when interpretation is uncertain")

    text = " ".join(
        [
            *output.counter_evidence,
            *output.normal_explanation,
            *output.next_procedure,
            *output.confirm_question,
        ]
    )
    for phrase in BANNED_EXTERNAL_FACTS:
        if phrase in text:
            raise ModelRetry(f"External fact is not allowed: {phrase}")
    return output
