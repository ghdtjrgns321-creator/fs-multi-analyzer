"""온보딩 LLM 별칭 제안기 — 무표준코드 미매핑 계정에 canonical 후보 제안.

무표준코드 라벨(예: KB '투자금융자산')은 표준코드가 없어 매핑이 안 되고, 수백 개 금융
canonical 중 어디로 넣을지는 회계 분류 판단이라 전역 별칭이 위험하다(이중계상·오분류).
→ 회사 단위로: 계산(후보 검색)은 코드, 분류 선택은 LLM, 적용은 **고신뢰만 자동 등록**
(온보딩 auto_register_aliases, 임계 미만·기타는 보류 → '기타 중요 계정' 경로로 표면화).

포지셔닝: 부정 확정 아님. LLM은 제시된 candidate 목록 안에서만 고른다(없으면 '기타 중요
계정'으로 보류). 보류분 교정·수동 등록은 전처리 페이지(dashboard/onboarding.py)가 담당.
"""

from __future__ import annotations

import time
from pathlib import Path

import duckdb
import yaml
from pydantic import BaseModel, Field

from config.settings import settings
from src.db.normalized import db_path
from src.normalize.config import normalize_label

CANONICAL_PATH = Path("config/canonical_accounts.yaml")
NO_MATCH = "기타 중요 계정"  # 후보 중 적절한 게 없을 때 보류값

# sj_div → 호환 statement(같은 표 family만 후보로). SCE는 전용 2D가 담당 → 제외.
_STATEMENT_COMPAT: dict[str, set[str]] = {
    "BS": {"BS"},
    "IS": {"IS", "CIS"},
    "CIS": {"IS", "CIS"},
    "CF": {"CF"},
}


class AliasSuggestion(BaseModel):
    """미매핑 계정 1건에 대한 별칭 제안(제안일 뿐, 자동적용 아님)."""

    alias: str = Field(description="회사 라벨(미매핑 계정명)")
    sj_div: str = Field(default="", description="표 구분(BS/IS/CIS/CF)")
    suggested_canonical: str = Field(description="제안 canonical(candidates 중 하나, 없으면 기타)")
    confidence: float = Field(default=0.0, description="0~1 신뢰도")
    reason: str = Field(default="", description="회계적 근거(짧게)")


class AliasSuggestionResult(BaseModel):
    """한 회사연도의 별칭 제안 묶음."""

    corp_code: str = ""
    year: str = ""
    suggestions: list[AliasSuggestion] = Field(default_factory=list)


def _bigrams(text: str) -> set[str]:
    norm = normalize_label(text)
    return {norm[i : i + 2] for i in range(len(norm) - 1)} if len(norm) >= 2 else {norm}


def load_canonical_specs(path: Path = CANONICAL_PATH) -> dict[str, dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload.get("canonical_accounts", {}) or {}


def candidate_canonicals(
    label: str, sj_div: str, specs: dict[str, dict] | None = None, limit: int = 12
) -> list[str]:
    """statement 호환 canonical을 라벨 유사도(2-gram 자카드)순으로 ≤limit개. 정확일치 우선."""

    specs = specs if specs is not None else load_canonical_specs()
    compat = _STATEMENT_COMPAT.get(sj_div, set())
    if not compat:
        return []
    label_grams = _bigrams(label)
    label_norm = normalize_label(label)
    scored: list[tuple[float, str]] = []
    for canon, spec in specs.items():
        if not isinstance(spec, dict) or spec.get("statement") not in compat:
            continue
        names = [canon, *spec.get("aliases", [])]
        # 정확 라벨 일치는 최상위
        if any(normalize_label(n) == label_norm for n in names):
            scored.append((1.0, canon))
            continue
        best = 0.0
        for n in names:
            g = _bigrams(n)
            if not (g and label_grams):
                continue
            jac = len(g & label_grams) / len(g | label_grams)
            best = max(best, jac)
        if best > 0:
            scored.append((best, canon))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [c for _, c in scored[:limit]]


def unmapped_accounts(corp_code: str, year: int, data_dir: Path | None = None) -> list[dict]:
    """정규화 DB에서 무표준코드 미매핑 계정(SCE 제외). (alias, sj_div, amount) 중복 제거."""

    root = data_dir or settings.data_dir
    path = db_path(corp_code, year, root)
    if not path.exists():
        return []
    with duckdb.connect(str(path), read_only=True) as con:
        rows = con.execute(
            """
            select label, sj_div, max(abs(amount)) amt
            from normalized_financials
            where mapping_status = 'unmapped_extension_account'
              and sj_div <> 'SCE'
              and (account_id like '%미사용%' or trim(account_id) = '')
            group by label, sj_div
            order by amt desc
            """
        ).fetchall()
    return [{"alias": r[0], "sj_div": r[1], "amount": float(r[2] or 0)} for r in rows]


SYSTEM_PROMPT = """
당신은 공시 재무제표 정규화의 계정 분류 보조자다.
회사가 표준계정코드 없이 신고한 라벨 여러 개를 각각, 그 계정의 candidate canonical 목록 중에서
회계적으로 가장 맞는 하나로 분류 제안한다. suggestions 배열로 모든 계정을 반환하되, 각 항목의 alias에는
입력으로 받은 라벨을 그대로 적는다. 각 계정은 자기 후보 목록 안에서만 고르고 다른 계정의 후보를 쓰지 않는다.
목록에 적절한 것이 없으면 반드시 '기타 중요 계정'으로 둔다. candidate 밖의 canonical을 지어내지 않는다(앵커링).
같은 표(statement) 안에서만 고른다.

[회계 구분 주의 — 표면 글자가 비슷해도 실질이 다르면 candidate에 그 실질이 없을 수 있다.
억지로 고르지 말고 조금이라도 불확실하면 '기타 중요 계정'으로 둔다. 아래는 흔한 혼동 예시다]
- 발생원가(제조원가·매입액)와 비용화(매출원가)는 다르다.
- 잔액(기초·기말 재고액)과 변동(재고의 변동)은 다르다.
- 소계 범위가 다르면(예: 당좌자산은 유동자산의 일부) 같은 계정이 아니다.
- 순증감과 단방향(증가/감소)을 구분한다.
- 특수·구조화 상품(유동화채무·신주인수권부사채·공급자금융·파생상품)을 일반 계정으로 일반화하지 않는다.
- 폐기와 처분, 계속영업과 중단영업을 구분한다.
- 자본거래의 주체·방향(주식선택권 행사와 신주발행, 종속기업 배당과 비지배 배당, 양수·양도·분할·합병)을 혼동하지 않는다.

부정(분식)을 확정하지 않는다. 제안은 후보이며 사람이 최종 확인한다. 한국어로만 답한다.
""".strip()


def build_alias_agent(model_name: str | None = None):
    """별칭 제안 OpenAI 에이전트(perspectives/review_chunks 패턴 동일)."""

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
        output_type=AliasSuggestionResult,
        system_prompt=SYSTEM_PROMPT,
        model_settings=model_settings,
        retries=2,
    )


def _anchor(suggestion: AliasSuggestion, candidates: list[str]) -> AliasSuggestion:
    """제안 canonical이 candidates 밖이면 '기타 중요 계정'으로 강등(앵커링·환각 차단)."""

    if (
        suggestion.suggested_canonical not in candidates
        and suggestion.suggested_canonical != NO_MATCH
    ):
        suggestion.suggested_canonical = NO_MATCH
        suggestion.confidence = 0.0
    return suggestion


def suggest_aliases(
    corp_code: str,
    year: int,
    agent_factory=None,
    data_dir: Path | None = None,
    canonical_path: Path = CANONICAL_PATH,
    limit_accounts: int = 30,
) -> dict:
    """미매핑 계정에 별칭 제안(제안만, 디스크 미기록). 무키/실패는 graceful.

    반환: {status, result: AliasSuggestionResult|None, latency_s, message}
    """

    if agent_factory is None and not settings.openai_api_key:
        return {"status": "skipped", "message": "OPENAI_API_KEY 미설정", "result": None}

    accounts = unmapped_accounts(corp_code, year, data_dir)[:limit_accounts]
    if not accounts:
        return {
            "status": "ok",
            "message": "무표준코드 미매핑 계정 없음",
            "result": AliasSuggestionResult(corp_code=corp_code, year=str(year)),
        }

    specs = load_canonical_specs(canonical_path)
    agent = (agent_factory or build_alias_agent)()
    # 회사당 1회 배치 호출: 모든 미매핑 계정을 한 프롬프트에(계정당 후보 목록 동봉).
    # 키는 (정규화 라벨, sj_div) 복합 — 동명이표(BS·IS 같은 라벨) 덮어쓰기 방지 +
    # LLM이 alias를 미세 변형(공백·전각)해도 매칭되도록 normalize_label로 흡수.
    cand_map: dict[tuple[str, str], list[str]] = {}
    lines = [
        "다음은 한 회사의 무표준코드 미매핑 계정 목록이다. 각 계정을 그 계정의 후보 안에서만 분류하라.",
        "suggestions 배열로 모든 계정을 반환하고, 각 항목 alias에는 아래 라벨을 그대로 적는다.\n",
    ]
    for idx, acct in enumerate(accounts, 1):
        candidates = candidate_canonicals(acct["alias"], acct["sj_div"], specs)
        cand_map[(normalize_label(acct["alias"]), acct["sj_div"])] = candidates
        lines.append(
            f"[{idx}] 라벨: {acct['alias']} | 표: {acct['sj_div']} | 금액(절대): {acct['amount']:.0f}"
        )
        lines.append(f"    후보: {', '.join(candidates) or '(없음)'}")
    prompt = "\n".join(lines)

    # 배치 1회 실패가 전체 계정 누락이 되지 않게: 빈 결과로 graceful 반환(result=None 금지 — 호출부 방어).
    empty = AliasSuggestionResult(corp_code=corp_code, year=str(year))
    started = time.monotonic()
    try:
        output = agent.run_sync(prompt).output
    except Exception as exc:  # noqa: BLE001 — 온보딩은 LLM 오류를 안내로 흡수
        return {"status": "error", "message": f"{type(exc).__name__}: {exc}", "result": empty}

    raw_suggestions = getattr(output, "suggestions", None) or []
    suggestions: list[AliasSuggestion] = []
    for s in raw_suggestions:
        key = (normalize_label(s.alias), s.sj_div)
        if key not in cand_map:  # sj_div 우선 매칭
            # LLM이 sj_div를 비웠거나 틀린 경우 라벨만으로 보조 매칭
            alt = [k for k in cand_map if k[0] == normalize_label(s.alias)]
            if not alt:
                continue  # 입력에 없던 alias는 환각 — 버린다
            key = alt[0]
            s.sj_div = key[1]
        suggestions.append(_anchor(s, cand_map[key]))
    return {
        "status": "ok",
        "message": "",
        "latency_s": round(time.monotonic() - started, 2),
        "result": AliasSuggestionResult(
            corp_code=corp_code, year=str(year), suggestions=suggestions
        ),
    }


def to_alias_additions(
    result: AliasSuggestionResult, min_confidence: float = 0.7
) -> list[dict[str, str]]:
    """신뢰도 임계 이상·非기타 제안만 quirk alias_additions 형태로 변환(append는 사람 몫)."""

    out: list[dict[str, str]] = []
    for s in result.suggestions:
        if s.suggested_canonical == NO_MATCH or s.confidence < min_confidence:
            continue
        out.append({"canonical": s.suggested_canonical, "alias": s.alias})
    return out
