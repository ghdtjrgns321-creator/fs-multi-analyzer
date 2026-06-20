"""D-A 잔여 측정: 현재 config 등록 account_id vs 군집별 미분류 잔여(읽기전용).

재현: PYTHONPATH=. uv run python data/backtest/_da_remaining.py
입력: data/backtest/_da_cluster.json(원본 전수 미분류 군집) + 현재 config.
출력: 군집별 등록종/잔여종/잔여행수. 신규개념후보만(타표문반복 제외).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from src.normalize.config import load_canonical_accounts

acc_cfg = load_canonical_accounts(Path("config/canonical_accounts.yaml"))
reg_ids: set[str] = set()
for a in acc_cfg:
    for aid in getattr(a, "account_ids", []) or []:
        reg_ids.add(aid)
# ifrs_ ≡ ifrs-full_ 통일(운영 mapper와 동일)
norm = set(reg_ids)
for aid in list(reg_ids):
    if aid.startswith("ifrs-full_"):
        norm.add("ifrs_" + aid[len("ifrs-full_") :])
print("config 등록 account_id 수(변형 포함):", len(norm))

d = json.load(open("data/backtest/_da_cluster.json", encoding="utf-8"))
accounts = d["accounts"]

agg: dict[str, dict[str, int]] = defaultdict(
    lambda: {"reg_n": 0, "reg_rows": 0, "rem_n": 0, "rem_rows": 0}
)
remaining_top: dict[str, list] = defaultdict(list)
for a in accounts:
    if a["flag"] != "신규개념후보":
        continue
    cl = a["cluster"]
    rows = a["n"]
    aid = a["account_id"]
    aid2 = ("ifrs_" + aid[len("ifrs-full_") :]) if aid.startswith("ifrs-full_") else aid
    registered = (aid in norm) or (aid2 in norm)
    g = agg[cl]
    if registered:
        g["reg_n"] += 1
        g["reg_rows"] += rows
    else:
        g["rem_n"] += 1
        g["rem_rows"] += rows
        remaining_top[cl].append((rows, a["n_companies"], aid, a.get("labels", a.get("label", ""))))

order = sorted(agg.items(), key=lambda kv: -(kv[1]["reg_rows"] + kv[1]["rem_rows"]))
print()
header = f"{'군집':34s} {'등록/총':>9} {'잔여종':>5} {'잔여행수':>9} {'잔여%':>6}"
print(header)
print("-" * 74)
tot_rem_rows = 0
hi_value = []
for cl, g in order:
    tot = g["reg_n"] + g["rem_n"]
    totrows = g["reg_rows"] + g["rem_rows"]
    pct = g["rem_rows"] / totrows * 100 if totrows else 0
    tot_rem_rows += g["rem_rows"]
    mark = "[DONE]" if g["rem_n"] == 0 else ("[PART]" if g["reg_n"] > 0 else "[NONE]")
    print(
        f"{mark} {cl:31s} {g['reg_n']:>4}/{tot:<4} {g['rem_n']:>5} {g['rem_rows']:>9} {pct:>5.0f}%"
    )
print("-" * 74)
print("총 잔여 신규개념 행수:", tot_rem_rows)

# 잔여가 큰 군집의 top 미등록 account_id (등록 우선순위)
print("\n=== 잔여 상위 군집의 미등록 account_id (행수순 top5) ===")
big = sorted(agg.items(), key=lambda kv: -kv[1]["rem_rows"])
for cl, g in big[:8]:
    if g["rem_rows"] == 0:
        continue
    items = sorted(remaining_top[cl], reverse=True)[:5]
    print(f"\n[{cl}] 잔여 {g['rem_n']}종 / {g['rem_rows']}행")
    for rows, ncomp, aid, lab in items:
        lab0 = lab[0] if isinstance(lab, list) and lab else lab
        print(f"   {rows:>6}행 {ncomp:>4}사  {aid:55s} {lab0}")
