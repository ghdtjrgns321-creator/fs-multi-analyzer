"""Layer 1 서술 리더 엔진 — 파트 본문에서 감사 검토 항목 구조화추출(LLM).

설계 §4~§5. 목차 macro-block별 focus 프롬프트(reader_assign)를 시스템 프롬프트에 얹어, 파트 본문에서
`ExtractedItem` 리스트를 뽑는다. review_chunks(S7)와 같은 패턴이나, 단일주제 버킷팅이 아니라 파트를
읽고 항목을 추출한다(Layer 2가 파트를 가로질러 소비). 계산·LLM 분리: 여기는 LLM 해석·인용만,
정밀 계산은 결정론(Phase1). 무키·오류는 graceful(온보딩을 장애로 멈추지 않게).
"""

from __future__ import annotations

import time

from config.settings import settings
from src.notes.report_parts import ReportPart
from src.schemas.extract import ReaderOutput

SYSTEM_PROMPT = """당신은 공시 재무제표 리뷰 도구의 사업보고서 서술 리더다. 주어진 사업보고서 파트 본문만 사용한다.
외부 사실·뉴스·추측을 쓰지 않는다.
임무: 감사인이 검토할 가치가 있는 항목만 뽑아 구조화한다. 명세 나열(임원 개인 경력·계열사 전체 목록 등)은
요약/개수로만, 감사 고가치(특수관계·가족 임원·고액보수·대주주거래·소송·우발·제재·담보·내부통제 취약·
핵심감사사항·중요 회계추정)는 개별 항목으로.
계산·비율·증감률 산정 금지 — 원문 수치는 그대로 인용만 한다(옮겨적기+요약).
표에서 숫자를 인용할 때는 그 표의 단위 헤더(예: 단위:백만원, 단위:천US$, 단위:천원)를 숫자에 반드시
함께 적는다 — 단위 없는 맨숫자 금지. 통화·배수가 셀이 아니라 표 헤더에만 적혀 있으면 헤더를 찾아
그 단위를 숫자 옆에 명시한다(예: 채무보증한도 917,000천US$). 스케일을 잃은 숫자는 쓸모없다.
재무제표·주석에서 뽑은 항목은 연결(CFS)/별도(OFS)를 fs_div에 반드시 채운다 — 같은 주제가 연결·별도
두 번 실리므로 축이 없으면 서로 다른 금액이 같은 사실로 오인된다. 판정 근거는 원문에 있다:
주석 표제("연결재무제표 주석" vs "재무제표 주석")와 본문 주어("연결회사는" vs "회사는").
근거가 없으면 비워 둔다(추측 금지). 연결/별도 구분이 없는 서술 파트는 빈 값이 정상이다.
부정(분식)을 확정하지 않는다. 각 항목은 검토 관심 후보이며 정상 설명이 가능함을 전제한다.
근거 없는 항목은 만들지 않는다(evidence 필수). 한국어로만 답한다."""


def build_reader_agent(model_name: str | None = None):
    """서술 리더 OpenAI 에이전트 생성(review_chunks 패턴 동일). output_type=ReaderOutput."""

    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
    from pydantic_ai.providers.openai import OpenAIProvider

    model = OpenAIModel(
        model_name or settings.openai_model,
        provider=OpenAIProvider(api_key=settings.openai_api_key),
    )
    model_settings = OpenAIModelSettings(timeout=settings.openai_timeout_seconds)
    if settings.openai_reasoning_effort:
        model_settings["openai_reasoning_effort"] = settings.openai_reasoning_effort
    return Agent(
        model,
        output_type=ReaderOutput,
        system_prompt=SYSTEM_PROMPT,
        model_settings=model_settings,
        retries=2,
    )


def run_reader(part: ReportPart, focus: str, model_name: str | None = None) -> dict:
    """서술 리더 1회 실행. focus+파트 본문으로 ExtractedItem 추출. usage·latency 캡처.

    반환: {status, output:ReaderOutput|None, usage:{input/output/total_tokens}, latency_s, message}.
    무키는 status="skipped", 오류는 status="error"로 graceful(장애로 멈추지 않게).
    """

    if not settings.openai_api_key:
        return {"status": "skipped", "message": "OPENAI_API_KEY 미설정", "output": None}

    prompt = f"[초점]\n{focus}\n\n[PART {part.numeral}. {part.title} 본문]\n{part.text}"
    try:
        agent = build_reader_agent(model_name)
        started = time.perf_counter()
        result = agent.run_sync(prompt)
        latency = time.perf_counter() - started
        usage = result.usage()
        return {
            "status": "ok",
            "message": "",
            "output": result.output,
            "usage": {
                "input_tokens": getattr(usage, "request_tokens", 0) or 0,
                "output_tokens": getattr(usage, "response_tokens", 0) or 0,
                "total_tokens": getattr(usage, "total_tokens", 0) or 0,
            },
            "latency_s": round(latency, 2),
            "input_chars": len(part.text),
        }
    except Exception as exc:  # noqa: BLE001 (리더는 LLM 오류를 안내로 흡수)
        return {"status": "error", "message": f"{type(exc).__name__}: {exc}", "output": None}
