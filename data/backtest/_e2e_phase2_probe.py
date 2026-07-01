"""삼성 Phase2 관점 0건 원인 진단 — 삼켜진 예외를 드러낸다.

run_structured_perspective의 `except Exception: return deferred`가 진짜 실패를 가린다.
여기서는 numeric 관점 1개를 직접 호출하되 예외를 그대로 출력하고, 프롬프트 크기(chars)도 잰다.

실행: PYTHONPATH=. uv run python data/backtest/_e2e_phase2_probe.py [corp] [year]
"""

from __future__ import annotations

import asyncio
import json
import sys

CORP = sys.argv[1] if len(sys.argv) > 1 else "00126380"
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
YEARS = list(range(YEAR - 3, YEAR + 1))

from src.report.company_report import build_company_report  # noqa: E402
from src.report.perspective_runner import (  # noqa: E402
    ALL_PERSPECTIVES,
    build_structured_perspective_agent,
    collect_perspective_materials,
)


async def main() -> None:
    report = build_company_report(CORP, YEARS)
    print(
        f"company={report.get('company_name')} queue={len(report.get('review_queue', []))} "
        f"series={len(report.get('account_level_series', []))}"
    )
    materials = collect_perspective_materials(report)

    # 관점별 프롬프트 크기 측정
    print("\n=== 관점별 material_board 프롬프트 크기 ===")
    for name in ALL_PERSPECTIVES:
        board = materials.get(name, {})
        prompt = json.dumps({"perspective": name, "material_board": board}, ensure_ascii=False)
        print(f"  {name:10s} prompt_chars={len(prompt):>9,}  (~tokens≈{len(prompt) // 3:>8,})")

    # numeric 관점 1개를 직접 호출 — 예외를 삼키지 않고 출력
    print("\n=== numeric 관점 직접 호출 (예외 노출) ===")
    name = "numeric"
    board = materials.get(name, {})
    prompt = json.dumps({"perspective": name, "material_board": board}, ensure_ascii=False)
    agent = build_structured_perspective_agent(name)
    try:
        result = await agent.run(prompt)
        out = result.output
        print(f"  OK status={out.status} suspicions={len(out.suspicions)}")
    except Exception as exc:  # noqa: BLE001 — 진단 목적
        print(f"  EXCEPTION {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
