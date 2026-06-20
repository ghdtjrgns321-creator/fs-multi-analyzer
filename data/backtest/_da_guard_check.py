"""이질병합 가드: 분식사 핵심계정이 등록 후에도 보존되는지·미분류 감소 확인."""

from __future__ import annotations

from src.normalize.pipeline import normalize_company_year

CASES = [
    ("아스트", "00409681", 2019, ["재고자산", "매출원가", "자기자본", "자본총계"]),
    ("두산에너빌리티", "00159616", 2018, ["계약자산", "매출원가", "수익", "재고자산"]),
]
for name, corp, year, core in CASES:
    df = normalize_company_year(corp, year)
    n_other = int((df["canonical"] == "기타 중요 계정").sum())
    n_mapped = int((df["canonical"] != "기타 중요 계정").sum())
    print(f"\n[{name} {corp} {year}] 분류={n_mapped} 기타={n_other} 총={len(df)}")
    for c in core:
        sub = df[df["canonical"] == c]
        amts = list(sub["amount"])[:2]
        print(f"   {c}: {len(sub)}행 amount={amts}")
    # 새 D-A canonical(CF조정/SCE 등)이 실제로 잡혔는지 표본
    sce = df[df["sj_div"] == "SCE"]
    cf = df[df["sj_div"] == "CF"]
    print(
        f"   SCE분류={int((sce['canonical'] != '기타 중요 계정').sum())}/{len(sce)}  "
        f"CF분류={int((cf['canonical'] != '기타 중요 계정').sum())}/{len(cf)}"
    )
