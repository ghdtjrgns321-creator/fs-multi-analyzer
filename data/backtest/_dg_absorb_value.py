"""흡수(본문중복) 행에 중요 정보가 있는지 판단 근거 측정(읽기전용).

흡수 행을 무차원(총계=본문중복) vs 유차원(부문·구성요소·차입건별 분해)로 분리.
유차원이 어떤 본문계정을 어떤 축으로 분해하는지 + 분식관점 고가치 사례를 본다.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from src.normalize.notes_classify import classify_note_facts, load_note_taxonomy, read_note_facts

BASE = Path("data/companies")
SAMPLE = 350
tax = load_note_taxonomy()

flist = []
for corp in sorted(BASE.iterdir()):
    if corp.is_dir():
        for yr in sorted(corp.iterdir()):
            t = yr / "raw" / "notes_xbrl" / "note_facts.tsv"
            if t.exists():
                flist.append(t)
step = max(1, len(flist) // SAMPLE)
sample = flist[::step][:SAMPLE]

absorb_nodim = 0
absorb_dim = 0
# 유차원 흡수: (본문concept) → 어떤 축으로 분해되나
concept_axes: dict[str, Counter] = defaultdict(Counter)
# 분식 고가치 축(부문·지역·차입건별·특수관계자·채권분류)
HIGH = {
    "SegmentsAxis",
    "GeographicalAreasAxis",
    "SegmentConsolidationItemsAxis",
    "BorrowingsByNameAxis",
    "CategoriesOfRelatedPartiesAxis",
    "MaturityAxis",
    "ClassesOfFinancialAssetsAxis",
    "CounterpartiesAxis",
}
highval_rows = 0
examples: dict[str, list] = defaultdict(list)

for t in sample:
    df = classify_note_facts(read_note_facts(t), tax)
    if df.empty or "dimensions" not in df:
        continue
    ab = df[df["bucket"] == "흡수"]
    corp = t.parts[-4]
    for _, r in ab.iterrows():
        dims = str(r["dimensions"]) if r["dimensions"] else ""
        # 연결/별도축만 있는 건 사실상 총계(본문 중복). 그 외 축이 있으면 분해.
        axes = [kv.split("=")[0] for kv in dims.split("|") if kv]
        non_cs = [a for a in axes if a != "ConsolidatedAndSeparateFinancialStatementsAxis"]
        if not non_cs:
            absorb_nodim += 1
            continue
        absorb_dim += 1
        for a in non_cs:
            concept_axes[r["concept"]][a] += 1
        if any(a in HIGH for a in non_cs):
            highval_rows += 1
            key = next(a for a in non_cs if a in HIGH)
            if len(examples[key]) < 3:
                members = "|".join(kv for kv in dims.split("|") if kv.split("=")[0] in HIGH)
                examples[key].append((corp, r["concept"], members[:70], r["value"]))

tot = absorb_nodim + absorb_dim
print(f"표본 {len(sample)} — 흡수 행 {tot}")
print(f"  무차원(총계=본문중복)      : {absorb_nodim} ({absorb_nodim / tot * 100:.1f}%)")
print(f"  유차원(부문·건별 분해)     : {absorb_dim} ({absorb_dim / tot * 100:.1f}%)")
print(f"    └ 분식 고가치 축 보유    : {highval_rows} ({highval_rows / tot * 100:.1f}%)")

print("\n=== 유차원 흡수: 본문계정이 어떤 축으로 분해되나(상위) ===")
flat = Counter()
for concept, axc in concept_axes.items():
    for a, n in axc.items():
        flat[(concept, a)] += n
for (concept, axis), n in flat.most_common(18):
    print(f"  {n:>6}  {concept:32s} ↘ {axis}")

print("\n=== 분식 고가치 분해 실제 사례 ===")
for axis, exs in examples.items():
    print(f"\n[{axis}]")
    for corp, concept, members, val in exs:
        print(f"  {corp} {concept[:22]:22s} = {val:>16}  ← {members}")
