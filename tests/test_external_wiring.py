"""external 관점 실검색 배선 — Phase2 카드 파이프라인 연결(死코드 부활).

내부 이상신호→검색어(Gemini)→구글 grounding 검색→출처 있는 SuspicionItem(scope=company·source_url)
으로 변환한다. 검색 의존성은 주입으로 모킹(실 API 없이 배선 검증).
"""

from __future__ import annotations

import asyncio

from src.report.external import run_external_suspicions
from src.report.external_agentic import SearchKeywords
from src.schemas.context import ContextBrief, ContextItem


def _report() -> dict:
    return {
        "company_name": "대주산업",
        "business_domain": {},
        "target_year": "2024",
        "review_queue": [{"subject": "매출채권", "key_evidence": "x"}],
        "ratio_summary": {},
        "latest_signal_snapshot": {},
    }


def _fake_query_agent(*_a, **_k):
    class _Agent:
        async def run(self, prompt: str):
            return type(
                "R", (), {"output": SearchKeywords(queries=["대주산업 2024 매출채권 대손"])}
            )()

    return _Agent()


async def _fake_context_factory(queries, retry_delays=()):
    return ContextBrief(
        items=[
            ContextItem(
                claim="업황 둔화 보도", source_title="기사A", source_url="https://a.example/1"
            ),
            ContextItem(
                claim="증설 투자 보도", source_title="기사B", source_url="https://b.example/2"
            ),
        ]
    )


def test_external_search_produces_sourced_suspicions() -> None:
    out = asyncio.run(
        run_external_suspicions(
            _report(),
            query_agent_factory=_fake_query_agent,
            context_factory=_fake_context_factory,
        )
    )
    assert out.status == "completed"
    assert len(out.suspicions) == 2
    for item in out.suspicions:
        assert item.perspective == "external"
        assert item.scope == "company"
        assert item.source_url and item.source_url.startswith("http")


def test_external_deferred_when_no_google_key(monkeypatch) -> None:
    # 실검색 경로인데 키 없음 → deferred(빈결과가 '위험 없음'으로 둔갑 금지, §9).
    monkeypatch.setattr("src.report.external.settings.google_api_key", "")
    out = asyncio.run(run_external_suspicions(_report()))
    assert out.status == "deferred"
    assert out.suspicions == []
