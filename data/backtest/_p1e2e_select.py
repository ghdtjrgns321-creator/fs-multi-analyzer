"""P1 E2E 검증 0단계 — 4셀 층화 샘플 선정(규모×금융업×양식세대 직교 대비).

8셀(2×2×2) 중 3축 각각에서 2:2 균형이 되는 4셀을 골라, 고정 seed로 셀당 1 회사연도.
주석 보유(정성검증 입력) + 자산총계 보유를 필수로 건다. 재현 위해 후보 정렬 후 seed 추출.

실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_select.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

PROF = Path("data/backtest/_p1e2e_profile.jsonl")
OUT = Path("data/backtest/_p1e2e_sample.json")

P75 = 964_200_062_868  # 대형 경계(자산총계 p75)
P50 = 256_070_415_241  # 소형 경계(자산총계 p50)
OLD = ("2015", "2016", "2017")  # 구 양식세대(IFRS 초기)
NEW = ("2023", "2024", "2025")  # 신 양식세대
SEED = 20260617


def big(o: dict) -> bool:
    return bool(o["asset"]) and o["asset"] >= P75


def small(o: dict) -> bool:
    return bool(o["asset"]) and 0 < o["asset"] <= P50


def ok(o: dict) -> bool:
    return bool(o["note"])  # 주석 보유 필수(정성검증 입력)


CELLS = {
    "대형·금융·신양식": lambda o: big(o) and o["fin"] and o["year"] in NEW and ok(o),
    "대형·비금융·구양식": lambda o: big(o) and not o["fin"] and o["year"] in OLD and ok(o),
    "소형·비금융·신양식": lambda o: small(o) and not o["fin"] and o["year"] in NEW and ok(o),
    "소형·금융·구양식": lambda o: small(o) and o["fin"] and o["year"] in OLD and ok(o),
}


def main() -> None:
    prof = [json.loads(line) for line in PROF.read_text(encoding="utf-8").splitlines()]
    rng = random.Random(SEED)
    sel: list[dict] = []
    for name, pred in CELLS.items():
        cands = sorted((o for o in prof if pred(o)), key=lambda o: (o["corp"], o["year"]))
        print(f"{name}: 후보 {len(cands)}")
        if not cands:
            print("  ⚠ 후보 0 — 셀 완화 필요")
            continue
        pick = rng.choice(cands)
        sel.append({"cell": name, **pick})

    OUT.write_text(json.dumps(sel, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n선정 {len(sel)}/4:")
    for s in sel:
        print(
            f"  [{s['cell']}] {s['corp']}/{s['year']} 자산={s['asset']:,.0f} "
            f"{'금융' if s['fin'] else '비금융'} 행={s['rows']}"
        )


if __name__ == "__main__":
    main()
