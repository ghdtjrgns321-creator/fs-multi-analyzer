"""L1 normalization pipeline for raw OpenDART financial statements."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import settings
from src.normalize.config import load_canonical_accounts
from src.normalize.mapper import AccountMapper
from src.normalize.schema import parse_amount, validate_raw_frame

OUTPUT_COLUMNS = [
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


def normalize_raw_file(path: Path, fs_div: str, mapper: AccountMapper) -> pd.DataFrame:
    """Normalize one raw finstate_all CSV file to long format."""

    raw = pd.read_csv(path, dtype=str)
    frame = validate_raw_frame(raw, fs_div)
    mapped = frame.apply(mapper.map_row, axis=1)
    output = pd.DataFrame(
        {
            "corp_code": frame["corp_code"],
            "year": frame["bsns_year"],
            "fs_div": frame["fs_div"],
            "sj_div": frame["sj_div"],
            "canonical": [item.canonical for item in mapped],
            "account_id": frame["account_id"],
            "label": frame["account_nm"],
            "amount": [
                parse_amount(value, settings.amount_round_digits)
                for value in frame["thstrm_amount"]
            ],
            "mapping_status": [item.mapping_status for item in mapped],
        }
    )
    return output[OUTPUT_COLUMNS]


def normalize_company_year(
    corp_code: str,
    year: int | str,
    data_dir: Path | None = None,
    config_path: Path | None = None,
) -> pd.DataFrame:
    """Normalize CFS/OFS raw files for one company-year."""

    root = data_dir or settings.data_dir
    mapping_path = config_path or (settings.config_dir / "canonical_accounts.yaml")
    mapper = AccountMapper(load_canonical_accounts(mapping_path))
    raw_dir = root / corp_code / str(year) / "raw"
    frames = [
        normalize_raw_file(raw_dir / f"finstate_all_{fs_div}.csv", fs_div, mapper)
        for fs_div in ("CFS", "OFS")
    ]
    return pd.concat(frames, ignore_index=True)
