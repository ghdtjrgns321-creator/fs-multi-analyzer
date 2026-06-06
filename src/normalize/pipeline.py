"""L1 normalization pipeline for raw OpenDART financial statements."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

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
            "canonical_statement": [item.statement for item in mapped],
            "account_id": frame["account_id"],
            "label": frame["account_nm"],
            "amount": [
                parse_amount(value, settings.amount_round_digits)
                for value in frame["thstrm_amount"]
            ],
            "mapping_status": [item.mapping_status for item in mapped],
            "account_detail": frame.get("account_detail", ""),
        }
    )
    return _dedupe_canonical_rows(_dedupe_statement_rows(output))[OUTPUT_COLUMNS]


def _dedupe_statement_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep one representative row for an account within one statement/year."""

    if frame.empty:
        return frame
    key = ["account_id", "label", "year", "fs_div", "sj_div"]
    scoped = frame.copy()
    scoped["_detail_score"] = scoped.apply(_detail_score, axis=1)
    scoped["_has_amount"] = scoped["amount"].notna()
    scoped["_abs_amount"] = scoped["amount"].abs().fillna(-1)
    return (
        scoped.sort_values(
            ["_detail_score", "_has_amount", "_abs_amount"],
            ascending=[False, False, False],
            kind="mergesort",
        )
        .drop_duplicates(key, keep="first")
        .drop(columns=["_detail_score", "_has_amount", "_abs_amount", "account_detail"])
        .reset_index(drop=True)
    )


def _dedupe_canonical_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep one canonical row per statement/year without summing component lines."""

    if frame.empty:
        return frame
    scoped = frame.copy()
    mapped = scoped[scoped["canonical"] != "기타 중요 계정"].copy()
    unmapped = scoped[scoped["canonical"] == "기타 중요 계정"].copy()
    if mapped.empty:
        return scoped
    mapped["_canonical_score"] = mapped.apply(_canonical_score, axis=1)
    mapped["_abs_amount"] = mapped["amount"].abs().fillna(-1)
    deduped = (
        mapped.sort_values(
            ["_canonical_score", "_abs_amount"],
            ascending=[False, False],
            kind="mergesort",
        )
        .drop_duplicates(["canonical", "year", "fs_div"], keep="first")
        .drop(columns=["_canonical_score", "_abs_amount"])
        .reset_index(drop=True)
    )
    return pd.concat([deduped, unmapped], ignore_index=True)


def _canonical_score(row: pd.Series) -> int:
    if str(row.get("sj_div", "")) == str(row.get("canonical_statement", "")):
        return 6
    if str(row.get("mapping_status", "")) == "exact_taxonomy_match":
        return 4
    canonical = str(row.get("canonical", ""))
    label = str(row.get("label", "")).replace(" ", "").strip()
    if canonical and label == canonical.replace(" ", "").strip():
        return 3
    return 2


def _detail_score(row: pd.Series) -> int:
    detail = str(row.get("account_detail", ""))
    fs_div = str(row.get("fs_div", ""))
    if fs_div == "CFS" and "연결재무제표" in detail:
        return 3
    if fs_div == "OFS" and ("별도재무제표" in detail or "재무제표" in detail):
        return 3
    if "[member]" not in detail:
        return 2
    return 1


def _empty_output() -> pd.DataFrame:
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def _normalize_if_present(path: Path, fs_div: str, mapper: AccountMapper) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 5:
        return _empty_output()
    try:
        return normalize_raw_file(path, fs_div, mapper)
    except EmptyDataError:
        return _empty_output()


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
        _normalize_if_present(raw_dir / f"finstate_all_{fs_div}.csv", fs_div, mapper)
        for fs_div in ("CFS", "OFS")
    ]
    nonempty = [frame for frame in frames if not frame.empty]
    if not nonempty:
        return _empty_output()
    return pd.concat(nonempty, ignore_index=True)
