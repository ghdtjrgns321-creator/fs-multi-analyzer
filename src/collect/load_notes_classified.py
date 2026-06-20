"""분류·필터된 주석을 회사연도 DuckDB(note_facts_classified)에 전수 적재.

적재범위 = detail + 기타주석 + 유차원 흡수(메타·무차원흡수 제외, select_for_load).
note_facts.tsv(재추출 7컬럼)를 분류→필터→corp/year 부착→DB write. Arelle 불필요(빠름).
재개: 테이블 있으면 skip.

실행: PYTHONPATH=. uv run python -m src.collect.load_notes_classified          (전수)
      PYTHONPATH=. uv run python -m src.collect.load_notes_classified 00100939  (특정 회사)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb

from config.settings import settings
from src.db.normalized import db_path, write_note_facts_classified
from src.normalize.notes_classify import (
    classify_note_facts,
    load_note_taxonomy,
    read_note_facts,
    select_for_load,
)

RESULT_PATH = Path("data/backtest/_dg_load_notes.jsonl")


def _has_table(path: Path) -> bool:
    if not path.exists():
        return False
    with duckdb.connect(str(path), read_only=True) as con:
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
    return "note_facts_classified" in tables


def note_year_dirs(root: Path, corp: str) -> list[str]:
    cdir = root / corp
    out = []
    for ydir in sorted(cdir.iterdir()) if cdir.is_dir() else []:
        if (ydir / "raw" / "notes_xbrl" / "note_facts.tsv").exists():
            out.append(ydir.name)
    return out


def run(
    corps: list[str] | None = None, log_every: int = 200, force: bool = False
) -> dict[str, int]:
    root = settings.data_dir
    taxonomy = load_note_taxonomy()
    all_corps = corps or sorted(d.name for d in root.iterdir() if d.is_dir() and d.name.isdigit())
    counts = {"loaded": 0, "skip": 0, "empty": 0, "error": 0}
    rows_total = 0
    t0 = time.perf_counter()
    processed = 0

    with RESULT_PATH.open("a", encoding="utf-8") as out:
        for corp in all_corps:
            for year in note_year_dirs(root, corp):
                processed += 1
                rec: dict = {"corp": corp, "year": year}
                path = db_path(corp, year, root)
                if not force and _has_table(path):
                    counts["skip"] += 1
                    continue
                try:
                    facts = read_note_facts(
                        root / corp / year / "raw" / "notes_xbrl" / "note_facts.tsv"
                    )
                    classified = classify_note_facts(facts, taxonomy)
                    loadable = select_for_load(classified)
                    loadable = loadable.assign(corp_code=corp, year=year)
                    write_note_facts_classified(loadable, corp, year, root)
                    counts["loaded"] += 1
                    rows_total += len(loadable)
                    rec.update(status="ok", rows=len(loadable))
                except Exception as exc:  # noqa: BLE001 — 한 건 실패가 전체를 막지 않게
                    counts["error"] += 1
                    rec.update(status="error", error=str(exc)[:200])
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if processed % log_every == 0:
                    el = (time.perf_counter() - t0) / 60
                    print(
                        f"[{processed}] loaded={counts['loaded']} skip={counts['skip']} "
                        f"err={counts['error']} rows={rows_total} | {el:.1f}분",
                        flush=True,
                    )
            out.flush()

    el = (time.perf_counter() - t0) / 60
    print(
        f"\n[완료] 처리 {processed} | loaded={counts['loaded']} skip={counts['skip']} "
        f"error={counts['error']} | 적재행 {rows_total:,} | {el:.1f}분 | 로그 {RESULT_PATH}"
    )
    return counts


def main() -> None:
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    run(args or None, force=force)


if __name__ == "__main__":
    main()
