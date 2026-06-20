"""재정규화 20개사 테스트 검증 — 통화·428 canonical 반영·SCE·분류율."""

from __future__ import annotations

from pathlib import Path

import duckdb

BASE = Path("data/companies")
corps = sorted(d.name for d in BASE.iterdir() if d.is_dir() and d.name.isdigit())[:20]

checked = 0
for corp in corps:
    for ydir in sorted(p for p in (BASE / corp).iterdir() if p.is_dir()):
        db = ydir / "analysis.duckdb"
        if not db.exists():
            continue
        con = duckdb.connect(str(db), read_only=True)
        tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if "normalized_financials" not in tabs:
            con.close()
            continue
        cols = [c[0] for c in con.execute("DESCRIBE normalized_financials").fetchall()]
        n = con.execute("SELECT COUNT(*) FROM normalized_financials").fetchone()[0]
        mapped = con.execute(
            "SELECT COUNT(*) FROM normalized_financials WHERE canonical != '기타 중요 계정'"
        ).fetchone()[0]
        n_canon = con.execute(
            "SELECT COUNT(DISTINCT canonical) FROM normalized_financials WHERE canonical != '기타 중요 계정'"
        ).fetchone()[0]
        currencies = (
            [
                r[0]
                for r in con.execute(
                    "SELECT DISTINCT currency FROM normalized_financials"
                ).fetchall()
            ]
            if "currency" in cols
            else []
        )
        sce_n = (
            con.execute("SELECT COUNT(*) FROM sce_equity_components").fetchone()[0]
            if "sce_equity_components" in tabs
            else -1
        )
        # 새 D-A canonical(CF조정·세그먼트 등)이 실제로 잡혔나 표본
        cf = con.execute(
            "SELECT COUNT(*) FROM normalized_financials WHERE sj_div='CF' AND canonical != '기타 중요 계정'"
        ).fetchone()[0]
        cf_tot = con.execute(
            "SELECT COUNT(*) FROM normalized_financials WHERE sj_div='CF'"
        ).fetchone()[0]
        con.close()
        cur = "currency" in cols
        print(
            f"{corp}/{ydir.name}: {n}행 분류 {mapped}/{n}({mapped / n * 100:.0f}%) "
            f"canon종={n_canon} 통화={'O' + str(currencies) if cur else 'X(stale!)'} "
            f"SCE={sce_n} CF분류={cf}/{cf_tot}"
        )
        checked += 1
        if checked >= 6:
            break
    if checked >= 6:
        break
