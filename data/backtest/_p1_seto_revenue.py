"""세토피아 매출 미분류 원인 — 매출/수익 행의 account_id·label·canonical 직접 확인."""

from __future__ import annotations

from pathlib import Path

import duckdb

BASE = Path("data/companies")
db = BASE / "01091382" / "2017" / "analysis.duckdb"
con = duckdb.connect(str(db), read_only=True)
df = con.execute(
    "SELECT sj_div, fs_div, account_id, label, canonical, mapping_status, amount "
    "FROM normalized_financials WHERE sj_div IN ('IS','CIS') ORDER BY fs_div, sj_div"
).fetchdf()
con.close()
print("세토피아 2017 IS/CIS 전체 행 (매출·수익 분류 확인):")
for _, r in df.iterrows():
    print(
        f"  {r['fs_div']:4s} {r['sj_div']:4s} id={str(r['account_id'])[:42]:42s} "
        f"label={str(r['label'])[:20]:20s} → {str(r['canonical'])[:14]:14s} [{r['mapping_status']}]"
    )
