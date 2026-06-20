"""분식사 원본 재무제표 가용성 전수조사 — 정정본 vs 원본 차이 + 교체 대상 확정(읽기전용).

각 분식 회사연도: list(final=False)로 원본 사업보고서 rcept → finstate_xml 가용 여부 → 원본
자산총계·당기순이익(연결) 추출 → 현 정규화(정정본)와 대조. 원본가용·diff면 교체 대상.
재현: PYTHONPATH=. uv run python data/backtest/_orig_availability_scan.py
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import duckdb

from src.collect.opendart import DartCollector

# 2015+ 분식연도 6사 (corp_code, 회사, 분식연도들)
TARGETS = [
    ("00159616", "두산에너빌리티", [2017, 2018, 2019]),
    ("00409681", "아스트", [2018, 2019, 2020, 2021]),
    ("00118345", "디아이동일", [2016, 2017, 2018, 2019]),
    ("00657783", "모델솔루션", [2022, 2023]),
    ("00413046", "셀트리온", [2016, 2017, 2018, 2019, 2020]),
    ("01091382", "세토피아", [2018, 2019]),
]
col = DartCollector()
M = 1_000_000


def original_rcept(corp: str, fy: int) -> str | None:
    """fy의 원본 사업보고서 rcept(신고 fy+1, 가장 이른 사업보고서)."""
    sy = fy + 1
    lst = col._dart.list(corp=corp, start=f"{sy}0101", end=f"{sy}1231", kind="A", final=False)
    if lst is None or lst.empty:
        return None
    biz = lst[lst["report_nm"].astype(str).str.contains("사업보고서", regex=False)]
    biz = biz[~biz["report_nm"].astype(str).str.contains("정정")]  # 원본만
    if biz.empty:
        return None
    return str(biz.sort_values("rcept_dt").iloc[0]["rcept_no"])


def orig_values(rcept: str) -> dict[str, float] | None:
    """원본 XBRL에서 Assets·ProfitLoss 연결(무 ComponentsOfEquity) 추출. 빈 템플릿이면 None."""
    tmpzip = Path(tempfile.gettempdir()) / f"o_{rcept}.zip"
    try:
        ok = col._dart.finstate_xml(rcept, save_as=str(tmpzip))
    except Exception:
        return None
    if not ok or not tmpzip.exists():
        return None
    from arelle import Cntlr

    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(tmpzip) as zf:
        zf.extractall(tmp)
    ent = list(Path(tmp).glob("*.xbrl"))
    if not ent:
        return None
    c = Cntlr.Cntlr(logFileName="logToBuffer")
    m = c.modelManager.load(str(ent[0]))
    if m is None or not getattr(m, "facts", None):
        c.modelManager.close()
        return None
    # context-aware: 연결(Consolidated)·당기(최신 endDate)·차원없음(구성요소/세그먼트 제외)만.
    cand: dict[str, list] = {"Assets": [], "ProfitLoss": []}
    for f in m.facts:
        if f.concept is None or f.concept.qname is None:
            continue
        ln = f.concept.qname.localName
        if ln not in cand:
            continue
        ctx = f.context
        if ctx is None:
            continue
        dimmap = {d.localName: dv for d, dv in (ctx.qnameDims or {}).items()}
        # 연결/별도축 외 다른 축(구성요소·세그먼트 등) 있으면 제외
        other_axes = set(dimmap) - {"ConsolidatedAndSeparateFinancialStatementsAxis"}
        if other_axes:
            continue
        # 연결만(별도 제외). 축 없으면 연결로 간주.
        csa = dimmap.get("ConsolidatedAndSeparateFinancialStatementsAxis")
        member = ""
        if csa is not None:
            try:
                member = csa.memberQname.localName if csa.isExplicit else ""
            except Exception:
                member = str(csa)
        if member and "Consolidated" not in member:
            continue
        end = ctx.endDatetime
        try:
            v = float(f.value)
        except (ValueError, TypeError):
            continue
        cand[ln].append((end, v))
    out: dict[str, float] = {}
    for ln, lst2 in cand.items():
        if lst2:
            out[ln] = max(lst2, key=lambda t: t[0] or 0)[1]  # 최신 기간(당기)
    c.modelManager.close()
    return out or None


def current_value(corp: str, fy: int, canon: str) -> float | None:
    db = Path(f"data/companies/{corp}/{fy}/analysis.duckdb")
    if not db.exists():
        return None
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = con.execute(
            f"SELECT amount FROM normalized_financials WHERE canonical='{canon}' AND fs_div='CFS' "
            "AND sj_div IN ('BS','IS','CIS')"
        ).fetchdf()
    finally:
        con.close()
    a = df["amount"].dropna()
    return None if a.empty else float(a.iloc[0])


print(f"{'회사연도':22} {'원본가용':6} {'원본순이익':>14} {'정정순이익':>14} {'판정'}")
print("-" * 80)
for corp, name, years in TARGETS:
    for fy in years:
        rc = original_rcept(corp, fy)
        ov = orig_values(rc) if rc else None
        if ov is None:
            print(f"{name + '/' + str(fy):22} {'없음':6} (원본 XBRL 빈템플릿/미제공)")
            continue
        o_pl = ov.get("ProfitLoss")
        c_pl = current_value(corp, fy, "당기순이익")
        diff = (o_pl - c_pl) if (o_pl is not None and c_pl is not None) else None
        verdict = (
            "교체대상(diff)"
            if (diff and abs(diff) > 1e9)
            else ("동일" if diff is not None else "비교불가")
        )
        op = f"{o_pl / M:,.0f}" if o_pl is not None else "—"
        cp = f"{c_pl / M:,.0f}" if c_pl is not None else "—"
        print(f"{name + '/' + str(fy):22} {'O':6} {op:>14} {cp:>14} {verdict}")
