"""OpenDART L0 collection wrapper.

Only collects and stores raw payloads. It does not normalize, analyze, or call LLMs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import OpenDartReader
import pandas as pd

from config.settings import settings


@dataclass(frozen=True)
class AnnualReport:
    """Minimal annual report metadata needed for XBRL download."""

    corp_code: str
    business_year: int
    rcept_no: str
    report_name: str


class DartCollector:
    """Small OpenDART adapter. API key is read only through config.settings."""

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key if api_key is not None else settings.dart_api_key
        if not key:
            raise ValueError("DART_API_KEY is not configured")
        self._dart = OpenDartReader(key)

    def finstate_all(self, corp_code: str, year: int, fs_div: str) -> pd.DataFrame:
        """Fetch single-company full financial statements."""

        return self._dart.finstate_all(corp_code, year, reprt_code="11011", fs_div=fs_div)

    def annual_report(self, corp_code: str, year: int) -> AnnualReport | None:
        """Find the final annual report submitted after the business year."""

        submitted_year = year + 1
        reports = self._dart.list(
            corp=corp_code,
            start=f"{submitted_year}0101",
            end=f"{submitted_year}1231",
            kind="A",
            final=True,
        )
        if reports is None or reports.empty:
            return None

        mask = reports["report_nm"].astype(str).str.contains("사업보고서", regex=False)
        candidates = reports[mask].copy()
        if candidates.empty:
            return None

        row = candidates.sort_values("rcept_dt").iloc[-1]
        return AnnualReport(
            corp_code=corp_code,
            business_year=year,
            rcept_no=str(row["rcept_no"]),
            report_name=str(row["report_nm"]),
        )

    def save_xbrl_zip(self, report: AnnualReport, path: Path) -> bool:
        """Download raw financial statement XBRL zip for the annual report."""

        path.parent.mkdir(parents=True, exist_ok=True)
        return bool(self._dart.finstate_xml(report.rcept_no, save_as=str(path)))
