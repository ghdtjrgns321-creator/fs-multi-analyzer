"""힌트 train — 7사 baseline 배치(무힌트) 제안 수집. 오답 유형 통독용.

_p1e2e_exp.py 함수 재사용. 무힌트로 돌려 오답을 드러낸다(그 오답 유형으로 힌트를 만든다).
비용 가드(HARD_KRW) 공유.

실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_hint_run.py
"""

from __future__ import annotations

import json
from pathlib import Path

from data.backtest._p1e2e_exp import (
    HARD_KRW,
    _accumulate,
    anchor_one,
    batch_agent,
    batch_prompt,
    cost_krw,
    spent,
)
from src.report.alias_suggest import load_canonical_specs, unmapped_accounts

SAMPLE = Path("data/backtest/_p1e2e_hint_sample.json")
OUT = Path("data/backtest/_p1e2e_hint_run.json")


def main() -> None:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    specs = load_canonical_specs()
    log: list[dict] = []
    for s in sample:
        if cost_krw() > HARD_KRW:
            print(f"[중단] 예산 ₩{cost_krw():.0f}", flush=True)
            break
        corp, year = s["corp"], int(s["year"])
        accts = unmapped_accounts(corp, year)[:30]
        if not accts:
            print(f"  {s['cell']} {corp}/{year} 미매핑 0 — skip", flush=True)
            continue
        prompt, cmap = batch_prompt(accts, specs)
        result = batch_agent().run_sync(prompt)  # 무힌트 baseline
        _accumulate(result)
        sugg = [
            {
                "alias": x.alias,
                "sj_div": x.sj_div,
                "canonical": anchor_one(x.suggested_canonical, cmap.get(x.alias, [])),
                "confidence": x.confidence,
                "reason": x.reason,
            }
            for x in result.output.suggestions
        ]
        log.append(
            {
                "corp": corp,
                "year": year,
                "cell": s["cell"],
                "n_accounts": len(accts),
                "suggestions": sugg,
            }
        )
        print(
            f"  {s['cell']} {corp}/{year} 계정{len(accts)}→제안{len(sugg)} | 누적 ₩{cost_krw():.0f}",
            flush=True,
        )

    OUT.write_text(
        json.dumps(
            {"spent": spent, "cost_krw": round(cost_krw(), 1), "log": log},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nDONE | 입력 {spent['in']:,} 출력 {spent['out']:,} | ₩{cost_krw():.0f}", flush=True)


if __name__ == "__main__":
    main()
