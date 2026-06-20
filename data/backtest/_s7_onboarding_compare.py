"""S7 Step4 비교 — GPT(gpt-5.4) 온보딩 청크선별 실행 + 토큰·시간 실측.

입력은 내용필터된 다이제스트(data/backtest/_s7_sample/{corp}_{year}.txt = PART 추출 + III 주석
앵커단락 + V·IX·X·XI 전문). 설계대로 "통째 투입"이 아니라 검토관심 본문만 GPT에 넣는다.
같은 다이제스트를 사람(Opus)이 읽어 대조한다(별도). 외부 LLM 비용·시간을 정확히 캡처한다.

저장: data/backtest/_s7_onboarding_compare/{corp}_{year}.input.txt(복사) / .gpt.json + _summary.json
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from src.report.review_chunks import (
    ReviewChunkSelection,
    _baseline_hint,
    build_chunk_agent,
    load_review_baseline,
)

SAMPLE = Path("data/backtest/_s7_sample")
OUT = Path("data/backtest/_s7_onboarding_compare")
OUT.mkdir(parents=True, exist_ok=True)

# 다이제스트 크기 밴드(사람이 읽을 수 있고 비용 절제). 너무 작으면 빈 껍데기.
MIN_CHARS = 12_000
MAX_CHARS = 70_000
N_NEW, N_OLD = 6, 4

_HEAD = re.compile(r"### CORP (\d+)\s+YEAR (\d+)")


def _era(year: int) -> str:
    return "old" if year <= 2017 else "new"


def _gpt_select(body: str, corp: str, year: str) -> dict:
    baseline = load_review_baseline()
    prompt = (
        f"{_baseline_hint(baseline)}\n\n[대상] corp_code={corp} year={year}\n\n"
        f"[사업보고서 검토관심 본문]\n{body}"
    )
    agent = build_chunk_agent()
    started = time.perf_counter()
    result = agent.run_sync(prompt)
    latency = time.perf_counter() - started
    usage = result.usage()
    return {
        "selection": result.output,
        "input_tokens": getattr(usage, "request_tokens", 0) or 0,
        "output_tokens": getattr(usage, "response_tokens", 0) or 0,
        "latency_s": round(latency, 2),
    }


def main() -> None:
    files = sorted(SAMPLE.glob("*.txt"))
    pool = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        if not (MIN_CHARS <= len(text) <= MAX_CHARS):
            continue
        m = _HEAD.search(text)
        if not m:
            continue
        corp, year = m.group(1), int(m.group(2))
        pool.append(
            {"corp": corp, "year": year, "era": _era(year), "chars": len(text), "body": text}
        )

    pool.sort(key=lambda r: r["chars"])
    new = [p for p in pool if p["era"] == "new"][:N_NEW]
    old = [p for p in pool if p["era"] == "old"][:N_OLD]
    chosen = new + old
    print(f"선정 {len(chosen)} (신 {len(new)} / 구 {len(old)}) / pool {len(pool)}", flush=True)

    summary = []
    for b in chosen:
        corp, year = b["corp"], str(b["year"])
        (OUT / f"{corp}_{year}.input.txt").write_text(b["body"], encoding="utf-8")
        try:
            res = _gpt_select(b["body"], corp, year)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERR {corp} {year}: {type(exc).__name__}: {exc}", flush=True)
            summary.append(
                {
                    "corp": corp,
                    "year": year,
                    "era": b["era"],
                    "status": "error",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        sel: ReviewChunkSelection = res["selection"]
        (OUT / f"{corp}_{year}.gpt.json").write_text(
            json.dumps(sel.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rec = {
            "corp": corp,
            "year": year,
            "era": b["era"],
            "status": "ok",
            "input_chars": b["chars"],
            "input_tokens": res["input_tokens"],
            "output_tokens": res["output_tokens"],
            "latency_s": res["latency_s"],
            "n_chunks": len(sel.chunks),
            "types": sorted({c.disclosure_type for c in sel.chunks}),
        }
        summary.append(rec)
        print(
            f"  ok {corp} {year} {b['era']} chars={b['chars']} "
            f"in={res['input_tokens']} out={res['output_tokens']} {res['latency_s']}s "
            f"chunks={len(sel.chunks)} {rec['types']}",
            flush=True,
        )

    (OUT / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok = [r for r in summary if r["status"] == "ok"]
    if ok:
        n = len(ok)
        tin = sum(r["input_tokens"] for r in ok)
        tout = sum(r["output_tokens"] for r in ok)
        tlat = sum(r["latency_s"] for r in ok)
        print(
            f"\n[집계] ok {n}사 / 평균 in={tin // n} out={tout // n} 토큰 / "
            f"평균 {tlat / n:.1f}s / 합계 in={tin} out={tout}",
            flush=True,
        )


if __name__ == "__main__":
    main()
