"""프로덕션 분류기 정합성: 표본 전체 bucket% 가 survey(_dg_canonical_reuse)와 일치하는지.

분류 로직을 별도 구현(survey)이 아니라 src.normalize.notes_classify로 재집계 → 일치하면 무버그.
+ 풍부한 연도(2024) 실증으로 차입금/특수관계자 등 고가치 카테고리 분류 확인.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from src.normalize.notes_classify import (
    classify_note_facts,
    load_note_taxonomy,
    read_note_facts,
)

BASE = Path("data/companies")
SAMPLE = 400
tax = load_note_taxonomy()

files = []
for corp in sorted(BASE.iterdir()):
    if corp.is_dir():
        for yr in sorted(corp.iterdir()):
            t = yr / "raw" / "notes_xbrl" / "note_facts.tsv"
            if t.exists():
                files.append(t)
step = max(1, len(files) // SAMPLE)
sample = files[::step][:SAMPLE]

bucket = Counter()
cat = Counter()
for t in sample:
    df = classify_note_facts(read_note_facts(t), tax)
    bucket.update(df["bucket"].tolist())
    cat.update(df[df["bucket"] == "detail"]["category"].tolist())
total = sum(bucket.values())
print(f"표본 {len(sample)} 총 {total}행 — 프로덕션 분류기 집계")
for b in ("흡수", "메타", "detail", "기타주석"):
    print(f"  {b}: {bucket[b]:>8} ({bucket[b] / total * 100:4.1f}%)")
print("  (survey 기준: 흡수 42.3·메타 14.3·detail (분류 81.7%+기타18.3%))")
print("\ndetail 카테고리 상위 12:")
for c, n in cat.most_common(12):
    print(f"  {n:>7}  {c}")

# 풍부한 연도 실증
print("\n=== 00102858/2024 (대형사 풍부연도) 차입금조건·특수관계자 실증 ===")
df = classify_note_facts(
    read_note_facts(BASE / "00102858" / "2024" / "raw" / "notes_xbrl" / "note_facts.tsv"), tax
)
print("bucket:", df["bucket"].value_counts().to_dict())
for catname in ("차입금조건", "특수관계자거래"):
    sub = df[df["category"] == catname].head(3)
    print(f"  [{catname}] {len(df[df['category'] == catname])}행:")
    for _, r in sub.iterrows():
        print(f"     {str(r['concept'])[:42]:42s} {str(r['label_ko'])[:16]:16s} = {r['value']}")
