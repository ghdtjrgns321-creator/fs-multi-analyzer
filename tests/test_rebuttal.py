"""S6 — 반박 에이전트 (PHASE2_DESIGN §10).

균형 반박이 카드에 반대근거·판정을 채우되, 위험도 보존·카드 제거 0·반박 미수행 유지를 고정한다.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from src.report import rebuttal as rb
from src.schemas.findings import AccountFinding, IssueType
from src.schemas.suspicion import RebuttalEntry, RebuttalOutput


def _card(account, cluster_key, *, risk="High") -> AccountFinding:
    return AccountFinding(
        account=account,
        issue_type=IssueType.REVENUE_RECEIVABLES,
        materiality_score=0.5,
        anomaly_score=0.0,
        confidence="Medium",
        risk_level=risk,
        cluster_key=cluster_key,
    )


def test_system_prompt_has_role_and_instruction() -> None:
    prompts = rb.load_perspective_prompts()
    text = rb.build_rebuttal_system_prompt(prompts)
    assert "반박" in text
    assert "normal_dominant" in text


def test_rebuttal_input_includes_suspicion_context() -> None:
    cards = [_card("매출채권", "acct:BS:매출채권")]
    context = {
        "acct:BS:매출채권": [
            {"perspective": "numeric", "description": "급증", "cited_value": "100"}
        ]
    }
    payload = rb.build_rebuttal_input(cards, context)
    assert payload[0]["cluster_key"] == "acct:BS:매출채권"
    assert payload[0]["suspicions"][0]["perspective"] == "numeric"


def test_apply_rebuttal_fills_matched_card() -> None:
    card = _card("매출채권", "acct:BS:매출채권")
    output = RebuttalOutput(
        entries=[
            RebuttalEntry(
                cluster_key="acct:BS:매출채권",
                verdict="normal_dominant",
                counter_evidence=["연말 대형계약"],
                normal_explanation=["판매 집중"],
                confirm_question=["4분기 매출?"],
                next_procedure=["연령분석 확인"],
            )
        ]
    )
    rb.apply_rebuttal([card], output)
    assert card.rebuttal_verdict == "normal_dominant"
    assert card.counter_evidence == ["연말 대형계약"]
    assert card.risk_level == "High"  # 위험도 숫자 불변(§9)


def test_apply_rebuttal_ignores_unknown_key_and_keeps_unmatched() -> None:
    card = _card("재고자산", "acct:BS:재고자산")
    output = RebuttalOutput(
        entries=[RebuttalEntry(cluster_key="acct:BS:없는키", verdict="suspicion_dominant")]
    )
    result = rb.apply_rebuttal([card], output)
    assert len(result) == 1  # 카드 제거 0
    assert card.rebuttal_verdict is None  # 매칭 안 됨 → 반박 미수행


def test_run_rebuttal_empty_cards() -> None:
    out = asyncio.run(rb.run_rebuttal([], {}))
    assert out.entries == []


def test_run_rebuttal_error_returns_empty() -> None:
    class BoomAgent:
        async def run(self, prompt: str):
            raise ValueError("boom")

    cards = [_card("매출채권", "acct:BS:매출채권")]
    out = asyncio.run(rb.run_rebuttal(cards, {}, agent_factory=lambda name="m": BoomAgent()))
    assert out.entries == []


def test_run_rebuttal_success_via_fake_agent() -> None:
    canned = RebuttalOutput(
        entries=[RebuttalEntry(cluster_key="acct:BS:매출채권", verdict="mixed")]
    )

    class FakeAgent:
        async def run(self, prompt: str):
            return SimpleNamespace(output=canned)

    cards = [_card("매출채권", "acct:BS:매출채권")]
    out = asyncio.run(rb.run_rebuttal(cards, {}, agent_factory=lambda name="m": FakeAgent()))
    assert out.entries[0].verdict == "mixed"


def test_no_key_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr(rb.settings, "openai_api_key", "")
    cards = [_card("매출채권", "acct:BS:매출채권")]
    out = asyncio.run(rb.run_rebuttal(cards, {}))
    assert out.entries == []
