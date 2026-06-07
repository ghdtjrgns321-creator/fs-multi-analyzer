"""L1 normalization pipeline for raw OpenDART financial statements."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from config.settings import settings
from src.normalize.config import load_canonical_accounts
from src.normalize.mapper import OTHER_CANONICAL, UNMAPPED, AccountMapper
from src.normalize.schema import parse_amount, validate_raw_frame

# IS↔CIS는 손익·포괄손익 통합신고(이자비용·지분법이익·당기순이익 등이 CIS로 신고)라 상호 호환.
# 나머지 재무제표 교차는 흐름조정·자본변동 행이 잔액/손익 칸으로 흡수되는 오매핑이므로 차단.
_STATEMENT_COMPATIBLE = {("IS", "CIS"), ("CIS", "IS")}

OUTPUT_COLUMNS = [
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
            "prior_amount": [
                parse_amount(value, settings.amount_round_digits)
                for value in _optional_amount_column(frame, "frmtrm_amount")
            ],
            "prior2_amount": [
                parse_amount(value, settings.amount_round_digits)
                for value in _optional_amount_column(frame, "bfefrmtrm_amount")
            ],
            "mapping_status": [item.mapping_status for item in mapped],
            "account_detail": frame.get("account_detail", ""),
        }
    )
    return _dedupe_canonical_rows(_dedupe_statement_rows(_apply_statement_guard(output)))[
        OUTPUT_COLUMNS
    ]


def _apply_statement_guard(frame: pd.DataFrame) -> pd.DataFrame:
    """행의 재무제표 구분(sj_div)이 매핑된 canonical의 정해진 statement와 다르면
    그 매핑을 무효화한다(기타 중요 계정으로 강등).

    Why: 공시자가 현금흐름표 증감조정·자본변동 행을 잔액/손익 계정과 같은 라벨로 적으면
    label alias로 엉뚱한 canonical(예: CF '재고자산' 조정 → 재고자산 잔액 칸)에 흡수되고,
    중복제거 키에 sj_div가 없어 잔액 계정을 덮거나 소실시킨다. statement 일치를 강제해 차단.
    IS↔CIS만 통합신고 호환으로 허용한다.
    """

    if frame.empty:
        return frame
    scoped = frame.copy()
    canonical_statement = scoped["canonical_statement"].astype(str)
    sj_div = scoped["sj_div"].astype(str)
    compatible = pd.Series(
        [
            (sj, cs) in _STATEMENT_COMPATIBLE
            for sj, cs in zip(sj_div, canonical_statement, strict=True)
        ],
        index=scoped.index,
    )
    mismatch = (
        (scoped["canonical"] != OTHER_CANONICAL)
        & (canonical_statement != "")
        & (canonical_statement != sj_div)
        & ~compatible
    )
    scoped.loc[mismatch, "canonical"] = OTHER_CANONICAL
    scoped.loc[mismatch, "mapping_status"] = UNMAPPED
    scoped.loc[mismatch, "canonical_statement"] = ""
    return scoped


def _optional_amount_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame:
        return frame[column]
    return pd.Series([None] * len(frame), index=frame.index)


def _dedupe_statement_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep one representative row for an account within one statement/year."""

    if frame.empty:
        return frame
    key = ["account_id", "label", "year", "fs_div", "sj_div"]
    scoped = frame.copy()
    scoped["_detail_score"] = scoped.apply(_detail_score, axis=1)
    # amount에 None/비numeric이 섞이면 object dtype → .abs() 크래시(선진). numeric 변환.
    amount_num = pd.to_numeric(scoped["amount"], errors="coerce")
    scoped["_has_amount"] = amount_num.notna()
    scoped["_abs_amount"] = amount_num.abs().fillna(-1)
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
    mapped["_abs_amount"] = pd.to_numeric(mapped["amount"], errors="coerce").abs().fillna(-1)
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
