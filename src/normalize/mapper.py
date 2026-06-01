"""Canonical account mapper."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.normalize.config import CanonicalAccount, normalize_label

EXACT = "exact_taxonomy_match"
ALIAS = "label_alias_match"
UNMAPPED = "unmapped_extension_account"
OTHER_CANONICAL = "기타 중요 계정"


@dataclass(frozen=True)
class MappingResult:
    canonical: str
    mapping_status: str


class AccountMapper:
    """Map rows to canonical accounts using account_id first, then aliases."""

    def __init__(self, accounts: list[CanonicalAccount]) -> None:
        self._by_id = {
            account_id: account.name for account in accounts for account_id in account.account_ids
        }
        self._by_alias = {
            normalize_label(alias): account.name
            for account in accounts
            for alias in account.aliases
        }

    def map_row(self, row: pd.Series) -> MappingResult:
        account_id = str(row.get("account_id", ""))
        label = normalize_label(row.get("account_nm", ""))

        if account_id in self._by_id:
            return MappingResult(self._by_id[account_id], EXACT)
        if label in self._by_alias:
            return MappingResult(self._by_alias[label], ALIAS)
        return MappingResult(OTHER_CANONICAL, UNMAPPED)
