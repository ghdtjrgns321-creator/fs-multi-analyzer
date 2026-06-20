"""강화된 extract_note_facts가 차원을 보존하는지 1개 zip으로 검증."""

from __future__ import annotations

from pathlib import Path

from src.collect.notes_xbrl import extract_note_facts

ZIP = Path("data/companies/00100939/2025/raw/financial_statement_xbrl.zip")
facts = extract_note_facts(ZIP)
print(f"총 fact: {len(facts)}")
with_dim = [f for f in facts if f.dimensions]
print(f"차원 보유 fact: {len(with_dim)} ({len(with_dim) / len(facts) * 100:.1f}%)")

# Assets 세그먼트값이 축 라벨과 매칭되는지
assets = [f for f in facts if f.concept == "Assets"]
last = sorted({f.period for f in assets})[-1]
print(f"\nAssets 기간 {last}:")
for f in assets:
    if f.period == last:
        print(f"  {f.value:>18}  ←  {f.dimensions or '(차원없음)'}")
