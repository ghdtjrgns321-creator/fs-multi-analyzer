"""DuckDB persistence for L1 normalized financial statements."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import pandas as pd

from config.settings import settings

if TYPE_CHECKING:
    from src.schemas.extract import ExtractedItem

_REPORT_EXTRACTS_COLUMNS = [
    "corp_code",
    "year",
    "part",
    "label",
    "statement",
    "evidence",
    "why_relevant",
]


def db_path(corp_code: str, year: int | str, data_dir: Path | None = None) -> Path:
    """Return company/year isolated DuckDB path."""

    root = data_dir or settings.data_dir
    path = root / corp_code / str(year) / ("analysis" + ".duckdb")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_normalized_financials(
    frame: pd.DataFrame,
    corp_code: str,
    year: int | str,
    data_dir: Path | None = None,
) -> Path:
    """Replace normalized_financials table for one company-year."""

    path = db_path(corp_code, year, data_dir)
    with duckdb.connect(str(path)) as con:
        con.register("normalized_frame", frame)
        con.execute(
            "CREATE OR REPLACE TABLE normalized_financials AS SELECT * FROM normalized_frame"
        )
    return path


def write_sce_components(
    frame: pd.DataFrame,
    corp_code: str,
    year: int | str,
    data_dir: Path | None = None,
) -> Path:
    """Replace sce_equity_components table for one company-year (별도 2D 산출물)."""

    path = db_path(corp_code, year, data_dir)
    with duckdb.connect(str(path)) as con:
        con.register("sce_frame", frame)
        con.execute("CREATE OR REPLACE TABLE sce_equity_components AS SELECT * FROM sce_frame")
    return path


def write_note_facts_classified(
    frame: pd.DataFrame,
    corp_code: str,
    year: int | str,
    data_dir: Path | None = None,
) -> Path:
    """Replace note_facts_classified table for one company-year (분류·필터된 주석 facts)."""

    path = db_path(corp_code, year, data_dir)
    with duckdb.connect(str(path)) as con:
        con.register("note_frame", frame)
        con.execute("CREATE OR REPLACE TABLE note_facts_classified AS SELECT * FROM note_frame")
    return path


def write_report_extracts(
    items: list[ExtractedItem],
    corp_code: str,
    year: int | str,
    data_dir: Path | None = None,
) -> Path:
    """Replace report_extracts table for one company-year (Layer 1 서술 리더 추출물).

    회사/연도 격리 — corp_code·year 컬럼을 함께 저장한다. 빈 items도 스키마 있는 빈 테이블로 생성.
    """

    rows = [
        {
            "corp_code": corp_code,
            "year": str(year),
            "part": it.part,
            "label": it.label,
            "statement": it.statement,
            "evidence": it.evidence,
            "why_relevant": it.why_relevant,
        }
        for it in items
    ]
    frame = pd.DataFrame(rows, columns=_REPORT_EXTRACTS_COLUMNS)
    path = db_path(corp_code, year, data_dir)
    with duckdb.connect(str(path)) as con:
        con.register("extract_frame", frame)
        con.execute("CREATE OR REPLACE TABLE report_extracts AS SELECT * FROM extract_frame")
    return path


def read_report_extracts(
    corp_code: str,
    year: int | str,
    data_dir: Path | None = None,
) -> list[dict]:
    """Load report_extracts rows for one company-year. 없는 DB·테이블은 [] graceful."""

    path = db_path(corp_code, year, data_dir)
    if not path.exists():
        return []
    with duckdb.connect(str(path)) as con:
        exists = con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'report_extracts'"
        ).fetchone()
        if not exists:
            return []
        frame = con.execute("SELECT * FROM report_extracts").fetch_df()
    return frame.to_dict("records")
