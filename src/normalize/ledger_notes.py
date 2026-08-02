"""주석 이관 원장 — XBRL 주석 fact 전량이 적재/사유제외/미설명 중 어디로 갔는지 분해.

제외 사유는 분류기가 이미 코드로 들고 있다(notes_classify.select_for_load):
  메타      = 표지·감사인·연락처 등 분석 대상이 아닌 fact
  본표 중복 = 본문 재무제표가 담당하는 총계(연결·별도 축만 붙은 흡수 행)
적재 대상으로 뽑혔는데 DB에 없는 건수가 미설명 — 조용한 드롭이 여기서 드러난다.

원본 XBRL이 아예 없는 회사연도는 수집 단계가 사유를 남긴다(storage.read_absence). 사유가
있으면 사유 있는 제외, 없으면 대조 불가(checkable=False)로 돌려준다.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from src.collect.storage import read_absence
from src.normalize.notes_classify import (
    classify_note_facts,
    is_dimensioned,
    load_note_taxonomy,
    read_note_facts,
    select_for_load,
)

META = "메타(표지·감사인·연락처)"
BODY_DUPLICATE = "본표 중복(본문 재무제표가 담당)"


def _loaded_rows(db_path: Path) -> int | None:
    if not db_path.exists():
        return None
    with duckdb.connect(str(db_path), read_only=True) as con:
        exists = con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'note_facts_classified'"
        ).fetchone()
        if not exists:
            return None
        return int(con.execute("SELECT count(*) FROM note_facts_classified").fetchone()[0])


def note_ledger(corp_code: str, year: str, base_dir: Path, taxonomy=None) -> dict:
    """주석 fact 전량을 적재/사유제외/미설명으로 분해한다."""

    ydir = base_dir / corp_code / str(year)
    facts = read_note_facts(ydir / "raw" / "notes_xbrl" / "note_facts.tsv")
    if facts.empty:
        reason = read_absence(base_dir, corp_code, year).get("xbrl_zip")
        return {
            "checkable": bool(reason),
            "total": 0,
            "loaded": 0,
            "excluded": {f"원본 미제공({reason})": 0} if reason else {},
            "unexplained": 0,
        }

    classified = classify_note_facts(facts, taxonomy or load_note_taxonomy())
    bucket = classified["bucket"]
    meta = int((bucket == "메타").sum())
    duplicate = int(((bucket == "흡수") & (~classified["dimensions"].map(is_dimensioned))).sum())
    expected = len(select_for_load(classified))
    loaded = _loaded_rows(ydir / "analysis.duckdb")
    if loaded is None:
        return {
            "checkable": False,
            "total": len(facts),
            "loaded": 0,
            "excluded": {},
            "unexplained": 0,
        }
    return {
        "checkable": True,
        "total": len(facts),
        "loaded": loaded,
        "excluded": {META: meta, BODY_DUPLICATE: duplicate},
        "unexplained": max(expected - loaded, 0),
    }
