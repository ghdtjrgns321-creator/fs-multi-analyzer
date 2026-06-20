"""적재된 note_facts_classified 검증 — bucket 분포·무차원흡수 제외·세그먼트 실재."""

from __future__ import annotations

from pathlib import Path

import duckdb

from src.normalize.notes_classify import is_dimensioned

BASE = Path("data/companies")
for corp in ("00100939", "00409681"):
    cdir = BASE / corp
    for ydir in sorted(p for p in cdir.iterdir() if p.is_dir()):
        db = ydir / "analysis.duckdb"
        if not db.exists():
            continue
        con = duckdb.connect(str(db), read_only=True)
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if "note_facts_classified" not in tables:
            con.close()
            continue
        df = con.execute("SELECT * FROM note_facts_classified").fetchdf()
        con.close()
        if df.empty:
            continue
        buckets = df["bucket"].value_counts().to_dict()
        # 무차원 흡수가 섞였나(있으면 버그)
        absorb = df[df["bucket"] == "흡수"]
        nodim = sum(1 for d in absorb["dimensions"] if not is_dimensioned(d))
        segrows = sum(
            1
            for d in df["dimensions"]
            if "SegmentsAxis" in str(d) or "GeographicalAreasAxis" in str(d)
        )
        print(
            f"{corp}/{ydir.name}: {len(df)}행 {buckets} | 무차원흡수={nodim}(0이어야) | 세그먼트행={segrows}"
        )
        # 유차원 흡수 샘플
        for _, r in absorb.head(2).iterrows():
            print(
                f"    [흡수] {str(r['concept'])[:24]:24s}={r['value']:>14} ← {str(r['dimensions'])[:55]}"
            )
