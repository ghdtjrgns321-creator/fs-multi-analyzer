"""재무제표 이관 원장 — DART raw CSV 각 행이 정규화 결과 어디로 갔는지 전량 분해.

모집단 = raw CSV 행 전부 = 적재 + 사유 있는 이관 + 미설명.
미설명이 1건이라도 있으면 이관이 깨진 것이다(src/report/coverage.py 셀 원장과 같은 규율).

임계로 자르지 않는다. "몇 %가 실렸나"가 아니라 "설명되지 않는 행이 있나"만 본다.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import duckdb

RAW_FILES = {"CFS": "finstate_all_CFS.csv", "OFS": "finstate_all_OFS.csv"}
RECLASSIFIED = "표 재분류(원본 표와 다른 표로 적재)"


def _norm_index(db_path: Path, year: str) -> tuple[set, dict]:
    """정규화 결과 색인 — (fs, sj, account_id) 집합과 (fs, account_id)→{sj} 매핑."""

    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = con.execute(
            "SELECT fs_div, sj_div, account_id, label FROM normalized_financials WHERE year = ?",
            [int(year)],
        ).fetchall()
    exact = set()
    by_id: dict[tuple[str, str], set[str]] = defaultdict(set)
    labels = set()
    for fs_div, sj_div, account_id, label in rows:
        exact.add((str(fs_div), str(sj_div), str(account_id)))
        by_id[(str(fs_div), str(account_id))].add(str(sj_div))
        labels.add((str(fs_div), str(sj_div), str(label)))
    return exact | labels, by_id


def financial_ledger(corp_code: str, year: str, base_dir: Path) -> dict:
    """raw 재무제표 행 전량을 적재/이관/미설명으로 분해한다.

    raw CSV가 하나도 없으면 대조 불가(checkable=False) — 빈 검사를 통과로 세지 않기 위해
    별도 상태로 돌려준다(§9 hollow-PASS 차단).
    """

    ydir = base_dir / corp_code / str(year)
    db_path = ydir / "analysis.duckdb"
    present = [fs for fs, name in RAW_FILES.items() if (ydir / "raw" / name).exists()]
    if not present or not db_path.exists():
        return {"checkable": False, "total": 0, "loaded": 0, "excluded": {}, "unexplained": []}

    exact, by_id = _norm_index(db_path, year)
    loaded = 0
    excluded: dict[str, int] = defaultdict(int)
    unexplained: list[dict] = []
    for fs_div in present:
        path = ydir / "raw" / RAW_FILES[fs_div]
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
            for row in csv.DictReader(handle):
                sj_div = str(row.get("sj_div", ""))
                account_id = str(row.get("account_id", ""))
                label = str(row.get("account_nm", ""))
                if (fs_div, sj_div, account_id) in exact or (fs_div, sj_div, label) in exact:
                    loaded += 1
                elif by_id.get((fs_div, account_id)):
                    excluded[RECLASSIFIED] += 1
                else:
                    unexplained.append(
                        {
                            "fs_div": fs_div,
                            "sj_div": sj_div,
                            "account_id": account_id,
                            "label": label,
                            "amount": str(row.get("thstrm_amount", "")),
                        }
                    )
    total = loaded + sum(excluded.values()) + len(unexplained)
    return {
        "checkable": True,
        "total": total,
        "loaded": loaded,
        "excluded": dict(excluded),
        "unexplained": unexplained,
    }


def sce_transfer(corp_code: str, year: str, base_dir: Path) -> dict:
    """자본변동표 이관 — raw SCE 행은 2D 테이블(sce_equity_components)이 받아야 한다.

    본문 테이블에도 SCE 행이 남으므로 위 행 대조만으로는 2D 이관 실패가 안 잡힌다(분석이 실제
    쓰는 경로가 2D다). 원본에 SCE 행이 있는데 2D 셀이 0이면 그 행 전부가 미설명이다.
    """

    ydir = base_dir / corp_code / str(year)
    db_path = ydir / "analysis.duckdb"
    raw_rows = 0
    for name in RAW_FILES.values():
        path = ydir / "raw" / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
            raw_rows += sum(1 for row in csv.DictReader(handle) if str(row.get("sj_div")) == "SCE")
    if not raw_rows:
        return {"checkable": True, "raw_rows": 0, "cells": 0, "unexplained": 0}
    if not db_path.exists():
        return {"checkable": False, "raw_rows": raw_rows, "cells": 0, "unexplained": 0}
    with duckdb.connect(str(db_path), read_only=True) as con:
        exists = con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'sce_equity_components'"
        ).fetchone()
        cells = (
            int(con.execute("SELECT count(*) FROM sce_equity_components").fetchone()[0])
            if exists
            else 0
        )
    return {
        "checkable": True,
        "raw_rows": raw_rows,
        "cells": cells,
        "unexplained": 0 if cells else raw_rows,
    }
