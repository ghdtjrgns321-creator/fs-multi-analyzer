"""원본 접수분(as-filed) 식별 — 정정 이력 중 최초 사업보고서(설계 §4).

DART는 정정 후에도 원본 접수분을 지우지 않는다(probe_asfiled.py 실측). 정정 이력을 포함한
전체 목록(list final=False)에서 "정정" 미포함 최초 사업보고서 행 = 그 시점 감사인이 본 원본.

식별 로직은 순수함수(테스트 가능). 실제 fetch(본문·XBRL)는 DartCollector 래퍼로 분리하되
호출 시에만 네트워크가 발생한다(import·정의는 무해).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

_ANNUAL = "사업보고서"
_CORRECTION = "정정"


@dataclass(frozen=True)
class OriginalReport:
    """원본 접수분 1건 — as-filed 입력의 출처."""

    corp_code: str
    business_year: int
    rcept_no: str
    rcept_dt: str
    report_name: str


def resolve_original_rcept(
    filings: pd.DataFrame | None, corp_code: str, year: int
) -> OriginalReport | None:
    """제출 목록(정정 포함, final=False)에서 원본 사업보고서 접수분을 고른다.

    규칙: report_nm에 '사업보고서' 포함 & '정정' 미포함 행 중 rcept_dt 최소(최초 제출).
    정정본은 원본이 아니다(전후꼬임 방지 — 입력은 정정 전 세상이 본 값이어야 한다).
    후보 없으면 None.
    """

    if filings is None or filings.empty:
        return None
    names = filings["report_nm"].astype(str)
    mask = names.str.contains(_ANNUAL, regex=False) & ~names.str.contains(_CORRECTION, regex=False)
    candidates = filings[mask].copy()
    if candidates.empty:
        return None
    row = candidates.sort_values("rcept_dt").iloc[0]  # 최초 제출 = 원본
    return OriginalReport(
        corp_code=corp_code,
        business_year=year,
        rcept_no=str(row["rcept_no"]),
        rcept_dt=str(row.get("rcept_dt", "")),
        report_name=str(row.get("report_nm", "")),
    )


def fetch_original(collector: Any, corp_code: str, year: int) -> OriginalReport | None:
    """원본 접수분 식별 — 네트워크(collector.filings) 사용. 실행 시에만 DART 호출.

    수집 자체(본문·XBRL 다운로드)는 호출측이 OriginalReport.rcept_no로 collector.document /
    save_xbrl_zip를 호출한다(SRP — 이 함수는 식별만).
    """

    submitted_year = year + 1
    filings = collector.filings(corp_code, f"{submitted_year}-01-01", f"{submitted_year}-12-31")
    return resolve_original_rcept(filings, corp_code, year)


__all__ = ["OriginalReport", "fetch_original", "resolve_original_rcept"]
