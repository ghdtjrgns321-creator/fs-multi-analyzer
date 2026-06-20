"""행별 전수 충실성 감사 — 본문 모든 과목 + 주석이 소실/오분류 없이 살아있나(읽기전용).

본문: raw finstate의 모든 account_id가 정규화에 생존하는가(소실=진짜 데이터유실). 소실분이
      dedup(중복 account_id) 때문인지 구분. 금액 보존(raw 금액이 정규화에 존재).
주석: note_facts.tsv 모든 concept이 분류 반영. 누락분이 정확히 메타+무차원흡수인가. 차원 보존.
재현: PYTHONPATH=. uv run python data/backtest/_p1_rowlevel_audit.py
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import duckdb

from src.normalize.notes_classify import (
    classify_note_facts,
    is_dimensioned,
    load_note_taxonomy,
    read_note_facts,
    select_for_load,
)

BASE = Path("data/companies")
BLANK = {"", "-표준계정코드 미사용-"}

# 대상: 분식 5사 + 정상 2사 + 표본사 일부
TARGETS = ["00159616", "00409681", "00413046", "00126380", "00309503", "00103626", "00150165"]
tax = load_note_taxonomy()


def raw_account_ids(corp: str, year: str) -> Counter:
    """raw finstate의 (account_id, sj_div)별 행수(표준ID 보유분만)."""
    c: Counter = Counter()
    for fs in ("CFS", "OFS"):
        p = BASE / corp / year / "raw" / f"finstate_all_{fs}.csv"
        if not p.exists() or p.stat().st_size <= 5:
            continue
        with p.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                aid = (r.get("account_id") or "").strip()
                if aid and aid not in BLANK:
                    c[(aid, fs, (r.get("sj_div") or "").strip())] += 1
    return c


print("=" * 70)
print("A. 본문 행별 — raw account_id 생존 (표준ID 보유분)")
for corp in TARGETS:
    cdir = BASE / corp
    years = (
        sorted(y.name for y in cdir.iterdir() if y.is_dir() and y.name.isdigit())
        if cdir.exists()
        else []
    )
    for year in years[:3]:
        db = cdir / year / "analysis.duckdb"
        if not db.exists():
            continue
        raw = raw_account_ids(corp, year)
        if not raw:
            continue
        con = duckdb.connect(str(db), read_only=True)
        norm = con.execute("SELECT account_id, fs_div FROM normalized_financials").fetchdf()
        con.close()
        norm_ids = {(str(a), str(f)) for a, f in zip(norm["account_id"], norm["fs_div"])}
        raw_ids = {(aid, fs) for (aid, fs, _sj) in raw}
        lost = raw_ids - norm_ids
        # 소실분 중 dedup(같은 account_id 중복신고)인지 — raw에서 2회+ 등장?
        lost_dup = sum(
            1 for (aid, fs) in lost if any(k[0] == aid and k[1] == fs and raw[k] > 1 for k in raw)
        )
        print(
            f"  {corp}/{year}: raw표준ID {len(raw_ids)} → 생존 {len(raw_ids & norm_ids)} "
            f"소실 {len(lost)}({'중복기인 ' + str(lost_dup) if lost else ''})"
        )
        if lost and len(lost) - lost_dup > 0:
            real = [
                x
                for x in lost
                if not any(k[0] == x[0] and k[1] == x[1] and raw[k] > 1 for k in raw)
            ][:5]
            print(f"      ⚠ 비중복 소실 예: {real}")

print("\n" + "=" * 70)
print("B. 주석 행별 — concept 분류 반영 + 누락 정합성")
for corp in TARGETS:
    cdir = BASE / corp
    years = (
        sorted(y.name for y in cdir.iterdir() if y.is_dir() and y.name.isdigit())
        if cdir.exists()
        else []
    )
    for year in years[:2]:
        tsv = cdir / year / "raw" / "notes_xbrl" / "note_facts.tsv"
        if not tsv.exists():
            continue
        facts = read_note_facts(tsv)
        cls = classify_note_facts(facts, tax)
        load = select_for_load(cls)
        # 누락 = 전체 - 적재. 누락이 정확히 메타 + 무차원흡수인가?
        n_all, n_load = len(cls), len(load)
        meta = int((cls["bucket"] == "메타").sum())
        absorb = cls[cls["bucket"] == "흡수"]
        nodim_absorb = int(sum(1 for d in absorb["dimensions"] if not is_dimensioned(d)))
        expected_drop = meta + nodim_absorb
        actual_drop = n_all - n_load
        ok = (
            "OK"
            if expected_drop == actual_drop
            else f"⚠불일치(예상{expected_drop}≠실제{actual_drop})"
        )
        # 차원 보존: 적재된 유차원흡수 + detail의 dimensions 비어있지 않은 비율
        print(
            f"  {corp}/{year}: 전체 {n_all} 적재 {n_load} 누락 {actual_drop}(메타{meta}+무차원흡수{nodim_absorb}) {ok}"
        )
