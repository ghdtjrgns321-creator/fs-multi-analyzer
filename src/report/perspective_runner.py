"""Phase2 구조화 관점 실행 — PHASE2_DESIGN §9.

관점 agent는 PerspectiveOutput(의심건 봉투)을 반환하도록 PydanticAI로 출력을 강제한다.
관점별 focus는 config playbook(데이터)에서, 공통 규칙은 코드에서 합쳐 system prompt를 만든다.
perspective 라벨은 코드가 재주입(LLM 자기라벨 불신). 환각 검사는 여기서 안 한다(S2 코드 단일).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from config.settings import settings
from src.agents.model_retry import DEFAULT_RETRY_DELAYS, make_agent, run_with_retry
from src.schemas.suspicion import PerspectiveName, PerspectiveOutput

PROMPTS_PATH = Path("config/playbooks/perspective_prompts.yaml")
OPENAI_MODEL_NAME = settings.openai_model
# 발견자 관점(카드 생성 전 병렬 스캔). external은 발견자가 아니라 카드 확정 후
# 타깃 검증자(src/report/external_verify.py)로 재배치됨 — PLAN §5 후속 검증 단계.
ALL_PERSPECTIVES: tuple[PerspectiveName, ...] = (
    "numeric",
    "note",
    "flow",
    "trend",
    "industry",
)


def load_perspective_prompts(path: Path = PROMPTS_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_system_prompt(prompts: dict[str, Any], perspective: str) -> str:
    """공통(role·grounding·forbid·output) + 관점 focus 를 합친다."""

    shared = prompts.get("shared", {})
    focus = prompts.get("perspectives", {}).get(perspective, {}).get("focus", "")
    parts = [
        shared.get("role", ""),
        shared.get("grounding", ""),
        shared.get("forbid", ""),
        shared.get("output", ""),
        f"[관점: {perspective}]\n{focus}",
    ]
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def build_structured_perspective_agent(
    perspective: str,
    model_name: str = OPENAI_MODEL_NAME,
    prompts: dict[str, Any] | None = None,
    banned_vocab: set[str] | None = None,
) -> Agent[None, PerspectiveOutput]:
    """관점 agent — 출력 타입 PerspectiveOutput 강제(PydanticAI).

    banned_vocab: 이 호출의 재료에서 추출한 내부 식별자 — 본문에 새면 코드가 반려(어휘 게이트)."""

    prompts = prompts or load_perspective_prompts()
    model = OpenAIModel(model_name, provider=OpenAIProvider(api_key=settings.openai_api_key))
    model_settings = OpenAIModelSettings(timeout=settings.openai_timeout_seconds)
    if settings.openai_reasoning_effort:
        model_settings["openai_reasoning_effort"] = settings.openai_reasoning_effort
    agent: Agent[None, PerspectiveOutput] = Agent(
        model,
        output_type=PerspectiveOutput,
        system_prompt=build_system_prompt(prompts, perspective),
        model_settings=model_settings,
        retries=2,
    )
    from src.report.vocab_guard import attach_vocab_guard

    attach_vocab_guard(agent, banned_vocab or set())
    return agent


async def run_structured_perspective(
    perspective: PerspectiveName,
    material_board: dict[str, object],
    agent_factory: Callable[..., Any] | None = None,
    prompts: dict[str, Any] | None = None,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> PerspectiveOutput:
    """관점 1회 실행. 키 없음/에러는 deferred. perspective 라벨은 코드가 재주입."""

    if agent_factory is None and not settings.openai_api_key:
        return PerspectiveOutput(status="deferred")
    prompts = prompts or load_perspective_prompts()
    # 어휘 게이트: 이 호출의 재료 키를 금지 목록으로(입력이 모집단 — 새 필드 자동 커버).
    from src.report.vocab_guard import banned_identifiers

    banned_vocab = banned_identifiers(material_board)
    factory = agent_factory or (
        lambda name=OPENAI_MODEL_NAME: build_structured_perspective_agent(
            perspective, name, prompts, banned_vocab=banned_vocab
        )
    )
    prompt = json.dumps(
        {"perspective": perspective, "material_board": material_board},
        ensure_ascii=False,
    )
    try:
        output: PerspectiveOutput = await asyncio.wait_for(
            run_with_retry(
                make_agent(factory, OPENAI_MODEL_NAME), prompt, OPENAI_MODEL_NAME, retry_delays
            ),
            timeout=settings.openai_timeout_seconds,
        )
    except Exception:
        # LLM 호출 실패(quota·타임아웃·에러)는 deferred(의도적 건너뜀)와 구분해 failed로.
        # deferred로 묻으면 0건이 "위험 후보 없음"으로 둔갑한다(hollow-PASS).
        return PerspectiveOutput(status="failed")
    # 코드가 perspective 재주입(LLM이 자기 관점을 잘못 라벨링하는 것 차단).
    stamped = [item.model_copy(update={"perspective": perspective}) for item in output.suspicions]
    return PerspectiveOutput(status=output.status, suspicions=stamped)


def collect_perspective_materials(report: dict[str, object]) -> dict[str, dict]:
    """6관점 material을 기존 helper로 모은다. 외부·동종 실패는 deferred dict."""

    from src.report.external import external_material
    from src.report.industry import industry_material
    from src.report.materials import (
        flow_material,
        note_material,
        numeric_material,
        trend_material,
    )

    materials: dict[str, dict] = {
        "numeric": numeric_material(report),
        "note": note_material(
            corp_code=str(report["corp_code"]),
            year=int(report["target_year"]),  # type: ignore[arg-type]
            note_facts=report.get("note_facts"),  # type: ignore[arg-type]
        ),
        "flow": flow_material(report),
        "trend": trend_material(report),
    }
    for name, fn in (("external", external_material), ("industry", industry_material)):
        try:
            materials[name] = fn(report)
        except Exception as exc:
            materials[name] = {"status": "deferred", "reason": str(exc) or exc.__class__.__name__}
    return materials


__all__ = [
    "ALL_PERSPECTIVES",
    "build_structured_perspective_agent",
    "build_system_prompt",
    "collect_perspective_materials",
    "load_perspective_prompts",
    "run_structured_perspective",
]
