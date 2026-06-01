"""Pandera L1 raw schema and amount casting."""

from __future__ import annotations

import pandas as pd
from pandera.pandas import Check, Column, DataFrameSchema

RAW_SCHEMA = DataFrameSchema(
    {
        "corp_code": Column(str, nullable=False),
        "bsns_year": Column(str, nullable=False),
        "fs_div": Column(str, Check.isin(["CFS", "OFS"]), nullable=False),
        "sj_div": Column(str, Check.isin(["BS", "IS", "CIS", "CF", "SCE"]), nullable=False),
        "account_id": Column(str, nullable=False),
        "account_nm": Column(str, nullable=False),
        "thstrm_amount": Column(str, nullable=True),
    },
    coerce=True,
)


def validate_raw_frame(frame: pd.DataFrame, fs_div: str) -> pd.DataFrame:
    """Inject fs_div and validate the L1 raw schema."""

    enriched = frame.copy()
    enriched["fs_div"] = fs_div
    return RAW_SCHEMA.validate(enriched, lazy=True)


def parse_amount(value: object, round_digits: int = 0) -> float | None:
    """Cast OpenDART amount strings to rounded numeric values."""

    if value is None or pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "nan", "None"}:
        return None
    return round(float(text), round_digits)
