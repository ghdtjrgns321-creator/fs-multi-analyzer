"""DuckDB persistence for L1 normalized financial statements."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from config.settings import settings


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
