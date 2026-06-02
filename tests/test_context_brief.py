import asyncio
from types import SimpleNamespace

from src.agents.context_brief import build_context_query, create_context_brief
from src.schemas.context import ContextBrief, ContextItem
from tests.test_red_flags_and_agent import valid_finding


def test_context_query_uses_company_year_and_issue() -> None:
    query = build_context_query("삼성전자", 2023, valid_finding())

    assert "삼성전자" in query
    assert "2023" in query
    assert "매출채권" in query


def test_context_brief_drops_items_without_grounded_source(monkeypatch) -> None:
    class FakeClient:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "삼성전자 2023" in prompt
            return SimpleNamespace(
                output=(
                    ContextBrief(
                        items=[
                            ContextItem(
                                claim="2023년 반도체 업황 약세가 보도되었다.",
                                source_title="Grounded article",
                                source_url="https://example.com/grounded",
                            ),
                            ContextItem(
                                claim="출처 없는 주장은 버려야 한다.",
                                source_title="",
                                source_url="",
                            ),
                            ContextItem(
                                claim="grounding chunk에 없는 URL도 버려야 한다.",
                                source_title="Ungrounded",
                                source_url="https://example.com/ungrounded",
                            ),
                        ]
                    ),
                    {
                        "https://example.com/grounded": "Grounded article",
                    },
                )
            )

    monkeypatch.setattr("src.agents.context_brief.settings.google_api_key", "fake")

    brief = asyncio.run(
        create_context_brief(
            valid_finding(),
            company_name="삼성전자",
            year=2023,
            client_factory=FakeClient,
            retry_delays=(0,),
        )
    )

    assert len(brief.items) == 1
    assert brief.items[0].source_url == "https://example.com/grounded"


def test_context_brief_does_not_mutate_finding(monkeypatch) -> None:
    finding = valid_finding()
    original = finding.model_dump(mode="json")

    class FakeClient:
        async def run(self, prompt: str) -> SimpleNamespace:
            return SimpleNamespace(output=(ContextBrief(items=[]), {}))

    monkeypatch.setattr("src.agents.context_brief.settings.google_api_key", "fake")

    asyncio.run(
        create_context_brief(
            finding,
            company_name="삼성전자",
            year=2023,
            client_factory=FakeClient,
            retry_delays=(0,),
        )
    )

    assert finding.model_dump(mode="json") == original
