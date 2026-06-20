"""Phase1 정합성 감사 2차 — 1차 미측정 이월항목(B~F)을 읽기전용 측정.

1차(자산=부채+자본·이질병합0·완전성·정정공시)에서 미측정한 잔여 항등식·분류 일관성·
부호·provenance·가짜 exact·무음 empty를 회사연도별로 측정한다. 생산코드 변경 없음.

산출: 콘솔 구조화 출력 + data/backtest/_p1_audit2.json(LLM 판단 입력).
재현: PYTHONPATH=. .venv/Scripts/python.exe data/backtest/_p1_integrity_audit2.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd
import yaml

BASE = Path("data/companies")
ROUND = 1_000_000  # 100만원 반올림(materiality)
CONFIG = Path("config/canonical_accounts.yaml")

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

# 부호 규약: K-IFRS 표시상 통상 양수인 비용·차감 항목(연도간 부호 일관성 점검 대상)
COST_CANONICALS = ["매출원가", "판매비와관리비", "법인세비용", "이자비용", "금융비용", "기타비용"]


def load_config() -> tuple[set[str], dict[str, str]]:
    """is_subtotal canonical 집합, account_id→canonical 표준코드 맵(가짜exact 판정용)."""
    d = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    ca = d["canonical_accounts"]
    subtotals = {k for k, v in ca.items() if v.get("is_subtotal")}
    std_ids: set[str] = set()
    for v in ca.values():
        for aid in v.get("account_ids", []):
            std_ids.add(aid)
    return subtotals, std_ids


def is_standard_account_id(aid: str) -> bool:
    """DART 표준 XBRL 계정코드 형태인가(ifrs-full_*, dart_*, entity:* 등)."""
    if not aid or not isinstance(aid, str):
        return False
    aid = aid.strip()
    if not aid or aid in ("-표준계정코드 미사용-", "nan", "None"):
        return False
    # 표준코드는 영문 prefix + 구분자(_ 또는 :). 한글 라벨/공백은 비표준.
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9\-]*[_:]", aid))


def load_year(corp: str, year: str):
    db = BASE / corp / year / "analysis.duckdb"
    if not db.exists():
        return None
    con = duckdb.connect(str(db), read_only=True)
    tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    if "normalized_financials" not in tabs:
        con.close()
        return None
    nf = con.execute("SELECT * FROM normalized_financials").fetchdf()
    sce = (
        con.execute("SELECT * FROM sce_equity_components").fetchdf()
        if "sce_equity_components" in tabs
        else pd.DataFrame()
    )
    note = (
        con.execute("SELECT * FROM note_facts_classified").fetchdf()
        if "note_facts_classified" in tabs
        else pd.DataFrame()
    )
    con.close()
    return nf, sce, note


def m(x):
    """100만원 단위 반올림."""
    return None if x is None or pd.isna(x) else round(float(x) / ROUND)


def canon(nf, name, fs, col="amount"):
    sub = nf[(nf["canonical"] == name) & (nf["fs_div"] == fs)]
    if sub.empty:
        return None
    v = pd.to_numeric(sub[col], errors="coerce").dropna()
    return None if v.empty else float(v.iloc[0])


def net_income_amounts(nf, sj, fs):
    """sj_div별 당기순이익(전체귀속) 금액. canonical 우선, 조정·가감·귀속분 제외."""
    sub = nf[(nf["sj_div"] == sj) & (nf["fs_div"] == fs)]
    # canonical='당기순이익'(IS/CIS 매핑) 우선 — 지배/비지배 귀속분과 분리됨
    exact = sub[sub["canonical"] == "당기순이익"]
    if not exact.empty:
        v = pd.to_numeric(exact["amount"], errors="coerce").dropna()
        if not v.empty:
            return [float(v.iloc[0])]
    # CF/SCE 등 미매핑: label로 본 항목만(조정·가감·차감전·귀속분 제외)
    lab = sub["label"].astype(str)
    is_ni = lab.str.contains("당기순이익", na=False) & ~lab.str.contains(
        "조정|가감|차감전|법인세|반영|제외|배분|귀속|지배", na=False
    )
    return [float(v) for v in pd.to_numeric(sub[is_ni]["amount"], errors="coerce").dropna()]


def audit_B(nf, sce, fs):
    """B 항등식 잔여: 유동/비유동 합=총계, 순이익 4표 일치, SCE roll-forward."""
    out = {}
    # 유동+비유동=총계
    for sub_a, sub_b, tot in [
        ("유동자산", "비유동자산", "자산총계"),
        ("유동부채", "비유동부채", "부채총계"),
    ]:
        a, b, t = canon(nf, sub_a, fs), canon(nf, sub_b, fs), canon(nf, tot, fs)
        if a is not None and b is not None and t is not None:
            out[tot] = {"sub": m(a), "nonsub": m(b), "total": m(t), "diff": m(t - (a + b))}
    # 당기순이익 4표 일치(canonical IS + label 기반 CIS/CF/SCE)
    ni = {}
    is_ni = canon(nf, "당기순이익", fs)
    if is_ni is not None:
        ni["IS"] = m(is_ni)
    for sj in ("CIS", "CF", "SCE"):
        vals = net_income_amounts(nf, sj, fs)
        if vals:
            ni[sj] = m(vals[0])
    # SCE marker 당기순이익(component_std=연결/별도재무제표)
    if not sce.empty:
        fsmark = "연결재무제표" if fs == "CFS" else "별도재무제표"
        sni = sce[
            (sce["fs_div"] == fs)
            & (sce["change_canonical"] == "당기순이익")
            & (sce["component_std"] == fsmark)
        ]
        v = pd.to_numeric(sni["amount"], errors="coerce").dropna()
        if not v.empty:
            ni["SCE_marker"] = m(float(v.iloc[0]))
    if len(ni) >= 2:
        vals = list(ni.values())
        out["당기순이익"] = {"values": ni, "max_diff": max(vals) - min(vals)}
    # 손익 항등식: 당기순이익 = 법인세비용차감전순이익 - 법인세비용
    pre, tax = canon(nf, "법인세비용차감전순이익", fs), canon(nf, "법인세비용", fs)
    if pre is not None and tax is not None and is_ni is not None:
        tol = max(abs(is_ni) * 0.01, 1e8)  # 1% 또는 1억(반올림 허용)
        std_ok = abs((pre - tax) - is_ni) <= tol
        flip_ok = abs((pre + tax) - is_ni) <= tol  # 법인세 부호 반대로 저장
        verdict = (
            "ok" if std_ok else ("tax_sign_inconsistent" if flip_ok else "discontinued_or_other")
        )
        out["손익항등식"] = {
            "pre_tax": m(pre),
            "tax": m(tax),
            "ni": m(is_ni),
            "std_diff": m((pre - tax) - is_ni),
            "verdict": verdict,
        }
    # SCE roll-forward: 기초자본 marker + Σ변동 marker = 자본총계 marker
    if not sce.empty:
        fsmark = "연결재무제표" if fs == "CFS" else "별도재무제표"
        mk = sce[(sce["fs_div"] == fs) & (sce["component_std"] == fsmark)].copy()
        mk["amt"] = pd.to_numeric(mk["amount"], errors="coerce")
        begin = mk[mk["change_canonical"] == "기초자본"]["amt"].sum()
        end = mk[mk["change_canonical"] == "자본총계"]["amt"].sum()
        moves = mk[~mk["change_canonical"].isin(["기초자본", "자본총계"])]["amt"].sum()
        # 부호 진단: 자본 차감변동(배당·자기주식)이 양수로 저장되면 단순합 roll-forward 불성립
        deduct = mk[mk["change_canonical"].isin(["배당변동", "자기주식변동"])]
        bad_sign = [
            f"{r['change_canonical']}={m(r['amt'])}"
            for _, r in deduct.iterrows()
            if pd.notna(r["amt"]) and r["amt"] > 0
        ]
        if begin or end:
            out["SCE_rollforward"] = {
                "begin": m(begin),
                "moves": m(moves),
                "end": m(end),
                "diff": m(end - (begin + moves)),
                "positive_deductions": bad_sign,  # 양수면 부호규약 위반 후보
            }
    return out


def audit_C(nf, subtotals):
    """C 소계 이중계상·is_subtotal 식별."""
    present = set(nf["canonical"].unique())
    sub_present = sorted(present & subtotals)
    # 소계와 구성 동시 존재(정상: 둘 다 게시) — is_subtotal 식별 가능 여부 확인
    has_components = bool(present - subtotals - {"기타 중요 계정"})
    return {"subtotals_present": sub_present, "has_line_components": has_components}


def audit_D(nf, fs):
    """D 부호 일관성·source-scale 이상치."""
    signs = {}
    for c in COST_CANONICALS:
        v = canon(nf, c, fs)
        if v is not None:
            signs[c] = "음수" if v < 0 else ("0" if v == 0 else "양수")
    # source-scale 이상치: 비소계 line item이 자산총계 초과(단위혼입 의심)
    tot = canon(nf, "자산총계", fs)
    outliers = []
    if tot and tot > 0:
        sub = nf[(nf["fs_div"] == fs) & (nf["canonical"] != "자산총계")]
        for _, r in sub.iterrows():
            a = pd.to_numeric(pd.Series([r["amount"]]), errors="coerce").iloc[0]
            if pd.notna(a) and abs(a) > tot * 5:  # 자산총계 5배 초과 = 비정상
                outliers.append(f"{r['canonical']}/{str(r['label'])[:14]}={m(a)}(자산{m(tot)})")
    return {"cost_signs": signs, "scale_outliers": outliers[:5]}


def audit_F(nf, std_ids):
    """F 가짜 exact·account_id 표준성."""
    exact = nf[nf["mapping_status"] == "exact_taxonomy_match"]
    fake = []
    for _, r in exact.iterrows():
        aid = str(r["account_id"])
        if not is_standard_account_id(aid):
            fake.append(f"{r['canonical']}/{str(r['label'])[:12]}/id={aid[:24]!r}")
    # exact인데 config 표준코드 집합에 없는 account_id(다른 의미의 표준코드일 수 있음·정보용)
    not_in_config = exact[~exact["account_id"].isin(std_ids)]["account_id"].nunique()
    return {
        "exact_total": int(len(exact)),
        "fake_exact_nonstd_id": fake[:8],
        "fake_count": len(fake),
        "exact_id_not_in_config": int(not_in_config),
    }


def audit_E(nf, sce, note, std_ids):
    """E provenance·note 매칭·Phase2 입력 행수."""
    prov_cols = [c for c in ("rcept_no", "ord", "source_file", "raw_line") if c in nf.columns]
    note_match = None
    if not note.empty and "concept" in note.columns:
        concepts = set(note["concept"].dropna().astype(str))
        matched = sum(1 for c in concepts if c in std_ids)
        note_match = {"note_concepts": len(concepts), "matched_to_canonical": matched}
    return {
        "provenance_cols": prov_cols,  # 비어있으면 raw 행 추적 불가
        "rows": {"normalized": int(len(nf)), "sce": int(len(sce)), "note": int(len(note))},
        "note_concept_match": note_match,
    }


def main():
    subtotals, std_ids = load_config()
    report: dict = {}
    # 회사간 비교가능성용 집계: canonical → {sj_div: corp set}
    cross: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    empty_silent = []

    for corp, name in TARGETS.items():
        cdir = BASE / corp
        years = (
            sorted(y.name for y in cdir.iterdir() if y.is_dir() and y.name.isdigit())
            if cdir.exists()
            else []
        )
        print(f"\n{'=' * 80}\n[{name} {corp}] 연도 {years}")
        company = {"name": name, "years": {}}
        for year in years:
            loaded = load_year(corp, year)
            raw_dir = cdir / year / "raw"
            has_raw = (raw_dir / "finstate_all_CFS.csv").exists() or (
                raw_dir / "finstate_all_OFS.csv"
            ).exists()
            if loaded is None:
                # raw finstate 있는데 정규화 산출 없음 = 무음 empty 후보
                if has_raw:
                    sz = max(
                        (raw_dir / f"finstate_all_{fs}.csv").stat().st_size
                        if (raw_dir / f"finstate_all_{fs}.csv").exists()
                        else 0
                        for fs in ("CFS", "OFS")
                    )
                    empty_silent.append(f"{name} {year}(raw최대 {sz}B)")
                    print(f"  {year}: 정규화 없음·raw finstate {sz}B → 무음 empty 후보")
                else:
                    print(f"  {year}: finstate_all CSV 부재(XBRL만) → 정규화 불가")
                continue
            nf, sce, note = loaded
            yd = {}
            for fs in ("CFS", "OFS"):
                if (nf["fs_div"] == fs).sum() == 0:
                    continue
                yd[fs] = {"B": audit_B(nf, sce, fs), "D": audit_D(nf, fs)}
            yd["C"] = audit_C(nf, subtotals)
            yd["F"] = audit_F(nf, std_ids)
            yd["E"] = audit_E(nf, sce, note, std_ids)
            company["years"][year] = yd
            # cross 집계
            for c, g in nf[nf["canonical"] != "기타 중요 계정"].groupby("canonical"):
                for sj in set(g["sj_div"]):
                    cross[c][sj].add(corp)
            # 콘솔 요약
            b_cfs = yd.get("CFS", {}).get("B", {})
            ident = []
            for k in ("자산총계", "부채총계"):
                if k in b_cfs:
                    ident.append(f"{k}diff={b_cfs[k]['diff']}")
            if "당기순이익" in b_cfs:
                ident.append(
                    f"순이익{b_cfs['당기순이익']['values']}d={b_cfs['당기순이익']['max_diff']}"
                )
            if "SCE_rollforward" in b_cfs:
                ident.append(f"SCE롤diff={b_cfs['SCE_rollforward']['diff']}")
            f = yd["F"]
            e = yd["E"]
            r = e["rows"]
            print(
                f"  {year}: norm{r['normalized']} sce{r['sce']} note{r['note']}"
                f" | exact{f['exact_total']} 가짜{f['fake_count']}"
            )
            if ident:
                print(f"      [B-CFS] {' | '.join(str(x) for x in ident)}")
            d_cfs = yd.get("CFS", {}).get("D", {})
            if d_cfs.get("cost_signs"):
                nout = len(d_cfs.get("scale_outliers", []))
                print(f"      [D] 부호 {d_cfs['cost_signs']} 이상치{nout}")
            if f["fake_count"]:
                print(f"      [F] 가짜exact {f['fake_exact_nonstd_id'][:3]}")
            if e["note_concept_match"]:
                print(f"      [E] note {e['note_concept_match']}")
        report[corp] = company

    # 회사간 비교가능성: 한 canonical이 회사마다 다른 sj_div로 매핑되는 경우
    print(
        f"\n{'=' * 80}\n[C 회사간 비교가능성] canonical별 sj_div 분기(여러 statement에 걸친 경우)"
    )
    incomparable = {}
    for c, sjmap in sorted(cross.items()):
        sjs = {sj for sj in sjmap if sj}
        if len(sjs - {"IS", "CIS"}) > 1 or (len(sjs) > 1 and not sjs <= {"IS", "CIS"}):
            incomparable[c] = {sj: sorted(s) for sj, s in sjmap.items()}
    for c, v in list(incomparable.items())[:30]:
        print(f"  {c}: {v}")
    report["_cross_incomparable"] = incomparable
    report["_silent_empty"] = empty_silent

    out = Path("data/backtest/_p1_audit2.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n무음 empty: {empty_silent}")
    print(f"회사간 비교불가 canonical 수: {len(incomparable)}")
    print(f"\n[저장] {out}")


if __name__ == "__main__":
    main()
