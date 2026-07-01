"""trend(추세) 관점 재편 검증 — 실 LLM E2E (대주 00112457).

change→trend 개명 + 당해급변은 numeric 전담 + 소급재작성 삭제 후:
numeric∩trend 계정 중복률이 이전(5/8=63%)보다 떨어지는지 측정한다.
실행: PYTHONPATH=. uv run python data/backtest/_e2e_trend.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.report.card_pipeline import build_suspicion_cards
from src.report.company_report import build_company_report

CORP = "00112457"
OUT = Path(f"data/backtest/_E2E_TREND_{CORP}.json")


def main() -> None:
    report = build_company_report(CORP, [2021, 2022, 2023, 2024])
    result = asyncio.run(build_suspicion_cards(report, run_llm=True))

    by_persp: dict[str, list[str]] = {}
    scope_by_persp: dict[str, dict[str, int]] = {}
    for g in result.get("grounded", []):
        it = g.item
        d = scope_by_persp.setdefault(it.perspective, {})
        d[it.scope] = d.get(it.scope, 0) + 1
        if it.scope == "account":
            by_persp.setdefault(it.perspective, []).append(str(it.account_id))

    numeric = set(by_persp.get("numeric", []))
    trend = set(by_persp.get("trend", []))
    overlap = numeric & trend
    trend_only = trend - numeric
    rate = round(len(overlap) / len(trend), 3) if trend else None

    payload = {
        "scope_by_perspective": scope_by_persp,
        "numeric_accounts": sorted(numeric),
        "trend_accounts": sorted(trend),
        "overlap_accounts": sorted(overlap),
        "trend_only_accounts": sorted(trend_only),
        "overlap_rate": rate,  # trend 중 numeric과 겹치는 비율 (이전 0.63 대비)
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"scope 분포: {scope_by_persp}")
    print(f"numeric {len(numeric)}계정 · trend {len(trend)}계정")
    print(f"중복 {len(overlap)}계정 → 중복률 {rate} (이전 0.63)")
    print(f"trend 고유: {sorted(trend_only)}")
    print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
