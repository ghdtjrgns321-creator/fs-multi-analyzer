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
            "CREATE OR REPLACE TABLE normalized_financials "
            "AS SELECT * FROM normalized_frame"
        )
    return path
