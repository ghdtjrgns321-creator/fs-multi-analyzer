"""Raw OpenDART payload storage helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ABSENCE_REASONS = {"no_report", "dart_no_data", "dart_no_xbrl", "ok"}


def year_dir(data_dir: Path, corp_code: str, year: int | str) -> Path:
    """Return and create the company/year raw directory."""

    path = data_dir / corp_code / str(year) / "raw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_frame(frame: pd.DataFrame, path: Path) -> None:
    """Persist a raw DataFrame as CSV and JSON records."""

    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    frame.to_json(path.with_suffix(".json"), orient="records", force_ascii=False, indent=2)


def write_json(payload: dict[str, Any], path: Path) -> None:
    """Persist metadata without exposing secrets."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def collection_summary_path(data_dir: Path, corp_code: str, year: int | str) -> Path:
    """Return the per-company-year collection summary path."""

    return data_dir / corp_code / str(year) / "raw" / "collection_summary.json"


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON metadata file; missing or malformed files return an empty dict."""

    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_collection_summary(data_dir: Path, corp_code: str, year: int | str) -> dict[str, Any]:
    """Read per-company-year collection summary metadata."""

    return read_json(collection_summary_path(data_dir, corp_code, year))


def read_absence(data_dir: Path, corp_code: str, year: int | str) -> dict[str, str]:
    """Read normalized absence manifest values from collection summary."""

    payload = read_collection_summary(data_dir, corp_code, year)
    absence = payload.get("absence")
    if not isinstance(absence, dict):
        return {}
    out: dict[str, str] = {}
    for key in ("fs", "xbrl_zip"):
        value = absence.get(key)
        if isinstance(value, str) and value in ABSENCE_REASONS:
            out[key] = value
    return out
