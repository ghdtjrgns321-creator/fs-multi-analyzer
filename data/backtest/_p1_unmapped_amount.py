"""금액가중 미분류의 정체 — 미분류(기타) 행을 금액순으로 본다(읽기전용).

무엇이 미분류로 큰 금액을 차지하나? 진짜 중요계정인가, 소계/CF집계/회사특화인가."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

BASE = Path("data/companies")
CASES = [
    ("셀트리온", "00413046", "2015"),
    ("세토피아", "01091382", "2017"),
    ("두산에너빌리티", "00159616", "2017"),
]

for name, corp, year in CASES:
    db = BASE / corp / year / "analysis.duckdb"
    con = duckdb.connect(str(db), read_only=True)
    df = con.execute(
        "SELECT sj_div, canonical, label, amount, fs_div FROM normalized_financials"
    ).fetchdf()
    con.close()
    df["amt"] = pd.to_numeric(df["amount"], errors="coerce").abs().fillna(0)
    other = df[df["canonical"] == "기타 중요 계정"].sort_values("amt", ascending=False)
    print(f"\n=== {name} {year} — 미분류(기타) 상위 12 (금액순) ===")
    for _, r in other.head(12).iterrows():
        print(f"  {r['sj_div']:4s} {r['fs_div']:4s} {int(r['amt']):>18,}  {str(r['label'])[:34]}")
    # sj_div별 미분류 금액 비중
    print("  sj_div별 미분류 금액합:")
    g = other.groupby("sj_div")["amt"].sum().sort_values(ascending=False)
    for sj, v in g.items():
        print(f"    {sj}: {int(v):,}")
