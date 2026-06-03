"""Indicator-only peer financial statement collection."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import settings
from src.collect.opendart import DartCollector
from src.collect.storage import write_frame
from src.db.normalized import write_normalized_financials
from src.normalize.pipeline import normalize_company_year


def ensure_peer_financials(
    corp_code: str,
    years: list[int] | tuple[int, ...],
    collector: DartCollector | None = None,
    data_dir: Path | None = None,
) -> None:
    """Collect and normalize CFS/OFS finstate_all only; no notes or L4 peer analysis."""

    root = data_dir or settings.data_dir
    dart = collector or DartCollector()
    for year in years:
        raw_dir = root / corp_code / str(year) / "raw"
        missing = [
            fs_div
            for fs_div in ("CFS", "OFS")
            if not (raw_dir / f"finstate_all_{fs_div}.csv").exists()
        ]
        for fs_div in missing:
            frame = dart.finstate_all(corp_code, int(year), fs_div)
            if frame is None or frame.empty:
                raise RuntimeError(f"{corp_code} {year} {fs_div} finstate_all 응답이 비어 있다.")
            write_frame(pd.DataFrame(frame), raw_dir / f"finstate_all_{fs_div}.csv")
        normalized = normalize_company_year(corp_code, year, data_dir=root)
        write_normalized_financials(normalized, corp_code, year, data_dir=root)
