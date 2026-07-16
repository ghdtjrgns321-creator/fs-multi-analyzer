"""annual_report 원본 해소 단위테스트 — 정정이력 회사에서 대상연도 원본(as-filed) 선택.

버그: 구 annual_report(final=True)가 정정이력 회사의 대상 사업보고서를 누락(셀=None·아=오년도).
수정: 기간필터 "(year.12)" + 정정미포함 원본(최초제출) 선택. 순수함수라 네트워크 없이 검증.
"""

from __future__ import annotations

import pandas as pd

from src.collect.opendart import select_annual_report


def _filings(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_picks_original_over_corrections_same_year():
    # 원본 + 정정 2건(같은 사업연도) → 최초 원본(정정 미포함) 선택.
    filings = _filings(
        [
            {
                "rcept_no": "20200330003829",
                "report_nm": "사업보고서 (2019.12)",
                "rcept_dt": "20200330",
            },
            {
                "rcept_no": "20200410002837",
                "report_nm": "[기재정정]사업보고서 (2019.12)",
                "rcept_dt": "20200410",
            },
            {
                "rcept_no": "20220512000850",
                "report_nm": "[기재정정]사업보고서 (2019.12)",
                "rcept_dt": "20220512",
            },
        ]
    )
    r = select_annual_report(filings, "00413046", 2019)
    assert r is not None
    assert r.rcept_no == "20200330003829"  # 최초 원본 = as-filed
    assert "정정" not in r.report_name


def test_ignores_other_year_corrections():
    # 대상연도(2020) 원본 + 타연도(2018·2019) 정정 섞임 → (2020.12)만 선택(구 버그 재현 방지).
    filings = _filings(
        [
            {
                "rcept_no": "20210205000367",
                "report_nm": "[기재정정]사업보고서 (2018.12)",
                "rcept_dt": "20210205",
            },
            {
                "rcept_no": "20210205000383",
                "report_nm": "[기재정정]사업보고서 (2019.12)",
                "rcept_dt": "20210205",
            },
            {
                "rcept_no": "20210322000920",
                "report_nm": "사업보고서 (2020.12)",
                "rcept_dt": "20210322",
            },
        ]
    )
    r = select_annual_report(filings, "00409681", 2020)
    assert r is not None
    assert r.rcept_no == "20210322000920"  # 2020 원본(타년도 정정에 오염 금지)


def test_single_report_returned():
    filings = _filings(
        [
            {
                "rcept_no": "20210331004698",
                "report_nm": "사업보고서 (2020.12)",
                "rcept_dt": "20210331",
            }
        ]
    )
    r = select_annual_report(filings, "00000000", 2020)
    assert r is not None and r.rcept_no == "20210331004698"


def test_correction_only_fallback():
    # 원본이 window 밖이라 정정만 남은 경우 → 최초 정정 fallback(None 아님).
    filings = _filings(
        [
            {
                "rcept_no": "20240208001322",
                "report_nm": "[기재정정]사업보고서 (2020.12)",
                "rcept_dt": "20240208",
            }
        ]
    )
    r = select_annual_report(filings, "00409681", 2020)
    assert r is not None and r.rcept_no == "20240208001322"


def test_none_when_no_matching_year():
    filings = _filings(
        [
            {
                "rcept_no": "20210515000001",
                "report_nm": "분기보고서 (2021.03)",
                "rcept_dt": "20210515",
            }
        ]
    )
    assert select_annual_report(filings, "00409681", 2020) is None
    assert select_annual_report(pd.DataFrame(), "00409681", 2020) is None
