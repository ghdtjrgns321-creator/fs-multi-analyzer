"""Load L1 normalized statements for deterministic analysis tools."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from config.settings import settings
from src.db.normalized import db_path
from src.normalize.sce import SCE_COMPONENT_COLUMNS

TOOL_COLUMNS = [
    "corp_code",
    "year",
    "fs_div",
    "sj_div",
    "canonical",
    "account_id",
    "label",
    "amount",
    "prior_amount",
    "prior2_amount",
    "mapping_status",
    "currency",
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
        if not path.exists():
            continue
        with duckdb.connect(str(path), read_only=True) as con:
            frame = con.execute("SELECT * FROM normalized_financials").fetchdf()
        for column in TOOL_COLUMNS:
            if column not in frame:
                frame[column] = None
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=TOOL_COLUMNS)
    return pd.concat(frames, ignore_index=True)[TOOL_COLUMNS]


def load_sce_equity_components(
    corp_code: str,
    years: list[int] | tuple[int, ...],
    data_dir: Path | None = None,
) -> pd.DataFrame:
    """Load SCE 2D equity-component table. Old DBs lacking the table degrade to empty."""

    frames: list[pd.DataFrame] = []
    for year in years:
        path = db_path(corp_code, year, data_dir or settings.data_dir)
        if not path.exists():
            continue
        with duckdb.connect(str(path), read_only=True) as con:
            tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
            if "sce_equity_components" not in tables:
                continue
            frame = con.execute("SELECT * FROM sce_equity_components").fetchdf()
        for column in SCE_COMPONENT_COLUMNS:
            if column not in frame:
                frame[column] = None
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=SCE_COMPONENT_COLUMNS)
    return pd.concat(frames, ignore_index=True)[SCE_COMPONENT_COLUMNS]
