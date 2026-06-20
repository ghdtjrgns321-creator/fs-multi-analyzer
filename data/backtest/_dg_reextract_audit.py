"""재추출 결과 전수 검증(§9 보고 무비판 수용 금지). 읽기전용.

검증: 전체 tsv의 7컬럼화·빈추출·mojibake(전수, 헤더+행수), 차원 보존율·세그먼트축 실재(표본).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

BASE = Path("data/companies")

# 1) 전수: 7컬럼화 + 빈추출 + mojibake
files = 0
seven = 0
six = 0
empty = 0
mojibake = 0
for corp in BASE.iterdir():
    if not corp.is_dir():
        continue
    for yr in corp.iterdir():
        t = yr / "raw" / "notes_xbrl" / "note_facts.tsv"
        if not t.exists():
            continue
        files += 1
        try:
            text = t.read_text(encoding="utf-8")
        except Exception:
            mojibake += 1
            continue
        if chr(0xFFFD) in text:
            mojibake += 1
        lines = text.splitlines()
        header = lines[0] if lines else ""
        if "dimensions" in header:
            seven += 1
        else:
            six += 1
        if len(lines) <= 1:
            empty += 1

print("=== 전수 ===")
print(f"note_facts.tsv 총           : {files}")
print(f"7컬럼(dimensions 보유)       : {seven}  ({seven / files * 100:.1f}%)")
print(f"구 6컬럼(미재추출)           : {six}")
print(f"빈껍데기(<=1행)             : {empty}")
print(f"mojibake 파일               : {mojibake}")

# 2) 표본: 차원 보존율 + 세그먼트축 실재
SAMPLE = 300
flist = []
for corp in sorted(BASE.iterdir()):
    if corp.is_dir():
        for yr in sorted(corp.iterdir()):
            t = yr / "raw" / "notes_xbrl" / "note_facts.tsv"
            if t.exists():
                flist.append(t)
step = max(1, len(flist) // SAMPLE)
sample = flist[::step][:SAMPLE]

rows = 0
with_dim = 0
axes: Counter = Counter()
seg_files = 0
for t in sample:
    has_seg = False
    for ln in t.read_text(encoding="utf-8").splitlines()[1:]:
        p = ln.split("\t")
        if len(p) < 7:
            continue
        rows += 1
        dims = p[6]
        if dims:
            with_dim += 1
            for kv in dims.split("|"):
                axis = kv.split("=")[0]
                axes[axis] += 1
                if axis in (
                    "SegmentsAxis",
                    "GeographicalAreasAxis",
                    "SegmentConsolidationItemsAxis",
                ):
                    has_seg = True
    if has_seg:
        seg_files += 1

print(f"\n=== 표본 {len(sample)} ===")
print(f"fact 행: {rows}")
print(f"차원 보유 fact: {with_dim} ({with_dim / rows * 100:.1f}%)")
print(f"세그먼트축 보유 파일: {seg_files}/{len(sample)} ({seg_files / len(sample) * 100:.0f}%)")
print("최빈 차원축 12:")
for axis, n in axes.most_common(12):
    print(f"  {n:>7}  {axis}")
