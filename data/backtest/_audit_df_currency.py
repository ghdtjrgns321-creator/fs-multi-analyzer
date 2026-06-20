"""D-F: USD 등 외화 보고 회사 전수 식별 (읽기전용).

원천: data/companies/{corp}/{year}/raw/finstate_all_{CFS,OFS}.csv
fs_div 는 파일명(CFS/OFS)에서, sj_div 는 열에서 취득.
벡터화: 각 CSV 를 한 번에 읽어 필요한 4열만 추출 후 concat.
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("data/companies")
OUT_DIR = Path("data/backtest")
USECOLS = ["corp_code", "bsns_year", "sj_div", "currency", "account_nm", "thstrm_amount"]

# 1) 전수 스캔 -------------------------------------------------------------
frames = []
files = sorted(ROOT.glob("*/*/raw/finstate_all_*.csv"))
print(f"[scan] finstate csv files: {len(files)}", file=sys.stderr)
n_read = 0
n_err = 0
for fp in files:
    fs_div = (
        "CFS"
        if fp.name.endswith("_CFS.csv")
        else ("OFS" if fp.name.endswith("_OFS.csv") else "OTHER")
    )
    try:
        df = pd.read_csv(
            fp,
            usecols=USECOLS,
            dtype=str,
            encoding="utf-8-sig",
            on_bad_lines="skip",
            low_memory=False,
        )
    except Exception:  # 빈/깨진 파일 방어
        n_err += 1
        continue
    if df.empty:
        continue
    df["fs_div"] = fs_div
    frames.append(df)
    n_read += 1

print(f"[scan] read ok={n_read} err={n_err}", file=sys.stderr)
alldf = pd.concat(frames, ignore_index=True)
print(f"[scan] total rows={len(alldf)}", file=sys.stderr)

# currency 정규화 (공백/대문자)
alldf["currency"] = alldf["currency"].fillna("").str.strip().str.upper()
alldf.loc[alldf["currency"] == "", "currency"] = "(blank)"

# 2) 통화 분포 (전수 분모) ------------------------------------------------
cur_dist = alldf["currency"].value_counts(dropna=False)
total_rows = len(alldf)

# 3) 외화(KRW 아닌, blank 제외) 행 ---------------------------------------
foreign = alldf[~alldf["currency"].isin(["KRW", "(blank)"])].copy()
print(
    f"[foreign] rows={len(foreign)} currencies={sorted(foreign['currency'].unique())}",
    file=sys.stderr,
)


# thstrm_amount 숫자화 (규모용)
def to_num(s):
    return pd.to_numeric(
        s.astype(str).str.replace(",", "", regex=False).str.replace(" ", "", regex=False),
        errors="coerce",
    )


foreign["amt"] = to_num(foreign["thstrm_amount"])

# 회사·연도·fs_div·sj_div·통화 단위 행수
grp = (
    foreign.groupby(["corp_code", "bsns_year", "fs_div", "sj_div", "currency"], dropna=False)
    .agg(rows=("currency", "size"), max_abs_amt=("amt", lambda x: x.abs().max()))
    .reset_index()
)

# 회사 단위 요약: 연도·통화·재무제표·대표 규모
comp = (
    foreign.groupby(["corp_code", "currency"], dropna=False)
    .agg(
        years=("bsns_year", lambda x: ",".join(sorted(set(x.astype(str))))),
        fs_divs=("fs_div", lambda x: ",".join(sorted(set(x)))),
        sj_divs=("sj_div", lambda x: ",".join(sorted(set(x.astype(str))))),
        rows=("currency", "size"),
        max_abs_amt=("amt", lambda x: x.abs().max()),
    )
    .reset_index()
    .sort_values(["rows"], ascending=False)
)

# 4) 혼재(KRW+외화) 위험: 같은 corp_code 가 KRW 와 외화 둘 다 보고? -------
cur_by_corp = alldf.groupby("corp_code")["currency"].apply(lambda x: set(x.unique()))
mixed = {}
for corp, curset in cur_by_corp.items():
    nonblank = {c for c in curset if c != "(blank)"}
    has_krw = "KRW" in nonblank
    has_foreign = bool(nonblank - {"KRW"})
    if has_krw and has_foreign:
        mixed[corp] = sorted(nonblank)
print(f"[mixed] corps with KRW+foreign mix = {len(mixed)}", file=sys.stderr)

# 외화 회사 corp_code 집합
foreign_corps = sorted(foreign["corp_code"].unique())

# 5) 회사명 보강 (DART corp codes pkl) ------------------------------------
name_map = {}
pkl = Path("docs_cache/opendartreader_corp_codes_20260607.pkl")
if pkl.exists():
    try:
        cc = pd.read_pickle(pkl)
        # 컬럼 추정
        code_col = next((c for c in cc.columns if "corp_code" in c.lower()), None)
        name_col = next(
            (
                c
                for c in cc.columns
                if "corp_name" in c.lower() or c.lower() == "name" or "corp_nm" in c.lower()
            ),
            None,
        )
        if code_col and name_col:
            cc2 = cc[[code_col, name_col]].dropna()
            cc2[code_col] = cc2[code_col].astype(str).str.zfill(8)
            name_map = dict(zip(cc2[code_col], cc2[name_col]))
        print(
            f"[name] pkl cols={list(cc.columns)} code={code_col} name={name_col} "
            f"mapped={len(name_map)}",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"[name] pkl load fail: {e}", file=sys.stderr)


def corp_name(code):
    return name_map.get(str(code).zfill(8), "")


# 6) JSON 결과 저장 -------------------------------------------------------
result = {
    "total_rows": int(total_rows),
    "currency_distribution": {k: int(v) for k, v in cur_dist.items()},
    "foreign_rows": int(len(foreign)),
    "foreign_currencies": {c: int(n) for c, n in foreign["currency"].value_counts().items()},
    "foreign_corp_count": len(foreign_corps),
    "mixed_corp_count": len(mixed),
    "mixed_corps": {
        c: name_map.get(c, "")
        and {"name": name_map.get(c, ""), "currencies": v}
        or {"name": "", "currencies": v}
        for c, v in mixed.items()
    },
}
with open(OUT_DIR / "_audit_df_currency.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# group / comp 표 CSV 로도 저장
grp["corp_name"] = grp["corp_code"].map(corp_name)
comp["corp_name"] = comp["corp_code"].map(corp_name)
grp.to_csv(OUT_DIR / "_audit_df_currency_group.csv", index=False, encoding="utf-8-sig")
comp.to_csv(OUT_DIR / "_audit_df_currency_company.csv", index=False, encoding="utf-8-sig")

# stdout 요약
print("=== CURRENCY DISTRIBUTION (전수 분모) ===")
print(f"total rows: {total_rows}")
for k, v in cur_dist.items():
    print(f"  {k:10s} {v:>10,}  ({v / total_rows * 100:.3f}%)")
print(f"\nforeign(=非KRW,非blank) rows: {len(foreign)}")
print(f"foreign corp count: {len(foreign_corps)}")
print(f"mixed (KRW+foreign) corp count: {len(mixed)}")
print("\n=== TOP foreign companies (rows) ===")
for _, r in comp.head(40).iterrows():
    nm = corp_name(r["corp_code"]) or "?"
    print(
        f"  {r['corp_code']} {nm[:18]:18s} {r['currency']:4s} yr={r['years']} "
        f"fs={r['fs_divs']} sj={r['sj_divs']} rows={r['rows']} "
        f"max|amt|={r['max_abs_amt']}"
    )
