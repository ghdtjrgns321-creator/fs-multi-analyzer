"""P1 E2E 검증 S2+S3 — DART 원문 전수항목 추출 + normalized 생존 추적표.

S2 oracle: 선정 회사연도 raw CSV(CFS+OFS) 전 유효 계정행을 그대로 항목화(가공 없음).
S3 추적: oracle 각 항목이 normalized_financials에 어떻게 생존했는지 분류.
  [정확매핑]  canonical≠기타 + amount 일치
  [기타강등]  canonical=기타 중요 계정
  [금액불일치] 매칭 행 있으나 amount 다름
  [소실]      normalized에 매칭 행 없음(dedup/강등으로 증발 가능 — S4에서 정당성 판정)

추적표 행수 == oracle 항목수(원문 모든 행을 강제 나열 → 통독 사각 차단).
실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_trace.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import duckdb

from config.settings import settings
from src.db.normalized import db_path

ROOT = settings.data_dir
SAMPLE = Path("data/backtest/_p1e2e_sample.json")
OUT_DIR = Path("data/backtest")
OTHER = "기타 중요 계정"
PLACEHOLDER = {"-표준계정코드 미사용-", "", "nan", "none"}


def parse_amt(s: str | None) -> int | None:
    try:
        return round(float(s))
    except (TypeError, ValueError):
        return None


def amt_eq(a: int | None, b: int | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return round(float(a)) == round(float(b))


def load_oracle(corp: str, year: str) -> list[dict]:
    """raw CFS+OFS 전 유효 계정행(account_nm 있는 행). 원문 그대로."""
    rows: list[dict] = []
    ydir = ROOT / corp / str(year) / "raw"
    for fs in ("CFS", "OFS"):
        path = ydir / f"finstate_all_{fs}.csv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig") as f:
            for i, r in enumerate(csv.DictReader(f)):
                label = (r.get("account_nm") or "").strip()
                if not label:
                    continue
                rows.append(
                    {
                        "fs_div": fs,
                        "row": i,
                        "sj_div": (r.get("sj_div") or "").strip(),
                        "account_id": (r.get("account_id") or "").strip(),
                        "label": label,
                        "amount": parse_amt(r.get("thstrm_amount")),
                        "detail": (r.get("account_detail") or "").strip(),
                    }
                )
    return rows


def load_norm(corp: str, year: str) -> list[tuple]:
    path = db_path(corp, year, ROOT)
    if not path.exists():
        return []
    con = duckdb.connect(str(path), read_only=True)
    try:
        return con.execute(
            "SELECT fs_div, sj_div, canonical, account_id, label, amount, mapping_status "
            "FROM normalized_financials"
        ).fetchall()
    finally:
        con.close()


def load_sce(corp: str, year: str) -> list[tuple]:
    """SCE 2D 테이블(변동행 × 자본구성요소). 메인이 붕괴시킨 SCE는 여기 보존된다."""
    path = db_path(corp, year, ROOT)
    if not path.exists():
        return []
    con = duckdb.connect(str(path), read_only=True)
    try:
        return con.execute(
            "SELECT fs_div, change_label, component_std, amount FROM sce_equity_components"
        ).fetchall()
    finally:
        con.close()


def classify(oracle: list[dict], norm: list[tuple], sce: list[tuple]) -> list[dict]:
    # SCE 2D 보존 인덱스: amount로(0 아닌 것) + change_label 존재 집합(0 component용)
    sce_amt: set[tuple] = set()
    sce_labels: set[tuple] = set()
    for fs, change_label, _comp, amt in sce:
        sce_labels.add((fs, change_label))
        if amt is not None:
            # 차감변동(배당·감자)은 SCE 2D에 -abs로 보존됨 → 절대값으로 매칭
            sce_amt.add((fs, change_label, round(abs(float(amt)))))
    by_full: dict[tuple, list[tuple]] = {}
    by_label: dict[tuple, list[tuple]] = {}
    for nr in norm:
        fs, sj, _canon, aid, label, _amt, _st = nr
        aid = (aid or "").strip()
        by_full.setdefault((fs, sj, aid, label), []).append(nr)
        by_label.setdefault((fs, sj, label), []).append(nr)

    out: list[dict] = []
    for o in oracle:
        rec = dict(o)
        # SCE 행: 메인이 붕괴시키므로 2D 테이블에서 보존 확인(component 분해값)
        if o["sj_div"] == "SCE":
            amt = o["amount"]
            preserved = (o["fs_div"], o["label"]) in sce_labels and (
                amt in (None, 0) or (o["fs_div"], o["label"], round(abs(float(amt)))) in sce_amt
            )
            rec["verdict"] = "SCE보존" if preserved else "소실"
            rec["canonical"] = "(SCE 2D)" if preserved else None
            rec["norm_amount"] = None
            out.append(rec)
            continue
        is_ph = o["account_id"].lower() in PLACEHOLDER or o["account_id"] in PLACEHOLDER
        cands = (
            None if is_ph else by_full.get((o["fs_div"], o["sj_div"], o["account_id"], o["label"]))
        )
        if not cands:
            cands = by_label.get((o["fs_div"], o["sj_div"], o["label"]))
        # CIS 행: 손익·포괄손익 통합신고로 IS에 매핑될 수 있음(CIS→IS 호환)
        if not cands and o["sj_div"] == "CIS":
            cands = by_label.get((o["fs_div"], "IS", o["label"]))
        if not cands:
            rec["verdict"] = "소실"
            rec["canonical"] = None
            rec["norm_amount"] = None
        else:
            exact = [c for c in cands if c[2] != OTHER and amt_eq(c[5], o["amount"])]
            demoted = [c for c in cands if c[2] == OTHER]
            amt_match = [c for c in cands if amt_eq(c[5], o["amount"])]
            if exact:
                rec["verdict"] = "정확매핑"
                rec["canonical"] = exact[0][2]
                rec["norm_amount"] = exact[0][5]
            elif demoted and not amt_match:
                rec["verdict"] = "기타강등"
                rec["canonical"] = OTHER
                rec["norm_amount"] = demoted[0][5]
            elif demoted:
                rec["verdict"] = "기타강등"
                rec["canonical"] = OTHER
                rec["norm_amount"] = amt_match[0][5]
            else:
                rec["verdict"] = "금액불일치"
                rec["canonical"] = cands[0][2]
                rec["norm_amount"] = cands[0][5]
        out.append(rec)
    return out


def main() -> None:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    summary: list[dict] = []
    for s in sample:
        corp, year = s["corp"], s["year"]
        oracle = load_oracle(corp, year)
        norm = load_norm(corp, year)
        sce = load_sce(corp, year)
        traced = classify(oracle, norm, sce)

        (OUT_DIR / f"_p1e2e_oracle_{corp}_{year}.json").write_text(
            json.dumps(oracle, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        trace_path = OUT_DIR / f"_p1e2e_trace_{corp}_{year}.csv"
        with trace_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "fs_div",
                    "sj_div",
                    "account_id",
                    "label",
                    "amount",
                    "verdict",
                    "canonical",
                    "norm_amount",
                    "detail",
                ]
            )
            for t in traced:
                w.writerow(
                    [
                        t["fs_div"],
                        t["sj_div"],
                        t["account_id"],
                        t["label"],
                        t["amount"],
                        t["verdict"],
                        t["canonical"],
                        t["norm_amount"],
                        t["detail"],
                    ]
                )

        counts: dict[str, int] = {}
        for t in traced:
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
        rec = {
            "corp": corp,
            "year": year,
            "cell": s["cell"],
            "oracle_rows": len(oracle),
            "norm_rows": len(norm),
            "trace_rows": len(traced),
            **counts,
        }
        summary.append(rec)
        print(
            f"[{s['cell']}] {corp}/{year}: oracle={len(oracle)} norm={len(norm)} "
            f"trace={len(traced)} | {counts}",
            flush=True,
        )

    (OUT_DIR / "_p1e2e_trace_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # 게이트: 추적표 행수 == oracle 항목수
    ok = all(r["trace_rows"] == r["oracle_rows"] for r in summary)
    print(f"\n추적표 행수 == oracle 항목수: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
