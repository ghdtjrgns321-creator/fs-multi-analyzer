"""원장(_P1_DEFECT_LEDGER.md) 심각도 높음 결함을 현재 코드로 재정규화해 live/fixed 판정.

stale duckdb 불신 — normalize_company_year로 즉석 재현. 결함별 시그니처를 코드로 검사.
출력: 각 결함 corp/year/판정(LIVE/FIXED/UNCLEAR) + 근거 수치.
실행: PYTHONPATH=. uv run python data/backtest/_p1_ledger_livecheck.py
"""

from __future__ import annotations

from src.normalize.pipeline import normalize_company_year, sce_components_company_year


def _rows(df, label_sub=None, canon=None):
    sub = df
    if label_sub is not None:
        sub = sub[sub["label"].astype(str).str.contains(label_sub, na=False)]
    if canon is not None:
        sub = sub[sub["canonical"] == canon]
    return sub


def check(corp, year, fn):
    try:
        df = normalize_company_year(corp, year)
    except Exception as exc:  # noqa: BLE001
        return f"ERROR {type(exc).__name__}: {exc}"
    if df is None or not len(df):
        return "EMPTY(원천부재?)"
    return fn(df)


def d1_balsa(df):  # 00148504/2025 발행사채증가→주식발행
    r = _rows(df, label_sub="발행사채의 증가")
    if not len(r):
        return "라벨부재"
    canon = set(r["canonical"])
    live = any("주식" in c for c in canon)
    return f"{'LIVE' if live else 'FIXED'} — 발행사채의증가 canonical={canon}"


def d2_finbs(df):  # 00176914/2023 금융업 2부문 BS 항등식
    has_fin = any(("금융업자산" in c or "금융업부채" in c) for c in df["canonical"].astype(str))
    bs = df[df["sj_div"] == "BS"]
    assets = bs[bs["canonical"] == "자산총계"]["amount"]
    a = float(assets.iloc[0]) if len(assets) else None
    return (
        f"{'FIXED' if has_fin else 'LIVE'} — 금융업자산/부채 canonical 존재={has_fin}, 자산총계={a:,.0f}"
        if a
        else f"금융업canon={has_fin}"
    )


def d3_htm(df):  # 00264945 만기보유←FVPL (취득)
    r = _rows(df, label_sub="당기손익-공정가치측정금융자산의 취득")
    if not len(r):
        return "라벨부재"
    canon = set(r["canonical"])
    live = any("만기보유" in c for c in canon)
    return f"{'LIVE' if live else 'FIXED'} — canonical={canon}"


def d_capital_gt_total(df):  # 자본금 > 자본총계 (00428729, 01573284)
    bs = df[df["sj_div"] == "BS"]
    cap = bs[bs["canonical"] == "자본금"]["amount"]
    tot = bs[bs["canonical"] == "자본총계"]["amount"]
    if not len(cap) or not len(tot):
        return f"계정부재 자본금={len(cap)} 자본총계={len(tot)}"
    cmax, tmax = float(cap.max()), float(tot.max())
    live = cmax > tmax
    return f"{'LIVE' if live else 'FIXED'} — 자본금={cmax:,.0f} {'>' if live else '<='} 자본총계={tmax:,.0f}"


def d_sales_eq_oi(df):  # 00545716 영업이익=영업수익, 매출 부재
    has_sales = "매출" in set(df["canonical"])
    oi = df[df["canonical"] == "영업이익"]["amount"]
    oimax = float(oi.max()) if len(oi) else None
    live = not has_sales
    return (
        f"{'LIVE' if live else 'FIXED'} — 매출canonical존재={has_sales}, 영업이익max={oimax:,.0f}"
        if oimax
        else f"매출={has_sales}"
    )


def d_invprop(df):  # 01089378/2025 투자부동산취득 유령
    r = _rows(df, label_sub="단기금융상품의 취득")
    if not len(r):
        return "라벨부재"
    canon = set(r["canonical"])
    live = any("투자부동산" in c for c in canon)
    return f"{'LIVE' if live else 'FIXED'} — 단기금융상품의취득 canonical={canon}"


def d_fakeexact(df):  # 01406618/2022 CF 가짜 exact
    r = _rows(df, label_sub="단기금융상품의 증가")
    if not len(r):
        return "라벨부재"
    pairs = set(zip(r["canonical"], r["mapping_status"]))
    live = any(("단기금융" not in c) for c, _ in pairs)
    return f"{'LIVE' if live else 'FIXED'} — 단기금융상품의증가 (canonical,status)={pairs}"


def d_sce_sign(corp, year):  # 00298687 OFS SCE 이익잉여금 member 부호
    try:
        sce = sce_components_company_year(corp, year)
    except Exception as exc:  # noqa: BLE001
        return f"ERROR {type(exc).__name__}: {exc}"
    if sce is None or not len(sce):
        return "SCE EMPTY"
    cols = list(sce.columns)
    ie = sce[
        sce.astype(str).apply(lambda r: r.str.contains("이익잉여금|결손", na=False).any(), axis=1)
    ]
    return f"SCE rows cols={cols}; 이익잉여금관련 {len(ie)}행 (수동확인 — 부호컬럼 점검)"


TASKS = [
    ("00148504", 2025, "발행사채→주식발행", lambda: check("00148504", 2025, d1_balsa)),
    ("00176914", 2023, "금융업2부문BS", lambda: check("00176914", 2023, d2_finbs)),
    ("00264945", 2021, "만기보유←FVPL", lambda: check("00264945", 2021, d3_htm)),
    ("00264945", 2023, "만기보유←FVPL", lambda: check("00264945", 2023, d3_htm)),
    ("00298687", 2022, "SCE이익잉여금부호", lambda: d_sce_sign("00298687", 2022)),
    ("00428729", 2025, "자본금>자본총계", lambda: check("00428729", 2025, d_capital_gt_total)),
    ("00428729", 2021, "자본금>자본총계", lambda: check("00428729", 2021, d_capital_gt_total)),
    ("00545716", 2021, "영업이익=매출", lambda: check("00545716", 2021, d_sales_eq_oi)),
    ("00545716", 2022, "영업이익=매출", lambda: check("00545716", 2022, d_sales_eq_oi)),
    ("01089378", 2025, "투자부동산유령", lambda: check("01089378", 2025, d_invprop)),
    ("01406618", 2022, "CF가짜exact", lambda: check("01406618", 2022, d_fakeexact)),
    ("01573284", 2022, "자본금6배(소계점유)", lambda: check("01573284", 2022, d_capital_gt_total)),
    ("01573284", 2023, "자본금6배(소계점유)", lambda: check("01573284", 2023, d_capital_gt_total)),
]

if __name__ == "__main__":
    print("=== P1 원장 높음 결함 live/fixed 판정 (현재 코드 재정규화) ===\n")
    live = fixed = other = 0
    for corp, year, name, fn in TASKS:
        res = fn()
        tag = (
            "LIVE"
            if res.startswith("LIVE")
            or " LIVE" in res
            or res.startswith("ERROR") is False
            and res.startswith("LIVE")
            else ""
        )
        if res.startswith("LIVE"):
            live += 1
        elif res.startswith("FIXED"):
            fixed += 1
        else:
            other += 1
        print(f"[{corp}/{year}] {name}\n    → {res}\n")
    print(f"=== 집계: LIVE={live}  FIXED={fixed}  OTHER(수동/부재)={other} / 총 {len(TASKS)} ===")
