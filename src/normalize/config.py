"""Canonical account mapping loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CanonicalAccount:
    name: str
    statement: str
    account_ids: tuple[str, ...]
    aliases: tuple[str, ...]


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
            )
        )
    return result


def normalize_label(label: object) -> str:
    """Normalize labels for alias lookup without embedding domain labels in code."""

    return str(label or "").replace(" ", "").strip()
