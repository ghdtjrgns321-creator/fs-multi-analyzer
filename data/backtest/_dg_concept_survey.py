"""신 XBRL 주석 concept 공간 측정(설계용 표본 조사, 읽기전용).

note_facts.tsv의 concept 분포·메타데이터 비율·수치 fact 비율을 표본으로 본다.
목적: 주석 분류 설계 근거. 수집은 병렬 진행 중이라 존재 파일만 읽음(표본).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

BASE = Path("data/companies")
SAMPLE = 400  # 표본 회사연도

files = []
for corp in sorted(BASE.iterdir()):
    if not corp.is_dir():
        continue
    for yr in sorted(corp.iterdir()):
        t = yr / "raw" / "notes_xbrl" / "note_facts.tsv"
        if t.exists():
            files.append(t)
print(f"수집된 note_facts.tsv 총 {len(files)}개")
# 균등 표본
step = max(1, len(files) // SAMPLE)
sample = files[::step][:SAMPLE]
print(f"표본 {len(sample)}개 조사\n")

concept_df = Counter()  # concept -> 등장 회사연도 수(doc frequency)
concept_rows = Counter()  # concept -> 총 fact 행수
numeric_concepts = set()
total_rows = 0
for t in sample:
    seen = set()
    try:
        lines = t.read_text(encoding="utf-8").splitlines()
    except Exception:
        continue
    for ln in lines[1:]:
        parts = ln.split("\t")
        if len(parts) < 6:
            continue
        concept, label_ko, label_en, period, unit, value = parts[:6]
        total_rows += 1
        concept_rows[concept] += 1
        if concept not in seen:
            concept_df[concept] += 1
            seen.add(concept)
        # 숫자 fact 판정
        v = value.replace(",", "").replace("-", "").replace(".", "")
        if v.isdigit() and unit:
            numeric_concepts.add(concept)

print(f"총 fact 행(표본): {total_rows}")
print(f"distinct concept: {len(concept_df)}")
print(f"  └ 수치형(unit 보유) concept: {len(numeric_concepts)}\n")

print("=== 최빈 concept 30(회사연도 doc-frequency) ===")
for c, n in concept_df.most_common(30):
    kind = "수치" if c in numeric_concepts else "메타/텍스트"
    print(f"  {n:>4}개사연도 {concept_rows[c]:>6}행  [{kind}] {c}")

# 메타데이터 추정(감사·식별·날짜·의견 등)
META_HINT = (
    "Auditor",
    "Audit",
    "Identif",
    "Indentif",
    "Opinion",
    "ReportDate",
    "Code",
    "Name",
    "Period",
)
meta = [c for c in concept_df if any(h in c for h in META_HINT)]
print(f"\n메타데이터 추정 concept: {len(meta)}종 (예: {meta[:6]})")
