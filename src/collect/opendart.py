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

    def company(self, corp_code: str) -> dict[str, object]:
        """Fetch OpenDART company profile metadata."""

        return dict(self._dart.company(corp_code))

    def document(self, rcept_no: str) -> str:
        """Fetch the full business report document as structured XML text.

        사업보고서 전체(주석 서술·우발·대주주거래·연결범위 등 XBRL이 못 긁는 narrative)를
        구조화 XML(dart3.xsd)로 반환한다. OpenDART는 원문 미제공 보고서에 ValueError를
        던지므로(미제출/정정), 파일 부재는 예외가 아니라 "미제공"으로 흡수해 ""를 돌려준다.
        """

        try:
            return str(self._dart.document(rcept_no))
        except ValueError:
            return ""

    def event(self, corp_code: str, key_word: str, start: str, end: str) -> pd.DataFrame:
        """주요사항보고서 event 1종 조회(구조화). 빈 응답·오류는 빈 DataFrame으로 흡수.

        OpenDartReader는 데이터 없으면 status dict({'status':'013'})를 반환하므로 DataFrame이
        아니면 빈 것으로 본다(미발생=정상 부재).
        """

        try:
            result = self._dart.event(corp_code, key_word, start=start, end=end)
        except Exception:
            return pd.DataFrame()
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

    def report(self, corp_code: str, key_word: str, year: int) -> pd.DataFrame:
        """정기보고서 주요정보 1종 조회(구조화). 빈 응답·오류는 빈 DataFrame으로 흡수."""

        try:
            result = self._dart.report(corp_code, key_word, year)
        except Exception:
            return pd.DataFrame()
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

    def filings(self, corp_code: str, start: str, end: str) -> pd.DataFrame:
        """Return the raw DART filing list (정정 이력 포함, final=False).

        annual_report는 kind='A'·final=True로 최종본만 보지만, 정정 이력은 final=False라야
        [기재정정]/[첨부정정] 재제출 기록이 남는다. 파싱은 호출측(correction.py)이 한다.
        """

        result = self._dart.list(corp=corp_code, start=start, end=end, final=False)
        return result if result is not None else pd.DataFrame()

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
        """Download raw financial statement XBRL zip for the annual report.

        OpenDART는 XBRL 원본파일이 없는 보고서(status 013/014)에 ValueError를 던진다.
        파일 부재는 예외가 아니라 "미제공"이므로 False로 흡수한다(수집 계약: bool).
        """

        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return bool(self._dart.finstate_xml(report.rcept_no, save_as=str(path)))
        except ValueError:
            return False
