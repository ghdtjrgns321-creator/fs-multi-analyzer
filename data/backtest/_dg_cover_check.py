"""00100939·00101044 본문 자산총계 값 확인 — 주석 2값이 CFS/OFS인지."""

from __future__ import annotations

from pathlib import Path

import duckdb

BASE = Path("data/companies")
for corp, note_vals in [
    ("00100939", "Assets 2024주석: 985,686,727,233 / 461,384,062,352"),
    ("00101044", "Assets 2024주석: 589,396,664,797 / 576,595,365,019"),
]:
    base = BASE / corp
    print(f"\n===== {corp} =====  ({note_vals})")
    for y in sorted(p for p in base.iterdir() if p.is_dir()):
        db = y / "analysis.duckdb"
        if not db.exists():
            continue
        con = duckdb.connect(str(db), read_only=True)
        try:
            cols = [c[0] for c in con.execute("DESCRIBE normalized_financials").fetchall()]
            df = con.execute(
                "SELECT fs_div, amount FROM normalized_financials WHERE canonical='자산총계'"
            ).fetchdf()
            vals = {
                row["fs_div"]: int(row["amount"])
                for _, row in df.iterrows()
                if row["amount"] is not None
            }
            print(f"  {y.name} 자산총계: {vals}   (컬럼:{cols})")
        except Exception as e:
            print(f"  {y.name}: {e}")
        con.close()
