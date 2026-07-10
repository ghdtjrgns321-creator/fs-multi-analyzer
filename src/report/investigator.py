"""카드별 조사원 — 결정론 게이트 + 도구 루프(PLAN §5 조사 단계).

게이트: 분해가 이미 원인을 설명(잔차 작고 단일 leaf 지배)했으면 도구 루프를 생략하고
종합 1호출만 한다. 배제가 아니라 경로 차이 — 모든 카드가 결론을 받는다.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from config.settings import settings
from src.agents.model_retry import run_with_retry
from src.report.decomposition import load_bridges
from src.report.investigation_config import load_investigation_config
from src.report.investigation_tools import InvestigationDeps
from src.report.investigation_tools import find_notes as _find_notes
from src.report.investigation_tools import get_decomposition as _get_decomposition
from src.report.investigation_tools import get_series as _get_series
from src.report.investigation_tools import top_changes as _top_changes
from src.report.perspective_runner import PROMPTS_PATH, load_perspective_prompts
from src.schemas.findings import AccountFinding
from src.schemas.investigation import InvestigationConclusion

OPENAI_MODEL_NAME = settings.openai_model


def build_investigator_agent(
    model_name: str = OPENAI_MODEL_NAME,
    prompts: dict | None = None,
    with_tools: bool = True,
) -> Agent[InvestigationDeps, InvestigationConclusion]:
    prompts = prompts or load_perspective_prompts(PROMPTS_PATH)
    block = prompts.get("investigator", {})
    system_prompt = "\n\n".join(
        p.strip() for p in (block.get("role", ""), block.get("instruction", "")) if p and p.strip()
    )
    model = OpenAIModel(model_name, provider=OpenAIProvider(api_key=settings.openai_api_key))
    model_settings = OpenAIModelSettings(timeout=settings.openai_timeout_seconds)
    if settings.openai_reasoning_effort:
        model_settings["openai_reasoning_effort"] = settings.openai_reasoning_effort
    agent: Agent[InvestigationDeps, InvestigationConclusion] = Agent(
        model,
        output_type=InvestigationConclusion,
        deps_type=InvestigationDeps,
        system_prompt=system_prompt,
        model_settings=model_settings,
        retries=2,
    )
    if with_tools:

        @agent.tool
        def get_series(ctx: RunContext[InvestigationDeps], series_key: str) -> dict[int, float]:
            """계정 연도별 금액 시계열. series_key 예: 'CFS:매출'."""

            return _get_series(ctx.deps, series_key)

        @agent.tool
        def get_decomposition(ctx: RunContext[InvestigationDeps], series_key: str) -> dict | None:
            """소계 계정의 YoY 변동을 구성 기여로 분해(항등식·재귀). 브리지 없으면 None."""

            return _get_decomposition(ctx.deps, series_key)

        @agent.tool
        def find_notes(ctx: RunContext[InvestigationDeps], keyword: str) -> list[dict]:
            """주석 fact에서 키워드 부분일치 검색(세그먼트·우발·특수관계 등)."""

            return _find_notes(ctx.deps, keyword)

        @agent.tool
        def top_changes(ctx: RunContext[InvestigationDeps]) -> list[dict]:
            """당기 전년비 변동 절대값 상위 계정 — 같이 움직인 계정 훑기."""

            return _top_changes(ctx.deps)

    return agent


def _investigation_prompt(card: AccountFinding, decomposition: dict | None) -> str:
    payload = {
        "account": card.account,
        "issue_type": card.issue_type.value,
        "claims": [c.model_dump() for c in card.claims],
        "merged_children": card.merged_children,
        "decomposition": decomposition,
    }
    return json.dumps(payload, ensure_ascii=False)


async def run_investigation(
    card: AccountFinding,
    report: dict,
    decomposition: dict | None,
    config: dict | None = None,
    agent_factory: Callable[..., object] | None = None,
    prompts: dict | None = None,
) -> InvestigationConclusion | None:
    """카드 1장 조사 — 게이트로 경로 분기, 실패는 None('조사 미수행' 표기, 둔갑 금지)."""

    if agent_factory is None and not settings.openai_api_key:
        return None
    cfg = config if config is not None else load_investigation_config()
    inv = cfg.get("investigation") or {}
    use_tools = needs_tool_loop(decomposition, inv.get("gate") or {})
    max_requests = int((inv.get("loop") or {}).get("max_requests", 8))
    deps = InvestigationDeps(
        series_rows=list(report.get("account_level_series") or []),
        target_year=int(report.get("target_year") or 0),
        bridges=load_bridges(),
        note_facts=list(report.get("note_facts") or []),
    )
    if agent_factory is None:
        agent = build_investigator_agent(prompts=prompts, with_tools=use_tools)
    else:
        agent = agent_factory(with_tools=use_tools)
    try:
        result = await asyncio.wait_for(
            run_with_retry(
                agent,
                _investigation_prompt(card, decomposition),
                OPENAI_MODEL_NAME,
                raw=True,
                deps=deps,
                usage_limits=UsageLimits(request_limit=max_requests),
            ),
            timeout=settings.openai_timeout_seconds * max_requests,
        )
    except Exception:
        return None
    conclusion: InvestigationConclusion = result.output
    conclusion.method = "tool_loop" if use_tools else "gate_summary"
    conclusion.tool_requests = getattr(result.usage(), "requests", 0)
    return conclusion


def needs_tool_loop(decomposition: dict | None, gate: dict) -> bool:
    """True = 도구 루프 필요(분해 없음·잔차 큼·기여 분산). False = 종합 1호출로 충분."""

    if not decomposition:
        return True
    residual_pct = decomposition.get("residual_pct")
    if residual_pct is None or abs(residual_pct) > float(gate.get("residual_pct_max", 20.0)):
        return True
    from dashboard.card_data import waterfall_leaves  # 기존 평탄화 재사용(external_verify 선례)

    delta = abs(float(decomposition.get("delta") or 0.0))
    if not delta:
        return True
    leaves = [(n, d) for n, d in waterfall_leaves(decomposition) if n != "미설명 잔차"]
    if not leaves:
        return True
    top_share = max(abs(d) for _, d in leaves) / delta * 100
    return top_share < float(gate.get("top_leaf_pct_min", 60.0))


__all__ = [
    "InvestigationDeps",
    "build_investigator_agent",
    "needs_tool_loop",
    "run_investigation",
]
