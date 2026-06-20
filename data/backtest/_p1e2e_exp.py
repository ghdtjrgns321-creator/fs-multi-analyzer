"""온보딩 alias 개선 실험 — ②배치 ③힌트+새샘플 ①high. 비용 ₩4,500 hard-stop.

단일변수: baseline(계정당·high끔, 기존 _p1e2e_alias_log.json) 대비
  ① 계정당 + reasoning high
  ② 배치(회사당1) + high끔
  ③ 배치 + high끔 + 회계힌트, 새 층화샘플(seed 변경)
매 LLM 호출마다 usage 실측 누적, cost_krw 출력, HARD 도달 시 즉시 중단·저장.

실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_exp.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from config.settings import settings
from src.report.alias_suggest import (
    NO_MATCH,
    SYSTEM_PROMPT,
    AliasSuggestion,
    AliasSuggestionResult,
    candidate_canonicals,
    load_canonical_specs,
    unmapped_accounts,
)

PROFILE = Path("data/backtest/_p1e2e_profile.jsonl")
LOG = Path("data/backtest/_p1e2e_exp_log.json")
SAMPLE4 = [("00110893", 2024), ("00125521", 2017), ("00112457", 2024), ("00108649", 2015)]

# 단가 가정(USD/100만 토큰, 환율 ₩1,380). LLM_MODEL_COMPARE.md 중간 가정값.
USD_IN, USD_OUT, PERM, KRW = 2.5, 10.0, 1_000_000, 1380
HARD_KRW = 4500.0

HINT = (
    "\n\n[회계 구분 주의 — 표면 글자가 비슷해도 실질이 다르면 candidate에 그 실질이 없을 수 있다]\n"
    "- 발생원가(제조원가)와 비용화(매출원가)는 다르다.\n"
    "- 잔액(기초/기말 재고액)과 변동(재고의 변동)은 다르다.\n"
    "- 소계 범위가 다르면(예: 당좌자산 vs 유동자산) 같은 계정이 아니다.\n"
    "- 순증감과 단방향(증가/감소)을 구분하라. 매입액과 매출원가를 혼동하지 마라.\n"
    "맞는 candidate가 없으면 억지로 고르지 말고 '기타 중요 계정'으로 둔다."
)

spent = {"in": 0, "out": 0}


def cost_krw() -> float:
    return ((spent["in"] * USD_IN + spent["out"] * USD_OUT) / PERM) * KRW


def _accumulate(result) -> None:
    u = result.usage()
    spent["in"] += getattr(u, "request_tokens", 0) or getattr(u, "input_tokens", 0) or 0
    spent["out"] += getattr(u, "response_tokens", 0) or getattr(u, "output_tokens", 0) or 0


def _model(effort: str | None):
    model = OpenAIModel(
        settings.openai_model, provider=OpenAIProvider(api_key=settings.openai_api_key)
    )
    ms = OpenAIModelSettings(timeout=settings.openai_timeout_seconds)
    if effort:
        ms["openai_reasoning_effort"] = effort
    return model, ms


def acct_agent(effort: str | None = None) -> Agent:
    model, ms = _model(effort)
    return Agent(
        model,
        output_type=AliasSuggestion,
        system_prompt=SYSTEM_PROMPT,
        model_settings=ms,
        retries=2,
    )


def batch_agent(effort: str | None = None, hint: bool = False) -> Agent:
    model, ms = _model(effort)
    sys = SYSTEM_PROMPT + (HINT if hint else "")
    return Agent(
        model, output_type=AliasSuggestionResult, system_prompt=sys, model_settings=ms, retries=2
    )


def batch_prompt(accts: list[dict], specs: dict) -> tuple[str, dict]:
    lines = [
        "다음은 한 회사의 미매핑 계정 목록이다. 각 계정을 그 계정의 candidate 안에서만 분류하라.",
        "계정마다 독립이며 다른 계정의 후보를 쓰지 마라. suggestions 배열로 전부 반환.\n",
    ]
    cand_map: dict = {}
    for i, a in enumerate(accts, 1):
        cands = candidate_canonicals(a["alias"], a["sj_div"], specs)
        cand_map[a["alias"]] = cands
        lines.append(f"[{i}] 라벨: {a['alias']} | 표: {a['sj_div']} | 금액: {a['amount']:.0f}")
        lines.append(f"    후보: {', '.join(cands) or '(없음)'}")
    return "\n".join(lines), cand_map


def anchor_one(canonical: str, cands: list[str]) -> str:
    return canonical if (canonical in cands or canonical == NO_MATCH) else NO_MATCH


def new_sample(exclude: set, seed: int) -> list[tuple[str, int]]:
    prof = [json.loads(x) for x in PROFILE.read_text(encoding="utf-8").splitlines()]
    p75, p50 = 964_200_062_868, 256_070_415_241
    old, new = ("2015", "2016", "2017"), ("2023", "2024", "2025")

    def big(o):
        return o["asset"] and o["asset"] >= p75

    def small(o):
        return o["asset"] and 0 < o["asset"] <= p50

    cells = {
        "대형금융신": lambda o: big(o) and o["fin"] and o["year"] in new and o["note"],
        "대형비금융구": lambda o: big(o) and not o["fin"] and o["year"] in old and o["note"],
        "소형비금융신": lambda o: small(o) and not o["fin"] and o["year"] in new and o["note"],
        "소형금융구": lambda o: small(o) and o["fin"] and o["year"] in old and o["note"],
    }
    rng = random.Random(seed)
    out = []
    for pred in cells.values():
        cs = sorted(
            (o for o in prof if pred(o) and (o["corp"], o["year"]) not in exclude),
            key=lambda o: (o["corp"], o["year"]),
        )
        if cs:
            p = rng.choice(cs)
            out.append((p["corp"], int(p["year"])))
    return out


def run_batch(samples, hint, specs, label, log):
    for corp, year in samples:
        if cost_krw() > HARD_KRW:
            print(f"  [중단] 예산 도달 cost={cost_krw():.0f}", flush=True)
            return
        accts = unmapped_accounts(corp, year)[:30]
        if not accts:
            continue
        prompt, cand_map = batch_prompt(accts, specs)
        result = batch_agent(hint=hint).run_sync(prompt)
        _accumulate(result)
        sugg = [
            {
                "alias": s.alias,
                "sj_div": s.sj_div,
                "canonical": anchor_one(s.suggested_canonical, cand_map.get(s.alias, [])),
                "confidence": s.confidence,
                "reason": s.reason,
            }
            for s in result.output.suggestions
        ]
        log.append(
            {
                "stage": label,
                "corp": corp,
                "year": year,
                "n_accounts": len(accts),
                "n_suggest": len(sugg),
                "cost_krw_after": round(cost_krw(), 1),
                "suggestions": sugg,
            }
        )
        print(
            f"  [{label}] {corp}/{year} 계정{len(accts)}→제안{len(sugg)} | 누적 ₩{cost_krw():.0f}",
            flush=True,
        )


def main() -> None:
    specs = load_canonical_specs()
    log: list[dict] = []

    print("=== ② 배치 (기존4사·high끔) ===", flush=True)
    run_batch(SAMPLE4, hint=False, specs=specs, label="②batch", log=log)

    # ③ 힌트는 ②와 같은 계정(기존4사)에 힌트만 추가해 직접 비교(단일변수=힌트).
    # 새 샘플은 무표준코드 계정이 거의 없어 힌트 효과 측정 불가 → 일반화는 별도로 기록.
    print("=== ③ 힌트 (기존4사·배치·high끔·회계힌트) — ②와 동일계정 비교 ===", flush=True)
    run_batch(SAMPLE4, hint=True, specs=specs, label="③hint", log=log)
    new4 = new_sample(exclude={(c, str(y)) for c, y in SAMPLE4}, seed=20260618)
    print(f"  (참고) 새 샘플 {new4} — 무표준코드 계정 거의 없어 일반화 측정 표본 부족", flush=True)

    print("=== ① high (기존4사·계정당·reasoning high) — 예산 남는만큼 ===", flush=True)
    high_note = ""
    stopped = False
    try:
        for corp, year in SAMPLE4:
            if stopped:
                break
            accts = unmapped_accounts(corp, year)[:30]
            for a in accts:
                if cost_krw() > HARD_KRW:
                    print(f"  [중단] 예산 도달 cost={cost_krw():.0f}", flush=True)
                    stopped = True
                    break
                cands = candidate_canonicals(a["alias"], a["sj_div"], specs)
                prompt = (
                    f"라벨: {a['alias']}\n표: {a['sj_div']}\n금액(절대): {a['amount']:.0f}\n"
                    f"candidate canonical(이 안에서만 선택, 없으면 '기타 중요 계정'):\n"
                    + "\n".join(f"- {c}" for c in cands)
                )
                result = acct_agent("high").run_sync(prompt)
                _accumulate(result)
                o = result.output
                log.append(
                    {
                        "stage": "①high",
                        "corp": corp,
                        "year": year,
                        "alias": a["alias"],
                        "sj_div": a["sj_div"],
                        "canonical": anchor_one(o.suggested_canonical, cands),
                        "confidence": o.confidence,
                        "reason": o.reason,
                        "cost_krw_after": round(cost_krw(), 1),
                    }
                )
            print(f"  [①high] {corp}/{year} 까지 누적 ₩{cost_krw():.0f}", flush=True)
    except Exception as exc:  # noqa: BLE001 — high 미지원 등 API 제약을 결과로 기록
        high_note = f"{type(exc).__name__}: {str(exc)[:180]}"
        print(f"  [①high 불가] {high_note}", flush=True)

    LOG.write_text(
        json.dumps(
            {"spent": spent, "cost_krw": round(cost_krw(), 1), "high_note": high_note, "log": log},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nDONE | 입력 {spent['in']:,} 출력 {spent['out']:,} | 총 ₩{cost_krw():.0f}", flush=True)


if __name__ == "__main__":
    main()
