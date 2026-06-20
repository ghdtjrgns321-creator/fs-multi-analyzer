"""50개 표본 재정규화 + 정합성 배치검증 — 전수 전 버그 탐지(8audit+20test 제외).

검증: 항등식(자산=부채+자본)·SCE검산(기초+Σ변동=기말)·이질병합·가짜exact·empty.
실패/이상 회사연도를 목록화 → LLM 판단. 재현: PYTHONPATH=. uv run python data/backtest/_p1_sample50_audit.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

BASE = Path("data/companies")
ROUND = 1_000_000  # 100만 반올림(materiality)

# 이미 깊이검증/기본검증된 28개 제외
EXCLUDE = {
    "00159616",
    "00409681",
    "00118345",
    "00657783",
    "00413046",
    "01091382",
    "00126380",
    "00309503",  # 8 audit
}
all_corps = sorted(d.name for d in BASE.iterdir() if d.is_dir() and d.name.isdigit())
EXCLUDE |= set(all_corps[:20])  # 20 test = 앞 20개
pool = [c for c in all_corps if c not in EXCLUDE]
# 유니버스 전체에 분산되도록 균등 추출 50개
step = max(1, len(pool) // 50)
sample = pool[::step][:50]
print(f"표본 50개 선정(pool {len(pool)}에서 균등). 첫/끝: {sample[0]}..{sample[-1]}")

# 1) force 재정규화
if "--skip-renorm" not in sys.argv:
    print("재정규화 중...")
    r = subprocess.run(
        [sys.executable, "-m", "src.normalize.renormalize_all", "--force", *sample],
        capture_output=True,
        text=True,
    )
    print("  ", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])


def amt(df, canon, fs):
    s = df[(df["canonical"] == canon) & (df["fs_div"] == fs)]
    if s.empty:
        return None
    v = pd.to_numeric(s["amount"], errors="coerce").dropna()
    return None if v.empty else round(float(v.iloc[0]) / ROUND)


fails = {"항등식": [], "SCE검산": [], "SCE미검증": [], "이질병합": [], "가짜exact": [], "empty": []}
checked = 0
for corp in sample:
    for ydir in sorted(p for p in (BASE / corp).iterdir() if p.is_dir()):
        db = ydir / "analysis.duckdb"
        if not db.exists():
            continue
        year = ydir.name
        try:
            con = duckdb.connect(str(db), read_only=True)
            tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
            if "normalized_financials" not in tabs:
                con.close()
                continue
            nf = con.execute("SELECT * FROM normalized_financials").fetchdf()
            sce = (
                con.execute("SELECT * FROM sce_equity_components").fetchdf()
                if "sce_equity_components" in tabs
                else pd.DataFrame()
            )
            con.close()
        except Exception as e:
            fails["empty"].append(f"{corp}/{year}:DB오류({str(e)[:40]})")
            continue
        checked += 1
        if nf.empty:
            fails["empty"].append(f"{corp}/{year}")
            continue
        # 항등식: 자산 = 부채 + 자본 (CFS·OFS)
        for fs in ("CFS", "OFS"):
            a, li, eq = amt(nf, "자산총계", fs), amt(nf, "부채총계", fs), amt(nf, "자본총계", fs)
            if a is not None and li is not None and eq is not None and abs(a - (li + eq)) > 2:
                fails["항등식"].append(f"{corp}/{year}/{fs}:diff={a - (li + eq)}")
        # SCE 검산: 기초 + Σ개별변동 = 기말. 소계(변동들의 합)·미매핑은 제외.
        # 미매핑(기타중요계정) 변동이 있으면 검산 불가(unverifiable)로 분리.
        SUBTOTALS = {
            "기초자본",
            "자본총계",
            "자본증감합계",
            "소유주와의 거래 합계",
            "총포괄손익",
            "포괄손익합계",
            "기타포괄손익합계",
        }
        if not sce.empty:
            mk = sce[(sce["fs_div"] == "CFS") & (sce["component_role"] == "marker")].copy()
            mk["a"] = pd.to_numeric(mk["amount"], errors="coerce")
            beg = mk[mk["change_canonical"] == "기초자본"]["a"].sum()
            end = mk[mk["change_canonical"] == "자본총계"]["a"].sum()
            has_unmapped = (mk["change_canonical"] == "기타 중요 계정").any()
            mv = mk[~mk["change_canonical"].isin(SUBTOTALS | {"기타 중요 계정"})]["a"].sum()
            if end == 0 or beg == 0:
                pass  # 기초/기말 마커 없음 → 검산 불가
            elif has_unmapped:
                fails["SCE미검증"].append(f"{corp}/{year}:미매핑변동 있음")
            elif abs(beg + mv - end) > abs(end) * 0.01:
                fails["SCE검산"].append(f"{corp}/{year}:오차={beg + mv - end:,.0f}/기말{end:,.0f}")
        # 가짜 exact: mapping_status=exact인데 account_id 공백/비표준
        fake = nf[
            (nf["mapping_status"] == "exact_taxonomy_match")
            & (nf["account_id"].fillna("").str.strip().isin(["", "-표준계정코드 미사용-"]))
        ]
        if len(fake) > 0:
            fails["가짜exact"].append(f"{corp}/{year}:{len(fake)}건")
        # 이질병합: 한 canonical에 sj_div 혼재(IS/CIS 제외)
        for canon, g in nf[nf["canonical"] != "기타 중요 계정"].groupby("canonical"):
            sjs = set(g["sj_div"]) - {"IS", "CIS"}
            if len(sjs) > 1:
                fails["이질병합"].append(f"{corp}/{year}:{canon}={sorted(set(g['sj_div']))}")

print(f"\n검증 회사연도: {checked}")
for k, v in fails.items():
    print(f"  {k}: 실패 {len(v)}건")
    for x in v[:6]:
        print(f"     {x}")
Path("data/backtest/_p1_sample50.json").write_text(
    json.dumps(
        {"sample": sample, "checked": checked, "fails": fails}, ensure_ascii=False, indent=1
    ),
    encoding="utf-8",
)
print("→ data/backtest/_p1_sample50.json")
