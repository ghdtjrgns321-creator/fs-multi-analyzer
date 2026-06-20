"""원본(분식) vs 정정본 본문+주석 대조 — 가져온 원본이 진짜 분식본인지 검증(읽기전용).

원본 rcept XBRL·정정 rcept XBRL을 같은 파서로 추출해 (account_id·fs_div·detail·기간) 키로
정렬, 본문 핵심계정·전체계정·주석(D8xx) diff를 분식방향과 함께 출력. 정정 XBRL 순이익이
디스크 정정본 finstate_all CSV와 일치하는지 교차검증(파서 신뢰성).

재현: PYTHONPATH=. uv run python data/backtest/_orig_vs_corr_compare.py <corp> <fy>
기본: 00159616 2017 (두산에너빌리티)
"""

from __future__ import annotations

import re
import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb
import pandas as pd
from arelle import Cntlr, XbrlConst

from src.collect.opendart import DartCollector

col = DartCollector()
M = 1_000_000

# ELR role 첫 자리 → 재무제표 구분. D2*=BS·D3*=IS·D4*=CIS·D5*=CF·D6*=SCE·D8*=주석·D9*=문서.
_GROUP_BY_HUNDREDS = {
    "2": "BS",
    "3": "IS",
    "4": "CIS",
    "5": "CF",
    "6": "SCE",
    "8": "NOTE",
    "9": "DOC",
}
_GROUP_PRIORITY = {"BS": 5, "IS": 5, "CIS": 5, "CF": 5, "SCE": 5, "NOTE": 2, "DOC": 1}
_CSA_AXIS = "ConsolidatedAndSeparateFinancialStatementsAxis"
# 본문 핵심계정(localName) — 항등식·분식 핵심
CORE = [
    "Assets",
    "CurrentAssets",
    "NoncurrentAssets",
    "Liabilities",
    "Equity",
    "LiabilitiesAndEquity",
    "Revenue",
    "OperatingIncomeLoss",
    "ProfitLoss",
]


def corr_rcept(corp: str, fy: int) -> str | None:
    """디스크 정정본 raw CSV 첫 행의 rcept_no(= 우리가 가진 정정 신고분)."""
    for div in ("CFS", "OFS"):
        p = Path(f"data/companies/{corp}/{fy}/raw/finstate_all_{div}.csv")
        if p.exists():
            df = pd.read_csv(p, dtype=str, nrows=1)
            if "rcept_no" in df and not df.empty:
                return str(df["rcept_no"].iloc[0])
    return None


def original_rcept(corp: str, fy: int) -> str | None:
    """fy 원본 사업보고서 rcept(신고 fy+1, 정정 아닌 가장 이른 것)."""
    sy = fy + 1
    lst = col._dart.list(corp=corp, start=f"{sy}0101", end=f"{sy}1231", kind="A", final=False)
    if lst is None or lst.empty:
        return None
    biz = lst[lst["report_nm"].astype(str).str.contains("사업보고서", regex=False)]
    biz = biz[~biz["report_nm"].astype(str).str.contains("정정")]
    if biz.empty:
        return None
    return str(biz.sort_values("rcept_dt").iloc[0]["rcept_no"])


def _role_group(elr: str) -> str | None:
    m = re.search(r"-D(\d)\d{5}", elr)
    return _GROUP_BY_HUNDREDS.get(m.group(1)) if m else None


def _concept_groups(model) -> dict[str, str]:
    """concept localName → 재무제표 구분(presentation ELR 기준, 본문 우선)."""
    groups: dict[str, str] = {}
    base = model.relationshipSet(XbrlConst.parentChild)
    for elr in base.linkRoleUris:
        g = _role_group(elr)
        if g is None:
            continue
        sub = model.relationshipSet(XbrlConst.parentChild, elr)
        for rel in sub.modelRelationships:
            for concept in (rel.fromModelObject, rel.toModelObject):
                if concept is None or concept.qname is None:
                    continue
                ln = concept.qname.localName
                if ln not in groups or _GROUP_PRIORITY[g] > _GROUP_PRIORITY[groups[ln]]:
                    groups[ln] = g
    return groups


def load_facts(rcept: str) -> dict | None:
    """rcept XBRL → {(account_id, fs_div, detail, period): (value, group, label)}.

    period: 당기=0·전기=1·전전기=2(전체 endDatetime 내림차순 rank). 숫자 fact만.
    """
    tmpzip = Path(tempfile.gettempdir()) / f"cmp_{rcept}.zip"
    try:
        ok = col._dart.finstate_xml(rcept, save_as=str(tmpzip))
    except Exception:
        return None
    if not ok or not tmpzip.exists():
        return None
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(tmpzip) as zf:
        zf.extractall(tmp)
    ent = list(Path(tmp).glob("*.xbrl"))
    if not ent:
        return None
    c = Cntlr.Cntlr(logFileName="logToBuffer")
    model = c.modelManager.load(str(ent[0]))
    if model is None or not getattr(model, "facts", None):
        c.modelManager.close()
        return None
    groups = _concept_groups(model)
    ends = sorted(
        {f.context.endDatetime for f in model.facts if f.context and f.context.endDatetime},
        reverse=True,
    )
    rank = {e: i for i, e in enumerate(ends)}
    out: dict = {}
    for f in model.facts:
        if f.concept is None or f.concept.qname is None or f.context is None:
            continue
        ln = f.concept.qname.localName
        aid = f"{f.concept.qname.prefix or 'ifrs'}_{ln}"
        ctx = f.context
        dims = {d.localName: dv for d, dv in (ctx.qnameDims or {}).items()}
        fs = "CFS"
        detail_parts = []
        for axis, dv in sorted(dims.items()):
            member = ""
            try:
                member = dv.memberQname.localName if dv.isExplicit else str(dv)
            except Exception:
                member = str(dv)
            if axis == _CSA_AXIS:
                fs = "OFS" if "Separate" in member else "CFS"
            else:
                detail_parts.append(f"{axis}={member}")
        detail = "|".join(detail_parts)
        end = ctx.endDatetime
        if end not in rank:
            continue
        try:
            v = float(f.value)
        except (ValueError, TypeError):
            continue
        out[(aid, fs, detail, rank[end])] = (v, groups.get(ln, "NOTE"), ln)
    c.modelManager.close()
    return out


def _find(facts: dict, localname: str, fs: str = "CFS", period: int = 0) -> float | None:
    for (aid, f_fs, detail, per), (v, _g, ln) in facts.items():
        if ln == localname and f_fs == fs and detail == "" and per == period:
            return v
    return None


def disk_profit(corp: str, fy: int) -> float | None:
    db = Path(f"data/companies/{corp}/{fy}/analysis.duckdb")
    if not db.exists():
        return None
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = con.execute(
            "SELECT amount FROM normalized_financials WHERE canonical='당기순이익' "
            "AND fs_div='CFS' AND sj_div IN ('IS','CIS')"
        ).fetchdf()
    finally:
        con.close()
    a = df["amount"].dropna()
    return None if a.empty else float(a.iloc[0])


def main() -> None:
    corp = sys.argv[1] if len(sys.argv) > 1 else "00159616"
    fy = int(sys.argv[2]) if len(sys.argv) > 2 else 2017
    r_orig = original_rcept(corp, fy)
    r_corr = corr_rcept(corp, fy)
    print(f"=== {corp} FY{fy} | 원본 rcept={r_orig} 정정 rcept={r_corr} ===")
    if not r_orig or not r_corr:
        print("rcept 확보 실패")
        return
    orig = load_facts(r_orig)
    corr = load_facts(r_corr)
    if orig is None or corr is None:
        print("XBRL 로드 실패")
        return

    # 0) 교차검증: 정정 XBRL 순이익 = 디스크 정정본 CSV
    corr_pl = _find(corr, "ProfitLoss")
    disk = disk_profit(corp, fy)
    print("\n[교차검증] 정정 XBRL ProfitLoss(CFS 당기) vs 디스크 정규화 당기순이익")
    print(
        f"  XBRL={corr_pl / M if corr_pl else None:,.0f}백만  디스크={disk / M if disk else None:,.0f}백만"
    )

    # 1) 본문 핵심계정 원본 vs 정정
    print("\n[본문 핵심계정] (CFS 당기, 백만원)")
    print(f"  {'계정':22} {'원본':>16} {'정정':>16} {'차이(원본-정정)':>18}")
    for ln in CORE:
        o = _find(orig, ln)
        c = _find(corr, ln)
        if o is None and c is None:
            continue
        diff = (o - c) if (o is not None and c is not None) else None
        os_ = f"{o / M:,.0f}" if o is not None else "—"
        cs = f"{c / M:,.0f}" if c is not None else "—"
        ds = f"{diff / M:,.0f}" if diff is not None else "—"
        print(f"  {ln:22} {os_:>16} {cs:>16} {ds:>18}")

    # 2) 전체 diff 상위(본문/주석) — 당기·차원없음·CFS
    common = set(orig) & set(corr)
    diffs = []
    for k in common:
        if k[3] != 0 or k[2] != "" or k[1] != "CFS":
            continue
        ov, og, ln = orig[k]
        cv, _cg, _ = corr[k]
        if abs(ov - cv) > 1e6:
            diffs.append((abs(ov - cv), og, ln, ov, cv))
    diffs.sort(reverse=True)
    print(
        f"\n[전체 diff 상위20] 공통키 {len(common)}, 변경 {len(diffs)} (CFS·당기·차원없음, |차|>1백만)"
    )
    print(f"  {'구분':5} {'계정':32} {'원본':>15} {'정정':>15} {'차이':>15}")
    for _, g, ln, ov, cv in diffs[:20]:
        print(f"  {g:5} {ln[:32]:32} {ov / M:>15,.0f} {cv / M:>15,.0f} {(ov - cv) / M:>15,.0f}")

    # 3) 주석(우리 실측 정의 = 차원분해 fact, detail≠"") 원본 vs 정정.
    #    finstate_xml엔 D8xx 주석 텍스트 fact 값이 없다(껍데기 linkbase뿐). 우리가 적재하는
    #    "주석"은 본문개념의 차원분해(세그먼트·자본구성·만기별 숫자)다. 그 차원 fact의 원본↔정정 차이.
    note_diffs = []
    for k in common:
        if k[2] == "" or k[3] != 0 or k[1] != "CFS":  # 차원있음·당기·CFS만
            continue
        ov = orig[k][0]
        cv = corr[k][0]
        if abs(ov - cv) > 1e6:
            note_diffs.append((abs(ov - cv), k[2], orig[k][2], ov, cv))
    note_diffs.sort(reverse=True)
    print(f"\n[차원분해 주석 변경 상위15] 총 {len(note_diffs)}건 (CFS·당기·차원보유 fact)")
    print(f"  {'계정':24} {'차원(detail)':40} {'원본':>12} {'정정':>12}")
    for _, detail, ln, ov, cv in note_diffs[:15]:
        print(f"  {ln[:24]:24} {detail[:40]:40} {ov / M:>12,.0f} {cv / M:>12,.0f}")

    # 원본·정정 전용(한쪽에만 있는 계정) 요약
    only_o = {k[0] for k in orig} - {k[0] for k in corr}
    only_c = {k[0] for k in corr} - {k[0] for k in orig}
    print(f"\n[구조차] 원본에만 account_id {len(only_o)}종, 정정에만 {len(only_c)}종")

    # 진단: group 분포 + 주석키 매칭 (주석 0건이 '안바뀜'인지 '못봄'인지 판별)
    from collections import Counter

    print(f"\n[진단] 원본 group분포 {dict(Counter(v[1] for v in orig.values()))}")
    print(f"[진단] 정정 group분포 {dict(Counter(v[1] for v in corr.values()))}")
    nko = {k for k in orig if orig[k][1] == "NOTE"}
    nkc = {k for k in corr if corr[k][1] == "NOTE"}
    print(f"[진단] NOTE키 원본 {len(nko)} 정정 {len(nkc)} 공통키 {len(nko & nkc)}")
    for k in list(nko)[:6]:
        print(f"    원본NOTE샘플 ln={orig[k][2]} detail={k[2][:50]} val={orig[k][0] / M:,.0f}")


if __name__ == "__main__":
    main()
