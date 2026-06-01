"""Load L1 normalized statements for deterministic analysis tools."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from config.settings import settings
from src.db.normalized import db_path

TOOL_COLUMNS = [
    "corp_code",
    "year",
    "fs_div",
    "sj_div",
    "canonical",
    "account_id",
    "label",
    "amount",
    "mapping_status",
]


def load_normalized_financials(
    corp_code: str,
    years: list[int] | tuple[int, ...],
    data_dir: Path | None = None,
) -> pd.DataFrame:
    """Load normalized_financials from company/year isolated DuckDB files."""

    frames: list[pd.DataFrame] = []
    for year in years:
        path = db_path(corp_code, year, data_dir or settings.data_dir)
        with duckdb.connect(str(path), read_only=True) as con:
            frame = con.execute(
                "SELECT corp_code, year, fs_div, sj_div, canonical, account_id, "
                "label, amount, mapping_status FROM normalized_financials"
            ).fetchdf()
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)[TOOL_COLUMNS]
