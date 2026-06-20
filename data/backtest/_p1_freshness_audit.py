"""Phase1 본문 정규화가 현 파이프라인 기준으로 최신인지 전수 점검(§9).

현 파이프라인 산출 normalized_financials는 currency 컬럼 보유(D-F)·428 canonical 반영.
구 스키마(currency 없음)면 그 회사연도 본문은 stale → 재정규화 필요.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import duckdb

BASE = Path("data/companies")

cy_with_db = 0
has_norm = 0
fresh = 0  # currency 컬럼 보유(현 파이프라인)
stale = 0  # normalized_financials 있으나 currency 없음
has_sce = 0
has_notes = 0
col_variants: Counter = Counter()

for corp in BASE.iterdir():
    if not corp.is_dir():
        continue
    for yr in corp.iterdir():
        db = yr / "analysis.duckdb"
        if not db.exists():
            continue
        cy_with_db += 1
        try:
            con = duckdb.connect(str(db), read_only=True)
            tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
            if "normalized_financials" in tabs:
                has_norm += 1
                cols = [c[0] for c in con.execute("DESCRIBE normalized_financials").fetchall()]
                if "currency" in cols:
                    fresh += 1
                else:
                    stale += 1
                col_variants[tuple(sorted(cols))] += 1
            if "sce_equity_components" in tabs:
                has_sce += 1
            if "note_facts_classified" in tabs:
                has_notes += 1
            con.close()
        except Exception:
            pass

print(f"analysis.duckdb 보유 회사연도   : {cy_with_db}")
print(f"  normalized_financials 보유    : {has_norm}")
print(f"    ├ 최신(currency 컬럼 O)     : {fresh}")
print(f"    └ 구스키마(currency X)=stale: {stale}")
print(f"  sce_equity_components 보유    : {has_sce}")
print(f"  note_facts_classified 보유    : {has_notes}")
print(f"\nnormalized_financials 컬럼 변종 수: {len(col_variants)}")
for cols, n in col_variants.most_common():
    print(f"  {n:>5}  cols={list(cols)}")
