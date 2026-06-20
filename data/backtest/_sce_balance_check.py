"""SCE 부호 정규화 검산 — 기초자본 + Σleaf변동 = 기말(자본총계)이 맞는지.

change_role(begin/total/subtotal/restated_begin/leaf) 기반으로 leaf만 합산한다(N1/D5 라운드1).
소계·조정후개시(스톡)를 합산하면 이중계상이라 검산이 깨진다. §F(_p1_company_review.py)와 동일한
src.normalize.sce.sce_balance helper를 써서 두 경로의 검산 로직을 일치시킨다.

재현: PYTHONPATH=. uv run python data/backtest/_sce_balance_check.py
"""

from __future__ import annotations

from pathlib import Path

from src.normalize.pipeline import sce_components_company_year
from src.normalize.sce import sce_balance

M = 1_000_000

# 금융형(00117267)·대형(00120526) 양쪽 + 기존 세토(00159616). 라운드1 검산 FAIL 분해 대상.
CASES = [
    ("삼성생명(금융형)", "00117267", "2025"),
    ("롯데지주(대형)", "00120526", "2024"),
    ("롯데지주(대형)", "00120526", "2025"),
    ("세토피아", "00159616", "2018"),
    ("별도전용", "00134176", "2023"),
    ("blank고비중", "00258689", "2023"),
]

for name, corp, year in CASES:
    df = sce_components_company_year(corp, year, data_dir=Path("data/companies"))
    if df.empty:
        print(f"{name} {corp}/{year}: SCE 없음")
        continue
    fs = "CFS" if (df["fs_div"] == "CFS").any() else "OFS"
    res = sce_balance(df, fs)
    if not res["computable"]:
        print(f"\n{name} {corp}/{year} ({fs}): ⛔ 검산 불가 {res}")
        continue
    beg, leaf_sum, end, diff = res["begin"], res["leaf_sum"], res["end"], res["diff"]
    verdict = "OK" if res["ok"] else f"FAIL({diff / M:,.0f})"
    print(
        f"\n{name} {corp}/{year} ({fs}): 기초 {beg / M:,.0f} + Σleaf {leaf_sum / M:,.0f}"
        f" = {(beg + leaf_sum) / M:,.0f}"
    )
    print(
        f"  기말(자본총계) {end / M:,.0f} | 검산오차 {diff / M:,.0f} → {verdict}"
        f"  (leaf {res['n_leaf']}행, 소계·조정후개시 {res['n_excluded']}행 제외)"
    )
