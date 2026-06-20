"""Phase1 정합성 감사 — A완전성·B항등식·C분류·F신뢰를 감사대상에 측정(읽기전용).

대상=백테스트 라벨 회사. 회사별로 측정값을 구조화 출력 → LLM이 읽고 판단.
재현: PYTHONPATH=. uv run python data/backtest/_p1_integrity_audit.py
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd

BASE = Path("data/companies")
ROUND = 1_000_000  # materiality 비교용 100만(원) 반올림

# 감사 대상(백테스트 라벨)
TARGETS = {
    "00159616": "두산에너빌리티(분식)",
    "00409681": "아스트(분식)",
    "00118345": "디아이동일(분식)",
    "00657783": "모델솔루션(분식)",
    "00413046": "셀트리온(분식)",
    "01091382": "세토피아(분식·미발굴)",
    "00126380": "삼성전자(정상)",
    "00309503": "KAI(정상)",
}


def raw_rows(corp: str, year: str) -> tuple[int, set[str], str]:
    """raw finstate CSV: 행수·sj_div집합·rcept_no(정정공시 판정용)."""
    total = 0
    sjs: set[str] = set()
    rcept = ""
    for fs in ("CFS", "OFS"):
        p = BASE / corp / year / "raw" / f"finstate_all_{fs}.csv"
        if not p.exists() or p.stat().st_size <= 5:
            continue
        # utf-8-sig: 첫 컬럼 BOM 제거(없으면 rcept_no 키 조회가 None 반환 = 정정공시 검사 무음)
        with p.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                total += 1
                sjs.add((r.get("sj_div") or "").strip())
                if not rcept:
                    rcept = (r.get("rcept_no") or "")[:8]
    return total, sjs, rcept


def load_norm(corp: str, year: str):
    db = BASE / corp / year / "analysis.duckdb"
    if not db.exists():
        return None
    con = duckdb.connect(str(db), read_only=True)
    tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    if "normalized_financials" not in tabs:
        con.close()
        return None
    df = con.execute("SELECT * FROM normalized_financials").fetchdf()
    notes = 0
    if "note_facts_classified" in tabs:
        notes = con.execute("SELECT COUNT(*) FROM note_facts_classified").fetchone()[0]
    con.close()
    return df, notes


def canon_amt(df, canonical, fs_div):
    sub = df[(df["canonical"] == canonical) & (df["fs_div"] == fs_div)]
    if sub.empty:
        return None
    v = pd.to_numeric(sub["amount"], errors="coerce").dropna()
    return None if v.empty else round(float(v.iloc[0]) / ROUND)


for corp, name in TARGETS.items():
    cdir = BASE / corp
    years = (
        sorted(y.name for y in cdir.iterdir() if y.is_dir() and y.name.isdigit())
        if cdir.exists()
        else []
    )
    print(f"\n{'=' * 78}\n[{name} {corp}] 연도 {years}")
    prev_amt: dict = {}
    for year in years:
        rn, raw_sj, rcept = raw_rows(corp, year)
        loaded = load_norm(corp, year)
        if loaded is None:
            print(f"  {year}: 정규화 없음 (raw {rn}행, sj={sorted(raw_sj)})")
            continue
        df, notes = loaded
        nn = len(df)
        mapped = int((df["canonical"] != "기타 중요 계정").sum())
        # C 금액가중 미분류(소계 제외 위해 BS만·절대값)
        amt = pd.to_numeric(df["amount"], errors="coerce").abs().fillna(0)
        other_mask = df["canonical"] == "기타 중요 계정"
        amt_other = float(amt[other_mask].sum())
        amt_all = float(amt.sum())
        amt_other_pct = amt_other / amt_all * 100 if amt_all else 0
        # B 항등식: 자산 = 부채 + 자본 (CFS·OFS)
        ident = []
        for fs in ("CFS", "OFS"):
            a = canon_amt(df, "자산총계", fs)
            li = canon_amt(df, "부채총계", fs)
            eq = canon_amt(df, "자본총계", fs)
            if a is not None and li is not None and eq is not None:
                diff = a - (li + eq)
                ident.append(f"{fs}:자산{a}={li}+{eq}? diff={diff}")
        # F 정정공시: 신고일(rcept YYYYMMDD) vs 회계연도. 정상=Y+1, 지연=정정 의심
        lag = ""
        if rcept and len(rcept) == 8 and year.isdigit():
            fy = int(year)
            fyear_rcept = int(rcept[:4])
            lag = f"신고{rcept}(FY+{fyear_rcept - fy})"
        # C 이질병합: 한 canonical에 sj_div 혼재(IS/CIS 제외)
        hetero = []
        for canon, grp in df[df["canonical"] != "기타 중요 계정"].groupby("canonical"):
            sjset = set(grp["sj_div"]) - set()
            if len({s for s in sjset} - {"IS", "CIS"}) > 1 or (
                len(sjset) > 1 and sjset != {"IS", "CIS"} and not sjset <= {"IS", "CIS"}
            ):
                hetero.append(f"{canon}={sorted(sjset)}")
        # 시계열: 올해 자산총계 vs 작년 동 amount(연결)
        ts = ""
        a_now = canon_amt(df, "자산총계", "CFS")
        if "자산총계_CFS" in prev_amt and a_now is not None:
            ts = f"자산총계 작년={prev_amt['자산총계_CFS']} 올해={a_now}"
        if a_now is not None:
            prev_amt["자산총계_CFS"] = a_now

        print(
            f"  {year}: raw{rn}→norm{nn} 분류{mapped}/{nn}({mapped / nn * 100:.0f}%) "
            f"금액가중미분류={amt_other_pct:.1f}% 주석{notes} {lag}"
        )
        print(
            f"      sj(raw)={sorted(raw_sj)} sj(norm)={sorted(set(df['sj_div']))} 통화={sorted(set(df['currency']))}"
        )
        if ident:
            print(f"      항등식 {' | '.join(ident)}")
        if hetero:
            print(f"      ⚠이질병합 {hetero[:5]}")
        if ts:
            print(f"      시계열 {ts}")
