"""전과정 파이프라인 실측 — 수집→정규화→온보딩→Phase1→Phase2.

실제 회사 1개를 DART 수집부터 Phase2 카드까지 운영 경로 그대로 실행하고, 단계별
시간·LLM 토큰·비용을 실측한다. 회사·연도는 인자(아래 상수 또는 CLI argv)로 받는다
(§3: 분석연도·corp 리터럴로 계산 구동 금지 — 윈도우는 target 연도에서 도출).

LLM 비용 캡처: pydantic_ai.Agent.run/run_sync 를 하니스에서 래핑해 호출마다 토큰을
단계 태그와 함께 누적한다(운영 코드 무수정). 모든 관점·반박·온보딩 LLM 호출이 잡힌다.

단가 가정: 입력 $2.5/1M · 출력 $10/1M · ₩1,380/$ (gpt-5.4 실단가 미확정 — repo 일관 가정).

실행: PYTHONPATH=. uv run python data/backtest/_e2e_measure.py [corp_code] [year]
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import pydantic_ai

# ── 측정 대상(인자화) ─────────────────────────────────────────────────────────
CORP = sys.argv[1] if len(sys.argv) > 1 else "00112457"  # 소형·비금융(자산 1114억)
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
YEARS = tuple(range(YEAR - 3, YEAR + 1))  # 4년 윈도우는 target에서 도출(리터럴 아님)

# ── 단가 가정 ────────────────────────────────────────────────────────────────
USD_IN, USD_OUT, PERM, KRW = 2.5, 10.0, 1_000_000, 1380

OUT_MD = Path(f"data/backtest/_E2E_MEASURE_{CORP}_{YEAR}.md")
OUT_JSON = Path(f"data/backtest/_E2E_MEASURE_{CORP}_{YEAR}.json")
OUT_CARDS = Path(f"data/backtest/_E2E_MEASURE_{CORP}_{YEAR}_cards.md")


def cost_krw(inp: int, out: int) -> float:
    return ((inp * USD_IN + out * USD_OUT) / PERM) * KRW


# ── LLM usage 캡처(운영 경로 무수정) ──────────────────────────────────────────
CURRENT_STAGE = "?"
USAGE_ROWS: list[dict] = []
_orig_run = pydantic_ai.Agent.run


def _usage_of(result):
    """pydantic_ai 버전차 흡수: usage가 property(신)거나 method(구) 둘 다 지원."""
    u = getattr(result, "usage", None)
    return u() if callable(u) else u


def _extract(usage) -> tuple[int, int, int]:
    inp = getattr(usage, "request_tokens", None) or getattr(usage, "input_tokens", None) or 0
    out = getattr(usage, "response_tokens", None) or getattr(usage, "output_tokens", None) or 0
    tot = getattr(usage, "total_tokens", None) or (inp + out)
    return int(inp), int(out), int(tot)


def _record(result, latency: float) -> None:
    inp, out, tot = _extract(_usage_of(result))
    USAGE_ROWS.append(
        {
            "stage": CURRENT_STAGE,
            "in": inp,
            "out": out,
            "total": tot,
            "latency_s": round(latency, 2),
        }
    )


async def _patched_run(self, *args, **kwargs):
    t0 = time.perf_counter()
    result = await _orig_run(self, *args, **kwargs)
    _record(result, time.perf_counter() - t0)
    return result


# run_sync 는 내부적으로 run 을 호출하므로 run 만 패치한다(이중 카운트 방지).
pydantic_ai.Agent.run = _patched_run

# ── 운영 진입점(패치 후 임포트) ───────────────────────────────────────────────
from config.settings import settings  # noqa: E402
from src.collect.spike import collect_company_years  # noqa: E402
from src.normalize.onboarding_gate import run_gate  # noqa: E402
from src.normalize.spike import normalize_company_years  # noqa: E402
from src.report.alias_suggest import suggest_aliases  # noqa: E402
from src.report.card_pipeline import build_suspicion_cards  # noqa: E402
from src.report.company_report import build_company_report  # noqa: E402

HOLISTIC_PROMPT_PATH = Path("data/backtest/_HOLISTIC_AUDIT_PROMPT.md")

STAGES: list[dict] = []  # {name, time_s, status, detail}


def _stage(name: str, fn):
    """단계 실행 + 시간 측정. 예외는 결과로 흡수(부분 실패도 리포트 생성)."""
    global CURRENT_STAGE
    CURRENT_STAGE = name
    t0 = time.perf_counter()
    status, detail = "ok", {}
    try:
        detail = fn() or {}
    except Exception as exc:  # noqa: BLE001 — 단계 오류를 결과로 기록(다음 단계 계속)
        status = "error"
        detail = {"error": f"{type(exc).__name__}: {exc}"}
    elapsed = time.perf_counter() - t0
    STAGES.append({"name": name, "time_s": round(elapsed, 2), "status": status, "detail": detail})
    print(f"[{name}] {status} · {elapsed:.1f}s · {detail}", flush=True)
    return detail


# ── S7 청크선별(dashboard.onboarding 인라인 — streamlit 의존 회피) ────────────
def _run_s7() -> dict:
    from src.collect.opendart import DartCollector
    from src.notes.report_parts import extract_parts
    from src.report.review_chunks import persist_review_chunks, select_review_chunks

    collector = DartCollector()
    report = collector.annual_report(CORP, YEAR)
    if report is None:
        return {"status": "absent", "message": "사업보고서 원문 미제공", "chunks": 0}
    parts = extract_parts(collector.document(report.rcept_no))
    result = select_review_chunks(parts, CORP, str(YEAR))
    if result["status"] == "ok" and result.get("selection") is not None:
        persist_review_chunks(CORP, str(YEAR), result["selection"])
        return {
            "status": "ok",
            "chunks": len(result["selection"].chunks),
            "input_chars": result.get("input_chars"),
            "usage": result.get("usage"),
        }
    return {"status": result["status"], "message": result.get("message", ""), "chunks": 0}


# ── G6 홀리스틱(dashboard.onboarding 인라인) ─────────────────────────────────
def _run_g6(gate: dict) -> dict:
    dump_path = (gate.get("G6_dump") or {}).get("dump_path")
    if not dump_path or not Path(dump_path).exists():
        return {"status": "skipped", "message": "G6 dump 없음"}
    if not settings.openai_api_key:
        return {"status": "skipped", "message": "OPENAI_API_KEY 미설정"}
    lens_prompt = (
        HOLISTIC_PROMPT_PATH.read_text(encoding="utf-8") if HOLISTIC_PROMPT_PATH.exists() else ""
    )
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
    from pydantic_ai.providers.openai import OpenAIProvider

    model = OpenAIModel(
        settings.openai_model, provider=OpenAIProvider(api_key=settings.openai_api_key)
    )
    ms = OpenAIModelSettings(timeout=settings.openai_timeout_seconds)
    if settings.openai_reasoning_effort:
        ms["openai_reasoning_effort"] = settings.openai_reasoning_effort
    agent = Agent(model, system_prompt=lens_prompt, model_settings=ms, retries=1)
    result = agent.run_sync(Path(dump_path).read_text(encoding="utf-8"))
    return {"status": "ok", "findings_chars": len(str(result.output))}


def _aggregate() -> dict:
    by_stage: dict[str, dict] = {}
    for row in USAGE_ROWS:
        agg = by_stage.setdefault(row["stage"], {"calls": 0, "in": 0, "out": 0})
        agg["calls"] += 1
        agg["in"] += row["in"]
        agg["out"] += row["out"]
    total_in = sum(r["in"] for r in USAGE_ROWS)
    total_out = sum(r["out"] for r in USAGE_ROWS)
    return {
        "by_stage": by_stage,
        "total_in": total_in,
        "total_out": total_out,
        "total_calls": len(USAGE_ROWS),
        "total_cost_krw": round(cost_krw(total_in, total_out), 1),
    }


def _write_report(results: dict) -> None:
    agg = results["llm"]
    total_time = sum(s["time_s"] for s in STAGES)
    lines = [
        f"# 전과정 파이프라인 실측 — {results['company_name']} ({CORP}/{YEAR})",
        "",
        f"- 윈도우: {list(YEARS)} · 측정일: {results['measured_at']}",
        f"- 단가 가정: 입력 ${USD_IN}/1M · 출력 ${USD_OUT}/1M · ₩{KRW}/$ (gpt-5.4 실단가 미확정)",
        f"- 모델: {settings.openai_model} · reasoning_effort={settings.openai_reasoning_effort or '(미설정)'}",
        "",
        "## 단계별 시간",
        "",
        "| 단계 | 시간(s) | 상태 | 핵심 결과 |",
        "|---|---:|---|---|",
    ]
    for s in STAGES:
        d = s["detail"]
        key = (
            d.get("error")
            or d.get("summary")
            or json.dumps(
                {k: v for k, v in d.items() if k not in ("error", "summary")}, ensure_ascii=False
            )
        )
        lines.append(f"| {s['name']} | {s['time_s']} | {s['status']} | {key[:90]} |")
    lines.append(f"| **합계** | **{total_time:.1f}** | | |")

    lines += [
        "",
        "## LLM 토큰·비용 (단계별)",
        "",
        "| 단계 | 호출 | 입력토큰 | 출력토큰 | 비용(₩) |",
        "|---|---:|---:|---:|---:|",
    ]
    for stage, a in agg["by_stage"].items():
        lines.append(
            f"| {stage} | {a['calls']} | {a['in']:,} | {a['out']:,} | "
            f"{cost_krw(a['in'], a['out']):,.1f} |"
        )
    lines.append(
        f"| **합계** | **{agg['total_calls']}** | **{agg['total_in']:,}** | "
        f"**{agg['total_out']:,}** | **{agg['total_cost_krw']:,.1f}** |"
    )

    lines += [
        "",
        "## 산출물 요약",
        "",
        f"- 게이트 통과: {results.get('gate_passed')}",
        f"- S7 검토관심 청크: {results.get('s7_chunks')}건",
        f"- Phase1 review_queue: {results.get('queue_len')}건 · account_level_series: {results.get('series_len')}행",
        f"- Phase2 계정카드: {results.get('account_cards')}건 · 회사레벨카드: {results.get('company_cards')}건 · 반박 entries: {results.get('rebuttal_entries')}",
        f"- Phase2 카드 markdown: `{OUT_CARDS.name}`",
        "",
        f"**총 소요 {total_time:.1f}초 · 총 비용 ₩{agg['total_cost_krw']:,.1f} · LLM 호출 {agg['total_calls']}회**",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    from datetime import datetime

    print(f"=== 전과정 실측: {CORP}/{YEAR} 윈도우 {list(YEARS)} ===", flush=True)

    _stage("collect", lambda: _collect_detail(collect_company_years(CORP, YEARS)))
    _stage("normalize", lambda: _normalize_detail(normalize_company_years(CORP, YEARS)))
    gate = _stage("onboarding_gate", lambda: run_gate(CORP, str(YEAR)))
    _stage("onboarding_s7", _run_s7)
    _stage("onboarding_alias", lambda: _alias_detail(suggest_aliases(CORP, YEAR)))
    _stage("onboarding_g6", lambda: _run_g6(gate))

    report_holder: dict = {}

    def _phase1() -> dict:
        report = build_company_report(CORP, list(YEARS))
        report_holder["report"] = report
        return {
            "company_name": report.get("company_name"),
            "queue_len": len(report.get("review_queue", [])),
            "series_len": len(report.get("account_level_series", [])),
            "target_year": report.get("target_year"),
        }

    p1 = _stage("phase1_report", _phase1)

    def _phase2() -> dict:
        report = report_holder.get("report")
        if not report:
            return {"error": "phase1 report 없음 — phase2 생략"}
        result = asyncio.run(build_suspicion_cards(report, run_llm=True))
        OUT_CARDS.write_text(result.get("rendered", ""), encoding="utf-8")
        return {
            "account_cards": len(result.get("account_cards", [])),
            "company_cards": len(result.get("company_cards", [])),
            "rebuttal_entries": result.get("rebuttal_entries", 0),
            "grounded": len(result.get("grounded", [])),
            "dropped": len(result.get("dropped", [])),
            "rendered_chars": len(result.get("rendered", "")),
        }

    p2 = _stage("phase2_cards", _phase2)

    llm = _aggregate()
    s7 = next((s["detail"] for s in STAGES if s["name"] == "onboarding_s7"), {})
    results = {
        "measured_at": datetime.now().isoformat(timespec="seconds"),
        "company_name": p1.get("company_name") or CORP,
        "gate_passed": gate.get("gate_passed"),
        "s7_chunks": s7.get("chunks"),
        "queue_len": p1.get("queue_len"),
        "series_len": p1.get("series_len"),
        "account_cards": p2.get("account_cards"),
        "company_cards": p2.get("company_cards"),
        "rebuttal_entries": p2.get("rebuttal_entries"),
        "llm": llm,
        "stages": STAGES,
        "usage_rows": USAGE_ROWS,
    }
    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_report(results)

    print("\n=== 요약 ===", flush=True)
    print(f"총 소요 {sum(s['time_s'] for s in STAGES):.1f}초", flush=True)
    print(
        f"총 비용 ₩{llm['total_cost_krw']:,.1f} (입력 {llm['total_in']:,} · 출력 {llm['total_out']:,} 토큰 · {llm['total_calls']}회)",
        flush=True,
    )
    print(f"리포트: {OUT_MD}", flush=True)


def _collect_detail(summary: dict) -> dict:
    if summary.get("status") != "ok":
        return {"error": f"수집 실패: {summary.get('reason') or summary.get('status')}"}
    rows = 0
    for _y, ys in (summary.get("years") or {}).items():
        for _fs, fsd in (ys.get("financial_statements") or {}).items():
            rows += int(fsd.get("rows", 0))
    return {"fs_rows_total": rows, "years": list((summary.get("years") or {}).keys())}


def _normalize_detail(result: dict) -> dict:
    rep = result.get("report") or {}
    return {
        "db_years": list((result.get("db_paths") or {}).keys()),
        "summary": str(rep)[:80] if rep else "",
    }


def _alias_detail(result: dict) -> dict:
    res = result.get("result")
    n = len(getattr(res, "suggestions", []) or []) if res is not None else 0
    return {"status": result.get("status"), "suggestions": n}


if __name__ == "__main__":
    main()
