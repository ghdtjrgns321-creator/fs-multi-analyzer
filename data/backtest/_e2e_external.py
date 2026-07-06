"""external 관점 실검색 배선 검증 — 실 LLM+구글검색 E2E (대주 00112457).

死코드였던 external 검색 파이프라인이 카드 파이프라인에 연결됐는지 실제로 확인한다.
검색어(Gemini 생성)·검색결과 건수·status를 덤프한다.
실행: PYTHONPATH=. uv run python data/backtest/_e2e_external.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from src.report.company_report import build_company_report
from src.report.external import external_material, run_external_suspicions
from src.report.external_agentic import generate_search_keywords

CORP = sys.argv[1] if len(sys.argv) > 1 else "00112457"
OUT = Path(f"data/backtest/_E2E_EXTERNAL_{CORP}.json")


async def _run(report: dict) -> dict:
    # 검색어를 먼저 뽑아 함께 기록(어떤 검색어로 검색했는지 추적).
    try:
        keywords = await generate_search_keywords(external_material(report))
        queries = list(keywords.queries)
    except Exception as exc:
        queries = [f"검색어 생성 실패: {exc}"]

    out = await run_external_suspicions(report)
    return {
        "status": out.status,
        "queries": queries,
        "item_count": len(out.suspicions),
        "items": [
            {"desc": s.description[:200], "source_url": s.source_url, "scope": s.scope}
            for s in out.suspicions
        ],
    }


def main() -> None:
    report = build_company_report(CORP, [2021, 2022, 2023, 2024])
    payload = asyncio.run(_run(report))
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"external status: {payload['status']}")
    print(f"검색어: {payload['queries']}")
    print(f"검색결과 item: {payload['item_count']}건")
    for it in payload["items"]:
        print(f"  - {it['source_url']}  {it['desc'][:60]}")
    print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
