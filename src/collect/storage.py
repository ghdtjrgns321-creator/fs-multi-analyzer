"""Raw OpenDART payload storage helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


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
