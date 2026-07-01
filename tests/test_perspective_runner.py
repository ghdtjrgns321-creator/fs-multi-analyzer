"""S5 — 구조화 관점 실행 (PHASE2_DESIGN §9).

playbook 로딩·system prompt 합성·perspective 코드 재주입·키없음/에러 deferred를 고정한다.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from src.report import perspective_runner as pr
from src.schemas.findings import IssueType
from src.schemas.suspicion import PerspectiveOutput, SuspicionItem


def test_playbook_has_six_perspectives() -> None:
    prompts = pr.load_perspective_prompts()
    assert "shared" in prompts
    assert set(prompts["perspectives"]) >= {
        "numeric",
        "note",
        "flow",
        "trend",
        "external",
        "industry",
    }


def test_system_prompt_merges_shared_and_focus() -> None:
    prompts = pr.load_perspective_prompts()
    text = pr.build_system_prompt(prompts, "flow")
    assert "관점: flow" in text
    assert "related_accounts" in text  # flow focus
    assert "한국어" in text  # shared forbid


def _fake_factory(output: PerspectiveOutput):
    class FakeAgent:
        async def run(self, prompt: str):
            return SimpleNamespace(output=output)

    def factory(name: str = "m"):
        return FakeAgent()

    return factory


def test_perspective_label_restamped() -> None:
    wrong = PerspectiveOutput(
        suspicions=[
            SuspicionItem(
                perspective="note",  # 일부러 틀린 라벨
                scope="account",
                issue_type=IssueType.REVENUE_RECEIVABLES,
                account_id="매출채권",
                year="2024",
                cited_value="100",
                description="의심.",
            )
        ]
    )
    out = asyncio.run(
        pr.run_structured_perspective("numeric", {}, agent_factory=_fake_factory(wrong))
    )
    assert out.suspicions[0].perspective == "numeric"


def test_error_returns_failed() -> None:
    # LLM 호출 에러는 deferred(의도적 건너뜀)가 아니라 failed로 — 빈 결과 둔갑 차단(hollow-PASS).
    class BoomAgent:
        async def run(self, prompt: str):
            raise ValueError("boom")

    out = asyncio.run(
        pr.run_structured_perspective("numeric", {}, agent_factory=lambda name="m": BoomAgent())
    )
    assert out.status == "failed"
    assert out.suspicions == []


def test_no_key_returns_deferred(monkeypatch) -> None:
    # 키 없음은 의도적 건너뜀 → deferred 유지(실패와 구분).
    monkeypatch.setattr(pr.settings, "openai_api_key", "")
    out = asyncio.run(pr.run_structured_perspective("numeric", {}))
    assert out.status == "deferred"
