"""D-A 잔여를 보편성(회사수) 임계별로 분해 — 등록 범위 선택지 근거(읽기전용).

신규개념후보 중 현재 config 미등록 account_id를, 사용 회사수 임계별로 누적 집계.
'몇 개 등록하면 잔여 행수 몇 %를 커버하나'를 보여 등록 범위 의사결정을 돕는다.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.normalize.config import load_canonical_accounts

acc_cfg = load_canonical_accounts(Path("config/canonical_accounts.yaml"))
norm: set[str] = set()
for a in acc_cfg:
    for aid in getattr(a, "account_ids", []) or []:
        norm.add(aid)
        if aid.startswith("ifrs-full_"):
            norm.add("ifrs_" + aid[len("ifrs-full_") :])

d = json.load(open("data/backtest/_da_cluster.json", encoding="utf-8"))
HIGH = {
    "CF / 현금흐름조정",
    "CF / 기타금융자산",
    "CF / 현금잔액·증감·환율효과",
    "SCE / 자본구성요소",
    "BS / 기타금융자산",
    "CF / 차입·사채",
    "CF / 투자활동흐름",
    "BS / 기타금융부채",
    "BS / 자본구성요소",
    "CF / 재무활동흐름",
    "BS / 기타비금융부채",
    "CF / 비금융자산(유형·무형·재고)",
    "CF / 관계·종속기업투자",
    "BS / 기타비금융자산",
}

rem = []  # 미등록 신규개념후보
for a in d["accounts"]:
    if a["flag"] != "신규개념후보":
        continue
    aid = a["account_id"]
    aid2 = ("ifrs_" + aid[len("ifrs-full_") :]) if aid.startswith("ifrs-full_") else aid
    if aid in norm or aid2 in norm:
        continue
    rem.append(a)

rem_high = [a for a in rem if a["cluster"] in HIGH]
total_rows_all = sum(a["n"] for a in rem)
total_rows_high = sum(a["n"] for a in rem_high)
print(f"미등록 신규개념 전체: {len(rem)}종 / {total_rows_all}행")
print(f"  └ 16고가치 군집 내: {len(rem_high)}종 / {total_rows_high}행\n")

print("회사수 임계별 누적(16고가치 군집 한정) — '≥N사 쓰는 계정만 등록' 시:")
print(f"{'임계(≥N사)':>10} {'등록종수':>7} {'커버행수':>9} {'군집내잔여%':>9}")
print("-" * 44)
for thr in (300, 200, 150, 100, 50, 30, 20, 10, 5, 1):
    sel = [a for a in rem_high if a["n_companies"] >= thr]
    rows = sum(a["n"] for a in sel)
    pct = rows / total_rows_high * 100 if total_rows_high else 0
    print(f"{thr:>10} {len(sel):>7} {rows:>9} {pct:>8.0f}%")

# ≥100사 계정 = 강한 보편 후보. 군집별로 나열.
print("\n=== ≥100사 미등록 계정(강보편, 우선등록 후보) ===")
strong = sorted(
    [a for a in rem_high if a["n_companies"] >= 100],
    key=lambda a: -a["n_companies"],
)
from collections import defaultdict

bycl = defaultdict(list)
for a in strong:
    bycl[a["cluster"]].append(a)
for cl, items in sorted(bycl.items(), key=lambda kv: -len(kv[1])):
    print(f"\n[{cl}] {len(items)}종")
    for a in items:
        lab = a.get("labels", a.get("label", ""))
        lab0 = lab[0] if isinstance(lab, list) and lab else lab
        print(f"   {a['n_companies']:>4}사 {a['n']:>6}행  {a['account_id']:52s} {lab0}")
print(f"\n≥100사 강보편 미등록 합계: {len(strong)}종")
