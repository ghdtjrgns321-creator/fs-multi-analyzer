"""힌트 train 8사 선정 — 무표준코드(ph) ≥10 회사 중 8셀(규모×금융×양식) 층화.

오답 수집이 목적이라 ph 많은 회사를 가중(셀별 상위 절반에서 seed 랜덤). 검증 4사 corp 전부 제외,
한 corp 중복 방지. 신규 오답 유형 수집을 위한 다양성 확보.

실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_hint_select.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

POOL = Path("data/backtest/_p1e2e_pool.jsonl")
OUT = Path("data/backtest/_p1e2e_hint_sample.json")

P75, P50 = 964_200_062_868, 256_070_415_241
OLD = ("2015", "2016", "2017", "2018")
NEW = ("2022", "2023", "2024", "2025")
EXCLUDE_CORP = {"00110893", "00125521", "00112457", "00108649"}  # 검증 4사 corp 전부
MIN_PH = 10
SEED = 20260619


def big(o):
    return o["asset"] and o["asset"] >= P75


def small(o):
    return o["asset"] and 0 < o["asset"] <= P50


def match(o, size, fin, g) -> bool:
    if o["corp"] in EXCLUDE_CORP or not o.get("note") or o["placeholder"] < MIN_PH:
        return False
    if bool(o["fin"]) != fin:
        return False
    if g == "신" and o["year"] not in NEW:
        return False
    if g == "구" and o["year"] not in OLD:
        return False
    if size == "대" and not big(o):
        return False
    if size == "소" and not small(o):
        return False
    return True


def main() -> None:
    pool = [json.loads(x) for x in POOL.read_text(encoding="utf-8").splitlines()]
    cells = {}
    for size in ("대", "소"):
        for fin in (True, False):
            for g in ("신", "구"):
                cells[f"{size}{'금융' if fin else '비금융'}{g}"] = (size, fin, g)

    rng = random.Random(SEED)
    used_corp = set()
    sel = []
    for name, (size, fin, g) in cells.items():
        cands = [o for o in pool if match(o, size, fin, g) and o["corp"] not in used_corp]
        print(f"{name}: 후보 {len(cands)}")
        if not cands:
            print("  ⚠ 빈 셀")
            continue
        top = sorted(cands, key=lambda o: -o["placeholder"])[: max(3, len(cands) // 2)]
        pick = rng.choice(top)
        used_corp.add(pick["corp"])
        sel.append({"cell": name, **pick})

    OUT.write_text(json.dumps(sel, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n선정 {len(sel)}/8:")
    for s in sel:
        print(
            f"  [{s['cell']}] {s['corp']}/{s['year']} ph={s['placeholder']} "
            f"{'금융' if s['fin'] else '비금융'} 자산={s['asset']:,.0f}"
        )


if __name__ == "__main__":
    main()
