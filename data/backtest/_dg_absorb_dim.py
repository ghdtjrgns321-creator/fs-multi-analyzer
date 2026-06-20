"""흡수(본문중복) concept이 주석에서 차원을 갖는지 실측 → 적재범위 결정 근거(읽기전용).

회사연도당 (흡수 concept) 출현 fact 수: 1이면 본문 단일숫자 중복, 여럿이면 세그먼트·기간 등
차원 보유(본문에 없는 정보). 분포로 흡수 적재 여부 판단.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.normalize.notes_classify import classify_concept, load_note_taxonomy, read_note_facts

BASE = Path("data/companies")
SAMPLE = 300
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

per_cy_counts: list[int] = []  # (회사연도, 흡수concept)별 fact 수
distinct_values: list[int] = []  # 그 중 서로 다른 value 수
multi_example: list[tuple] = []
for t in sample:
    df = read_note_facts(t)
    if df.empty:
        continue
    buckets = [classify_concept(str(c), tax)[0] for c in df["concept"]]
    df = df.assign(_b=buckets)
    ab = df[df["_b"] == "흡수"]
    for concept, g in ab.groupby("concept"):
        per_cy_counts.append(len(g))
        nv = g["value"].nunique()
        distinct_values.append(nv)
        if len(g) >= 4 and nv >= 3 and len(multi_example) < 6:
            multi_example.append((t.parts[-4], concept, len(g), nv, list(g["value"])[:4]))

n = len(per_cy_counts)
single = sum(1 for x in per_cy_counts if x == 1)
multi = sum(1 for x in per_cy_counts if x >= 2)
multi_realdim = sum(1 for c, v in zip(per_cy_counts, distinct_values) if c >= 2 and v >= 2)
print(f"표본 {len(sample)}파일, (회사연도×흡수concept) 조합 {n}건")
print(f"  단일 fact(=본문 중복 가능성)      : {single} ({single / n * 100:.1f}%)")
print(f"  복수 fact(차원 후보)              : {multi} ({multi / n * 100:.1f}%)")
print(f"    └ 그중 값도 2개+ 다름(진짜 차원): {multi_realdim} ({multi_realdim / n * 100:.1f}%)")
cnt = Counter(min(x, 5) for x in per_cy_counts)
print("  fact수 분포(5+묶음):", {k: cnt[k] for k in sorted(cnt)})
print("\n복수·다값 흡수 예시(본문에 없는 차원 후보):")
for corp, concept, c, v, vals in multi_example:
    print(f"  {corp} {concept[:38]:38s} {c}건/{v}값 {vals}")
