"""적재 결과 전수 검증(§9). note_facts_classified 테이블 수·행수·무차원흡수 누출·세그먼트 보존."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import duckdb

from src.normalize.notes_classify import is_dimensioned

BASE = Path("data/companies")

# 1) 전수: 테이블 보유 회사연도 수 + 총 행수
tables = 0
total_rows = 0
note_cy = 0  # note_facts.tsv 보유(적재 대상 분모)
for corp in BASE.iterdir():
    if not corp.is_dir():
        continue
    for yr in corp.iterdir():
        if (yr / "raw" / "notes_xbrl" / "note_facts.tsv").exists():
            note_cy += 1
        db = yr / "analysis.duckdb"
        if not db.exists():
            continue
        try:
            con = duckdb.connect(str(db), read_only=True)
            tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
            if "note_facts_classified" in tabs:
                tables += 1
                total_rows += con.execute("SELECT COUNT(*) FROM note_facts_classified").fetchone()[
                    0
                ]
            con.close()
        except Exception:
            pass

print("=== 전수 ===")
print(f"note 적재 대상(tsv 보유)     : {note_cy}")
print(f"note_facts_classified 테이블 : {tables}")
print(f"총 적재행                    : {total_rows:,}")

# 2) 표본: bucket 분포 + 무차원흡수 누출 + 세그먼트 보존
SAMPLE = 250
dbs = []
for corp in sorted(BASE.iterdir()):
    if corp.is_dir():
        for yr in sorted(corp.iterdir()):
            db = yr / "analysis.duckdb"
            if db.exists():
                dbs.append(db)
step = max(1, len(dbs) // SAMPLE)
sample = dbs[::step][:SAMPLE]

bucket = Counter()
nodim_absorb = 0
seg_rows = 0
checked = 0
for db in sample:
    try:
        con = duckdb.connect(str(db), read_only=True)
        tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if "note_facts_classified" not in tabs:
            con.close()
            continue
        df = con.execute("SELECT bucket, dimensions FROM note_facts_classified").fetchdf()
        con.close()
    except Exception:
        continue
    checked += 1
    bucket.update(df["bucket"].tolist())
    ab = df[df["bucket"] == "흡수"]
    nodim_absorb += sum(1 for d in ab["dimensions"] if not is_dimensioned(d))
    seg_rows += sum(
        1 for d in df["dimensions"] if "SegmentsAxis" in str(d) or "GeographicalAreasAxis" in str(d)
    )

print(f"\n=== 표본 {checked} DB ===")
print(f"bucket 분포: {dict(bucket)}")
print(f"무차원흡수 누출(0이어야): {nodim_absorb}")
print(f"세그먼트행: {seg_rows}")
