"""주석 전수수집 결과 독립 검증(보고 무비판 수용 금지·§9). 읽기전용 전수.

재현: PYTHONPATH=. uv run python data/backtest/_dg_collection_audit.py
검증: 파일수·빈껍데기·항목수 분포·실패 회계(jsonl) 직접 재산출.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

BASE = Path("data/companies")

# 1) note_facts.tsv 전수 카운트 + 항목수(=facts 행수) 분포 + 빈껍데기
counts: list[int] = []
empty = 0
files = 0
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
        n = max(0, len(text.splitlines()) - 1)  # 헤더 제외
        counts.append(n)
        if n == 0:
            empty += 1

counts.sort()
print(f"note_facts.tsv 파일 수      : {files}  (보고 4,614)")
print(f"빈껍데기(facts 0행)         : {empty}  (보고 0)")
print(f"치환문자(mojibake) 파일     : {mojibake}")
if counts:
    print(
        f"facts 항목수 — 최소/중앙/최대: {counts[0]} / {int(statistics.median(counts))} / {counts[-1]}"
    )
    print("             (보고 137 / 1,012 / 36,769)")
    print(f"총 facts 행(전수)          : {sum(counts):,}")

# 2) 실패 회계 — _dg_collect_all.jsonl status 집계
jl = Path("data/backtest/_dg_collect_all.jsonl")
if jl.exists():
    from collections import Counter

    st = Counter()
    rows = 0
    for line in jl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows += 1
        try:
            st[json.loads(line).get("status", "?")] += 1
        except Exception:
            st["_parse_err"] += 1
    print(f"\n_dg_collect_all.jsonl 행수  : {rows}  (보고 분모 5,126)")
    print("status 집계:")
    for k, v in st.most_common():
        print(f"  {k:20s} {v}")
else:
    print("\n_dg_collect_all.jsonl 없음 — 실패 회계 재현 불가")
