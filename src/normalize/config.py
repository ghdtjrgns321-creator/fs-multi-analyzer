"""Canonical account mapping loader."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CanonicalAccount:
    name: str
    statement: str
    account_ids: tuple[str, ...]
    aliases: tuple[str, ...]
    is_subtotal: bool = False


def load_canonical_accounts(path: Path) -> list[CanonicalAccount]:
    """Load canonical account mapping from YAML."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    accounts = payload.get("canonical_accounts", {})
    result: list[CanonicalAccount] = []
    for name, values in accounts.items():
        result.append(
            CanonicalAccount(
                name=str(name),
                statement=str(values["statement"]),
                account_ids=tuple(str(x) for x in values.get("account_ids", [])),
                aliases=tuple(str(x) for x in values.get("aliases", [])),
                is_subtotal=bool(values.get("is_subtotal", False)),
            )
        )
    return result


def subtotal_account_names(path: Path) -> set[str]:
    """Load canonical accounts marked as subtotal/identity rows."""

    return {account.name for account in load_canonical_accounts(path) if account.is_subtotal}


def normalize_label(label: object) -> str:
    """Normalize labels for alias lookup without embedding domain labels in code."""

    normalized = str(label or "").replace(" ", "").strip()
    return re.sub(r"\((손실|이익|손익)\)$", "", normalized)
