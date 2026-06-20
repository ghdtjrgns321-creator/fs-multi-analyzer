"""E2E 감사 심화 — 숫자 정합(raw finstate 금액 ↔ normalized canonical 금액) + 소실 funnel.

회사별: 핵심계정 raw 금액 ↔ norm 금액 1:1, raw행→norm행 funnel, 미출현(소실) 행 목록.
실행: PYTHONPATH=. uv run python -m data.backtest._e2e_reconcile
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from config.settings import settings
from src.db.normalized import db_path

OUT = Path("data/backtest/_e2e_reconcile.json")

# (회사, 대조연도) — 수집한 최신연도
TARGETS = [
    ("대형다각화", "00126380", 2024),
    ("금융지주", "00688996", 2024),
    ("자본거래多", "00258801", 2024),
    ("정정본", "00117212", 2024),
    ("구포맷", "00356361", 2017),
    ("소형단순", "00160375", 2024),
]

# 핵심계정 = (라벨, IFRS concept account_id, 허용 sj_div). 계정명 변형(당기순이익(손실))·
# IS↔CIS 차이를 흡수하려 account_id(개념)로 매칭. SCE 다중행은 본표 그룹만 보므로 자연 배제.
# account_id는 신택소노미(ifrs-full_X)·구택소노미(ifrs_X, ~2017) 둘 다 허용.
CORE = [
    ("자산총계", ("ifrs-full_Assets", "ifrs_Assets"), ("BS",)),
    ("부채총계", ("ifrs-full_Liabilities", "ifrs_Liabilities"), ("BS",)),
    ("자본총계", ("ifrs-full_Equity", "ifrs_Equity"), ("BS",)),
    ("매출액", ("ifrs-full_Revenue", "ifrs_Revenue"), ("IS", "CIS")),
    ("영업이익", ("dart_OperatingIncomeLoss",), ("IS", "CIS")),
    ("당기순이익", ("ifrs-full_ProfitLoss", "ifrs_ProfitLoss"), ("IS", "CIS")),
]


def _num(v) -> float | None:
    s = str(v).replace(",", "").strip()
    if s in ("", "nan", "None", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _raw_amount_by_id(raw: pd.DataFrame, aids: tuple, sj_allowed: tuple) -> float | None:
    """raw finstate에서 account_id(개념·신구택소노미) + 허용 sj_div 당기금액(본표). SCE 제외."""
    m = raw[(raw["account_id"].isin(aids)) & (raw["sj_div"].isin(sj_allowed))]
    vals = [n for n in (_num(v) for v in m["thstrm_amount"]) if n is not None]
    if not vals:
        return None
    return max(vals, key=abs)


def _raw_amount(raw: pd.DataFrame, sj: str, nm: str) -> float | None:
    """레거시(소실 funnel 라벨 금액용) — (sj_div, account_nm) 당기금액."""
    m = raw[(raw["sj_div"] == sj) & (raw["account_nm"] == nm)]
    vals = [n for n in (_num(v) for v in m["thstrm_amount"]) if n is not None]
    return max(vals, key=abs) if vals else None


def _load_raw(corp: str, year: int) -> pd.DataFrame:
    root = settings.data_dir
    frames = []
    for div in ("CFS", "OFS"):
        p = root / corp / str(year) / "raw" / f"finstate_all_{div}.csv"
        if p.exists() and p.stat().st_size > 0:
            try:
                df = pd.read_csv(p, dtype=str)
            except pd.errors.EmptyDataError:
                continue
            if len(df):
                df["_fs_div"] = div
                frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    results = []
    for dim, corp, year in TARGETS:
        raw = _load_raw(corp, year)
        con = duckdb.connect(str(db_path(corp, year, settings.data_dir)), read_only=True)
        norm = con.execute("select * from normalized_financials").fetchdf()
        con.close()

        # 우선 fs_div: CFS 있으면 CFS, 없으면 OFS (primary)
        primary = "CFS" if (raw.get("_fs_div") == "CFS").any() else "OFS"
        raw_p = raw[raw["_fs_div"] == primary] if "_fs_div" in raw else raw
        norm_p = norm[norm["fs_div"] == primary]

        # 1) 핵심계정 금액 대조 — account_id(개념) 기반(계정명 변형·IS↔CIS 흡수)
        recon = []
        for label, aids, sj_allowed in CORE:
            rv = _raw_amount_by_id(raw_p, aids, sj_allowed)
            nm_rows = norm_p[
                (norm_p["account_id"].isin(aids)) & (norm_p["sj_div"].isin(sj_allowed))
            ]
            nv = None
            if not nm_rows.empty:
                nv = max((float(x) for x in nm_rows["amount"].dropna()), key=abs, default=None)
            status = "n/a"
            if rv is not None and nv is not None:
                status = "match" if round(rv) == round(nv) else "MISMATCH"
            elif rv is not None and nv is None:
                status = "norm_missing"
            elif rv is None and nv is not None:
                status = "raw_missing"
            recon.append({"acct": label, "id": aids[0], "raw": rv, "norm": nv, "status": status})

        # 2) 소실 funnel — primary 본표(BS/IS/CIS/CF) raw 고유계정 vs norm
        body = raw_p[raw_p["sj_div"].isin(["BS", "IS", "CIS", "CF"])]
        raw_keys = set(
            zip(body["sj_div"], body["account_id"].fillna(""), body["account_nm"].fillna(""))
        )
        norm_body = norm_p[norm_p["sj_div"].isin(["BS", "IS", "CIS", "CF"])]
        norm_ids = set(norm_body["account_id"].fillna("").tolist())
        norm_labels = set(norm_body["label"].fillna("").tolist())
        missing = []
        for sj, aid, anm in raw_keys:
            if aid and aid in norm_ids:
                continue
            if anm and anm in norm_labels:
                continue
            amt = _raw_amount(
                body[
                    (body["account_id"].fillna("") == aid) & (body["account_nm"].fillna("") == anm)
                ],
                sj,
                anm,
            )
            missing.append({"sj": sj, "id": aid, "nm": anm, "amt": amt})
        missing.sort(key=lambda d: abs(d["amt"]) if d["amt"] else 0, reverse=True)

        results.append(
            {
                "dim": dim,
                "corp": corp,
                "year": year,
                "primary": primary,
                "raw_rows_primary": int(len(raw_p)),
                "raw_body_unique": len(raw_keys),
                "norm_rows_primary": int(len(norm_p)),
                "recon": recon,
                "missing_count": len(missing),
                "missing_top": missing[:15],
            }
        )
        mism = [r for r in recon if r["status"] not in ("match", "n/a")]
        print(
            f"[{dim}] {corp} {year} primary={primary} raw={len(raw_p)} norm={len(norm_p)} "
            f"미스매치={len(mism)} 소실후보={len(missing)}",
            flush=True,
        )
        for r in mism:
            print(
                f"    ! {r['acct']}: raw={r['raw']} norm={r['norm']} {r['status']}",
                flush=True,
            )

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
