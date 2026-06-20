"""IS/CIS 손익 미등록 표준 concept 범위 측정(D-A를 IS/CIS로 확장하기 위한 근거).

_da_cluster.json(전수 미분류 군집) 중 IS/CIS 손익·비용 군집의 현재 미등록 + 보편성(회사수).
"""

from __future__ import annotations

import json
from pathlib import Path

from src.normalize.config import load_canonical_accounts

PREFIXES = ("ifrs-full_", "ifrs_", "dart_")


def stem(s: str) -> str:
    for p in PREFIXES:
        if s.startswith(p):
            return s[len(p) :].lower()
    return s.lower()


acc = load_canonical_accounts(Path("config/canonical_accounts.yaml"))
reg = set()
for a in acc:
    for aid in a.account_ids:
        reg.add(aid)
        reg.add(stem(aid))

d = json.load(open("data/backtest/_da_cluster.json", encoding="utf-8"))
# IS/CIS 시작 군집(손익·비용·세금·EPS 등)
iscis = [
    a
    for a in d["accounts"]
    if a["flag"] == "신규개념후보"
    and a["cluster"].split(" / ")[0] in ("IS", "CIS")
    and a["account_id"] not in reg
    and stem(a["account_id"]) not in reg
]
print(f"IS/CIS 미등록 신규개념: {len(iscis)}종")
for thr in (200, 150, 100, 50, 30, 20, 10, 1):
    sel = [a for a in iscis if a["n_companies"] >= thr]
    rows = sum(a["n"] for a in sel)
    print(f"  ≥{thr:>3}사: {len(sel):>4}종  {rows:>7}행")

print("\n=== ≥50사 미등록 IS/CIS concept (회사수순) ===")
strong = sorted([a for a in iscis if a["n_companies"] >= 50], key=lambda a: -a["n_companies"])
for a in strong:
    labs = a.get("labels") or [a.get("label", "")]
    print(f"  {a['n_companies']:>4}사 {a['n']:>5}행  {a['account_id'][:46]:46s} {labs[0][:20]}")
