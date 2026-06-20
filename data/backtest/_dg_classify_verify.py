"""주석 분류기 검증: 2개 회사 분류 분포 + 고가치 카테고리 실증 + 기존 indexer 무손상."""

from __future__ import annotations

from pathlib import Path

from src.normalize.notes_classify import classify_company_year, load_note_taxonomy
from src.notes.indexer import load_account_note_mappings

tax = load_note_taxonomy()
print(
    f"카테고리 {len(tax.categories)}종, meta_tokens {len(tax.meta_tokens)}, "
    f"canonical stem {len(tax.canon_stems)}, 우선 {len(tax.high_priority)}\n"
)

# 차입금 풍부 대형사 + 분식사
CASES = [("대형사", "00102858"), ("두산에너빌리티", "00159616"), ("아스트", "00409681")]
for name, corp in CASES:
    base = Path("data/companies") / corp
    if not base.exists():
        print(f"[{name} {corp}] 데이터 없음")
        continue
    years = sorted(p.name for p in base.iterdir() if p.is_dir())
    for y in years:
        df = classify_company_year(corp, y)
        if df.empty:
            continue
        dist = df["bucket"].value_counts().to_dict()
        cats = df[df["bucket"] == "detail"]["category"].value_counts()
        print(f"[{name} {corp} {y}] {len(df)}행  {dist}")
        print(f"   detail 카테고리 상위: {dict(list(cats.items())[:6])}")
        # 고가치 카테고리 실증(차입금조건)
        bor = df[df["category"] == "차입금조건"].head(3)
        for _, r in bor.iterrows():
            print(
                f"   [차입금조건] {r['concept'][:45]:45s} {str(r['label_ko'])[:18]:18s} = {r['value']}"
            )
        break  # 회사당 1개 연도만
print("\n기존 indexer account_notes 무손상:", sorted(load_account_note_mappings().keys()))
