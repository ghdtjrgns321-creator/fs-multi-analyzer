"""Phase2 반박 에이전트 — PHASE2_DESIGN §10.

묶인 카드 전체를 일괄 1회 받아 카드마다 반대근거·정상설명·확인질문·다음절차를 채우고
판정 플래그(verdict)를 단다. 위험도 숫자는 안 건드리고(§9), 카드는 절대 제거하지 않는다.
반박 없는 카드는 verdict=None으로 남겨 '반박 미수행'으로 표시된다.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from config.settings import settings
from src.agents.model_retry import DEFAULT_RETRY_DELAYS, make_agent, run_with_retry
from src.report.perspective_runner import PROMPTS_PATH, load_perspective_prompts
from src.schemas.findings import AccountFinding
from src.schemas.suspicion import RebuttalOutput

OPENAI_MODEL_NAME = settings.openai_model


def build_rebuttal_system_prompt(prompts: dict[str, Any]) -> str:
    block = prompts.get("rebuttal", {})
    parts = [block.get("role", ""), block.get("instruction", "")]
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def build_rebuttal_agent(
    model_name: str = OPENAI_MODEL_NAME,
    prompts: dict[str, Any] | None = None,
    banned_vocab: set[str] | None = None,
) -> Agent[None, RebuttalOutput]:
    prompts = prompts or load_perspective_prompts(PROMPTS_PATH)
    model = OpenAIModel(model_name, provider=OpenAIProvider(api_key=settings.openai_api_key))
    model_settings = OpenAIModelSettings(timeout=settings.openai_timeout_seconds)
    if settings.openai_reasoning_effort:
        model_settings["openai_reasoning_effort"] = settings.openai_reasoning_effort
    agent: Agent[None, RebuttalOutput] = Agent(
        model,
        output_type=RebuttalOutput,
        system_prompt=build_rebuttal_system_prompt(prompts),
        model_settings=model_settings,
        retries=2,
    )
    from src.report.vocab_guard import attach_vocab_guard

    attach_vocab_guard(agent, banned_vocab or set())  # 어휘 게이트(내부 식별자 반려)
    return agent


def build_rebuttal_input(
    cards: list[AccountFinding],
    context: dict[str, list[dict]],
    decompositions: dict[str, dict] | None = None,
) -> list[dict]:
    """카드 + 의심근거(관점 description·cited_value) + 변동 분해(PLAN §6.5)를 반박 입력으로.

    분해가 있으면 반박이 숫자 없이 추측하는 대신 기여도("판관비 -54%")로 반박·설명하게 한다.
    """

    decompositions = decompositions or {}
    payload = []
    for card in cards:
        key = card.cluster_key or ""
        entry = {
            "cluster_key": key,
            "account": card.account,
            "issue_type": card.issue_type.value,
            "vote_count": card.vote_count,
            "materiality_score": card.materiality_score,
            "confidence": card.confidence,
            "suspicions": context.get(key, []),
        }
        if key in decompositions:  # 브리지 없는 카드는 키 자체를 생략(빈 필드 노이즈 금지)
            entry["decomposition"] = decompositions[key]
        if card.investigation is not None:  # 조사 결론 — 반박의 공격 대상(없으면 키 생략)
            entry["investigation"] = card.investigation.model_dump()
        payload.append(entry)
    return payload


async def run_rebuttal(
    cards: list[AccountFinding],
    context: dict[str, list[dict]],
    agent_factory: Callable[..., Any] | None = None,
    prompts: dict[str, Any] | None = None,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
    decompositions: dict[str, dict] | None = None,
) -> RebuttalOutput:
    """카드 전체 일괄 1회 반박. 키없음/에러는 빈 entries(카드는 그대로 생존)."""

    if not cards:
        return RebuttalOutput()
    if agent_factory is None and not settings.openai_api_key:
        return RebuttalOutput()
    prompts = prompts or load_perspective_prompts(PROMPTS_PATH)
    payload = build_rebuttal_input(cards, context, decompositions)
    # 어휘 게이트: 입력 payload의 내부 키(cluster_key·분해 필드 등)가 본문에 새면 반려.
    from src.report.vocab_guard import banned_identifiers

    banned_vocab = banned_identifiers(payload)
    factory = agent_factory or (
        lambda name=OPENAI_MODEL_NAME: build_rebuttal_agent(name, prompts, banned_vocab)
    )
    prompt = json.dumps(payload, ensure_ascii=False)
    try:
        return await asyncio.wait_for(
            run_with_retry(
                make_agent(factory, OPENAI_MODEL_NAME), prompt, OPENAI_MODEL_NAME, retry_delays
            ),
            timeout=settings.openai_timeout_seconds,
        )
    except Exception:
        return RebuttalOutput()


def apply_rebuttal(cards: list[AccountFinding], output: RebuttalOutput) -> list[AccountFinding]:
    """entries를 cluster_key로 카드에 주입. 없는 키 entry 무시(새 카드 0), 매칭 안 된 카드는 그대로.

    주의: 카드 객체를 in-place 수정한다(반환값은 동일 객체 리스트). 호출부는 같은 카드 dict를
    이후 정렬·렌더에 재사용하므로 의도된 동작. (불변 model_copy 리팩터는 백로그 — 리뷰 P1-2.)
    """

    by_key = {entry.cluster_key: entry for entry in output.entries}
    for card in cards:
        entry = by_key.get(card.cluster_key or "")
        if entry is None:
            continue  # 반박 미수행 — verdict=None 유지, 제거·강등 없음
        card.counter_evidence = entry.counter_evidence
        card.normal_explanation = entry.normal_explanation
        card.confirm_question = entry.confirm_question
        card.next_procedure = entry.next_procedure
        card.rebuttal_verdict = entry.verdict  # 위험도 숫자는 불변(§9)
    return cards


__all__ = [
    "apply_rebuttal",
    "build_rebuttal_agent",
    "build_rebuttal_input",
    "build_rebuttal_system_prompt",
    "run_rebuttal",
]
