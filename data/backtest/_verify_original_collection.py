"""원본 공시 수집 가능성 독립 재현(§9 — 서브에이전트 결과 무비판 수용 금지).

두산 FY2017: list(final=False)로 원본 사업보고서 rcept 확인 → finstate_xml로 원본 순이익 추출
→ 현 정규화(정정본) 순이익과 대조. 서브에이전트 주장(원본 -1,097억 vs 정정 -1,980억) 재현.
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import duckdb

from src.collect.opendart import DartCollector

CORP = "00159616"  # 두산에너빌리티
FY = 2017
col = DartCollector()

# 1) list(final=False) — 원본+정정 모두 나열
print("=== 1. 사업보고서 버전 (list final=False, FY2017 신고분=2018) ===")
lst = col._dart.list(corp=CORP, start="20180101", end="20181231", kind="A", final=False)
biz = (
    lst[lst["report_nm"].astype(str).str.contains("사업보고서")]
    if lst is not None and not lst.empty
    else None
)
if biz is not None:
    for _, r in biz.iterrows():
        print(f"  rcept={r['rcept_no']} dt={r['rcept_dt']} nm={r['report_nm']}")
# 정정 신고분(2024)도 확인
print("=== 정정분 (2024) ===")
lst2 = col._dart.list(corp=CORP, start="20240101", end="20241231", kind="A", final=False)
biz2 = (
    lst2[lst2["report_nm"].astype(str).str.contains("사업보고서")]
    if lst2 is not None and not lst2.empty
    else None
)
if biz2 is not None:
    for _, r in biz2.iterrows():
        print(f"  rcept={r['rcept_no']} dt={r['rcept_dt']} nm={r['report_nm']}")

# 2) 원본 rcept의 XBRL → 당기순이익(ProfitLoss)
orig_rcept = (
    str(biz.sort_values("rcept_dt").iloc[0]["rcept_no"])
    if biz is not None and not biz.empty
    else None
)
print(f"\n=== 2. 원본 rcept={orig_rcept} finstate_xml → 당기순이익 ===")
if orig_rcept:
    tmpzip = Path(tempfile.gettempdir()) / f"orig_{orig_rcept}.zip"
    ok = col._dart.finstate_xml(orig_rcept, save_as=str(tmpzip))
    if ok and tmpzip.exists():
        from arelle import Cntlr

        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(tmpzip) as zf:
            zf.extractall(tmp)
        ent = list(Path(tmp).glob("*.xbrl"))
        if ent:
            c = Cntlr.Cntlr(logFileName="logToBuffer")
            m = c.modelManager.load(str(ent[0]))
            vals = []
            for f in m.facts:
                if (
                    f.concept is not None
                    and f.concept.qname is not None
                    and f.concept.qname.localName == "ProfitLoss"
                ):
                    ctx = f.context
                    dims = list((ctx.qnameDims or {}).keys()) if ctx is not None else []
                    dimstr = "|".join(d.localName for d in dims) or "무차원"
                    vals.append((dimstr, f.value))
            c.modelManager.close()
            print(f"  원본 ProfitLoss 전체({len(vals)}): {vals[:8]}")
        else:
            print(f"  .xbrl 없음 — zip 내용: {[p.name for p in Path(tmp).iterdir()][:6]}")
    else:
        print("  finstate_xml 실패/빈응답")

# 3) 정정본(현 정규화 DB) 당기순이익
print("\n=== 3. 정정본(현 정규화) 당기순이익 FY2017 ===")
db = Path(f"data/companies/{CORP}/{FY}/analysis.duckdb")
if db.exists():
    con = duckdb.connect(str(db), read_only=True)
    df = con.execute(
        "SELECT fs_div, amount FROM normalized_financials WHERE canonical='당기순이익' AND sj_div IN ('IS','CIS')"
    ).fetchdf()
    con.close()
    for _, r in df.iterrows():
        print(f"  {r['fs_div']}: {int(r['amount']):,}")
