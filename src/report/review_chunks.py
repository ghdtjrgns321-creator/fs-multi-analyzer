"""S7 Step4 — 온보딩 LLM 검토관심 청크 선별 (B안 본체).

온보딩 LLM이 회사 사업보고서 원문(PART 텍스트)을 통독해, 감사인이 검토할 "공시 종류"가
실제 내용이 있는 청크를 골라낸다. baseline 키워드(report_review_keywords.yaml)는 LLM에 힌트로
주입하는 fallback일 뿐, 최종 선별·판단은 LLM이 한다(고정 키워드 의존 금지).

포지셔닝: 부정 확정 아님. "검토 관심 공시 종류" 식별이며 모든 청크는 정상 설명 가능성을 전제한다.
계산·LLM 분리: 여기는 LLM 해석만. 결정론 추출(PART 분해)은 src/notes/report_parts.py가 한다.
"""

from __future__ import annotations

import time
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from config.settings import settings
from src.notes.report_parts import ReportPart

BASELINE_PATH = Path("config/playbooks/report_review_keywords.yaml")
QUIRKS_PATH = Path("config/company_quirks.yaml")

# 온보딩 입력에서 제외할 PART — 마케팅 서술(II)·기계적 상세표(XII)는 검토 신호가 희박.
_EXCLUDE_NUMERALS = {"II", "XII"}

SYSTEM_PROMPT = """
당신은 공시 재무제표 리뷰 도구의 온보딩 검토자다.
주어진 사업보고서 본문(PART 텍스트)만 사용한다. 외부 사실·뉴스·추측을 쓰지 않는다.
임무: 감사인이 검토할 "공시 종류"(우발·소송·제재·담보보증·메자닌(전환사채 등)·특수관계자/대주주
거래·연결범위 변동·손상·계속기업/상장위험·감사의견/내부통제·재작성 등)가 본문에 실제 내용으로
존재하는 청크만 고른다.
회계정책 보일러플레이트(모든 회사에 있는 표준 IFRS 서술)와 "해당사항 없음"류 빈 섹션은 제외한다.
baseline 힌트 키워드는 참고만 하고, 최종 선별은 본문 근거로 직접 판단한다.
부정(분식)을 확정하지 않는다. 각 청크는 검토 관심 후보이며 정상 설명이 가능함을 전제한다.
한국어로만 답한다.
"""


class ReviewChunk(BaseModel):
    """검토 관심 공시 청크 1건."""

    disclosure_type: str = Field(description="공시 종류(예: 제재_규제, 메자닌_자금조달)")
    part: str = Field(default="", description="출처 PART 로마숫자(예: XI)")
    evidence: str = Field(description="본문에서 인용한 근거 문장(짧게)")
    why_review: str = Field(description="왜 검토 관심인가(정상 설명 가능 전제)")


class ReviewChunkSelection(BaseModel):
    """한 회사연도의 온보딩 청크 선별 결과."""

    corp_code: str = ""
    year: str = ""
    chunks: list[ReviewChunk] = Field(default_factory=list)
    summary: str = ""


def load_review_baseline(path: Path = BASELINE_PATH) -> dict:
    """검토관심 baseline 키워드 yaml 로드(없으면 빈 dict)."""

    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_onboarding_input(parts: list[ReportPart]) -> str:
    """PART 리스트에서 검토관심 본문만 모아 온보딩 입력 텍스트로 만든다(II·XII 제외)."""

    blocks = []
    for part in parts:
        if part.numeral in _EXCLUDE_NUMERALS:
            continue
        if part.text.strip():
            blocks.append(f"===== PART {part.numeral}. {part.title} =====\n{part.text}")
    return "\n\n".join(blocks)


def _baseline_hint(baseline: dict) -> str:
    """baseline yaml을 LLM 힌트 문자열로 압축(공시유형명 + anchors 일부)."""

    types = baseline.get("disclosure_types", {})
    lines = ["[baseline 힌트 — 공시 종류와 식별 키워드(참고용, 최종판단은 본문 근거)]"]
    for name, spec in types.items():
        anchors = ", ".join(spec.get("anchors", [])[:4])
        events = ", ".join(spec.get("event_signals", [])[:4])
        lines.append(f"- {name}: 앵커[{anchors}] 이벤트[{events}]")
    return "\n".join(lines)


def build_chunk_agent(model_name: str | None = None):
    """온보딩 청크선별 OpenAI 에이전트 생성(perspectives 패턴 동일)."""

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
        output_type=ReviewChunkSelection,
        system_prompt=SYSTEM_PROMPT,
        model_settings=model_settings,
        retries=2,
    )


def select_review_chunks(
    parts: list[ReportPart],
    corp_code: str,
    year: str,
    baseline_path: Path = BASELINE_PATH,
    model_name: str | None = None,
) -> dict:
    """온보딩 LLM으로 검토관심 청크 선별. usage·latency 캡처. 무키/실패는 graceful.

    반환: {status, selection, usage:{input_tokens,output_tokens,total_tokens}, latency_s, message}
    """

    if not settings.openai_api_key:
        return {"status": "skipped", "message": "OPENAI_API_KEY 미설정", "selection": None}

    baseline = load_review_baseline(baseline_path)
    body = build_onboarding_input(parts)
    prompt = (
        f"{_baseline_hint(baseline)}\n\n"
        f"[대상] corp_code={corp_code} year={year}\n\n"
        f"[사업보고서 본문]\n{body}"
    )

    try:
        agent = build_chunk_agent(model_name)
        started = time.perf_counter()
        result = agent.run_sync(prompt)
        latency = time.perf_counter() - started
        usage = result.usage()
        selection = result.output
        selection.corp_code = selection.corp_code or corp_code
        selection.year = selection.year or year
        return {
            "status": "ok",
            "message": "",
            "selection": selection,
            "usage": {
                "input_tokens": getattr(usage, "request_tokens", 0) or 0,
                "output_tokens": getattr(usage, "response_tokens", 0) or 0,
                "total_tokens": getattr(usage, "total_tokens", 0) or 0,
            },
            "latency_s": round(latency, 2),
            "input_chars": len(body),
        }
    except Exception as exc:  # noqa: BLE001 (온보딩은 LLM 오류를 안내로 흡수)
        return {
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
            "selection": None,
        }


def load_content_chunks(corp_code: str, year: str | int, path: Path = QUIRKS_PATH) -> list[dict]:
    """company_quirks.yaml에 캐시된 온보딩 선별 청크(content_chunks)를 로드.

    파일/회사/연도 미존재는 빈 리스트로 graceful(선별 안 된 정상 경로에서 깨지지 않게).
    load_company_quirks는 alias/override만 통과시키므로 content_chunks 전용 로더가 필요하다.
    """

    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    quirks = payload.get("company_quirks") or {}
    year_bucket = (quirks.get(str(corp_code), {}) or {}).get(str(year), {}) or {}
    return list(year_bucket.get("content_chunks", []) or [])


def persist_review_chunks(
    corp_code: str,
    year: str,
    selection: ReviewChunkSelection,
    path: Path = QUIRKS_PATH,
) -> dict:
    """선별 청크를 company_quirks.yaml의 content_chunks에 캐시(append, 헤더 주석 보존)."""

    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    payload = yaml.safe_load(raw) or {}
    quirks = payload.get("company_quirks") or {}

    year_bucket = quirks.setdefault(str(corp_code), {}).setdefault(str(year), {})
    year_bucket["content_chunks"] = [chunk.model_dump() for chunk in selection.chunks]
    payload["company_quirks"] = quirks

    header_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("#"):
            header_lines.append(line)
        else:
            break
    header = ("\n".join(header_lines) + "\n") if header_lines else ""

    body = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, default_flow_style=False)
    path.write_text(header + body, encoding="utf-8")
    return payload["company_quirks"]
