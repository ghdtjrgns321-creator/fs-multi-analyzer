"""거시 구조 전수 인벤토리 (read-only).

사업보고서를 '어떻게 쪼개서 분류할 것인가'의 입력 공간을 전 회사 raw에서 전수로 본다.
정규화/매핑 없이 원천 구조 차원만 집계. 목적: 거시 분류 설계 입력(수정·설계는 다음 단계).

차원:
  1. fs_div(연결/별도) × sj_div(BS/IS/CIS/CF/SCE) 행렬
  2. account_detail 종류(plain '-' / [member] / [구성요소] / 기타) — 차원(분해축) 규모
  3. currency(단위/통화) 분포
  4. 기간컬럼 충전율(thstrm/frmtrm/bfefrmtrm/thstrm_add) — 비교기간 가용성
  5. SCE 자본구성요소 축(구성요소 라벨 distinct) — SCE 2D 매트릭스 열
  6. 주석 디렉터리(raw/notes/{CFS,OFS}) 유무·파일수
  7. reprt_code distinct
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

BASE = Path("data/companies")
OUT = Path("data/backtest/_audit_macro_structure.json")
COMP_RE = re.compile(r"([^|]+?)\s*\[구성요소\]")


def detail_kind(detail: str) -> str:
    d = str(detail or "").strip()
    if d in ("-", ""):
        return "plain"
    if "[member]" in d:
        return "member"
    if "[구성요소]" in d:
        return "구성요소"
    return "기타detail"


def nonempty(s: pd.Series) -> int:
    return int(s.fillna("").astype(str).str.strip().replace("nan", "").ne("").sum())


def main() -> None:
    companies = files = 0
    years: set = set()
    sj_fs: Counter = Counter()  # (fs_div, sj_div) -> rows
    detail_by_sj: dict = {}  # sj_div -> Counter(detail_kind)
    currency: Counter = Counter()
    reprt: Counter = Counter()
    period_fill = {"thstrm": 0, "frmtrm": 0, "bfefrmtrm": 0, "thstrm_add": 0}
    rows_all = 0
    sce_components: Counter = Counter()  # SCE 구성요소 라벨
    notes_present = {"CFS": 0, "OFS": 0}
    notes_files: Counter = Counter()  # note 파일수 버킷
    company_year_with_notes = 0

    corp_dirs = sorted(d for d in BASE.iterdir() if d.is_dir() and d.name.isdigit())
    import os

    _lim = int(os.environ.get("LIMIT", "0"))
    if _lim:
        corp_dirs = corp_dirs[:_lim]

    for cdir in corp_dirs:
        companies += 1
        for ydir in sorted(cdir.iterdir()):
            if not (ydir.is_dir() and ydir.name.isdigit()):
                continue
            has_notes = False
            for fs in ("CFS", "OFS"):
                p = ydir / "raw" / f"finstate_all_{fs}.csv"
                if p.exists() and p.stat().st_size > 5:
                    try:
                        df = pd.read_csv(p, dtype=str)
                    except Exception:
                        df = None
                    if df is not None and "sj_div" in df.columns:
                        files += 1
                        years.add((cdir.name, ydir.name))
                        rows_all += len(df)
                        for sj, c in Counter(df["sj_div"].fillna("∅")).items():
                            sj_fs[(fs, sj)] += c
                        dk = (
                            df["account_detail"].map(detail_kind)
                            if "account_detail" in df
                            else None
                        )
                        if dk is not None:
                            for sj in df["sj_div"].fillna("∅").unique():
                                sub = dk[df["sj_div"] == sj]
                                d = detail_by_sj.setdefault(sj, Counter())
                                for k, n in Counter(sub).items():
                                    d[k] += n
                            # SCE 구성요소 라벨
                            sce = df[
                                (df["sj_div"] == "SCE")
                                & df["account_detail"]
                                .astype(str)
                                .str.contains("구성요소", na=False)
                            ]
                            for det in sce["account_detail"].astype(str):
                                for m in COMP_RE.findall(det):
                                    sce_components[m.strip()] += 1
                        if "currency" in df:
                            for cur, n in Counter(df["currency"].fillna("∅")).items():
                                currency[cur] += n
                        if "reprt_code" in df:
                            for rc, n in Counter(df["reprt_code"].fillna("∅")).items():
                                reprt[rc] += n
                        for col, key in (
                            ("thstrm_amount", "thstrm"),
                            ("frmtrm_amount", "frmtrm"),
                            ("bfefrmtrm_amount", "bfefrmtrm"),
                            ("thstrm_add_amount", "thstrm_add"),
                        ):
                            if col in df:
                                period_fill[key] += nonempty(df[col])
                # 주석 디렉터리
                ndir = ydir / "raw" / "notes" / fs
                if ndir.exists():
                    nfiles = sum(1 for _ in ndir.glob("*"))
                    if nfiles:
                        notes_present[fs] += 1
                        has_notes = True
                        notes_files[min(nfiles, 20)] += 1
            if has_notes:
                company_year_with_notes += 1

    out = {
        "coverage": {
            "companies": companies,
            "files": files,
            "company_years": len(years),
            "rows_all_raw": rows_all,
        },
        "fs_sj_matrix": {f"{fs}/{sj}": n for (fs, sj), n in sorted(sj_fs.items())},
        "detail_kind_by_sj": {sj: dict(c) for sj, c in sorted(detail_by_sj.items())},
        "currency": dict(currency.most_common(20)),
        "reprt_code": dict(reprt),
        "period_fill_rows": period_fill,
        "period_fill_pct": {
            k: round(100 * v / max(rows_all, 1), 1) for k, v in period_fill.items()
        },
        "sce_components_top": dict(sce_components.most_common(40)),
        "sce_components_distinct": len(sce_components),
        "notes": {
            "company_years_with_notes": company_year_with_notes,
            "by_fs": notes_present,
            "files_per_dir_bucket": dict(sorted(notes_files.items())),
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    c = out["coverage"]
    print(
        f"companies={c['companies']} files={c['files']} cy={c['company_years']} rows={c['rows_all_raw']:,}"
    )
    print("\nfs/sj 행렬:")
    for k, n in out["fs_sj_matrix"].items():
        print(f"  {k:<10} {n:,}")
    print("\ndetail_kind by sj:")
    for sj, c2 in out["detail_kind_by_sj"].items():
        print(f"  {sj:<5} {c2}")
    print(f"\ncurrency: {out['currency']}")
    print(f"reprt_code: {out['reprt_code']}")
    print(f"period_fill_pct: {out['period_fill_pct']}")
    print(
        f"\nSCE 구성요소 distinct={out['sce_components_distinct']}, 상위: {list(out['sce_components_top'])[:12]}"
    )
    print(f"notes: {out['notes']}")
    print(f"\nJSON -> {OUT}")


if __name__ == "__main__":
    main()
