"""원본 접수분 식별 단위 테스트 — 정정 이력에서 최초 사업보고서를 고르는가."""

from __future__ import annotations

import pandas as pd

from golden.asfiled.resolve_original import resolve_original_rcept


def _filings(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_picks_original_when_correction_exists():
    # 원본(정정 미포함) + 정정본 2건 → 원본(최초 제출)을 골라야 한다.
    filings = _filings(
        [
            {
                "rcept_no": "20210322001065",
                "report_nm": "사업보고서 (2020.12)",
                "rcept_dt": "20210322",
            },
            {
                "rcept_no": "20240418000399",
                "report_nm": "[기재정정]사업보고서 (2020.12)",
                "rcept_dt": "20240418",
            },
            {
                "rcept_no": "20241002000389",
                "report_nm": "[기재정정]사업보고서 (2020.12)",
                "rcept_dt": "20241002",
            },
        ]
    )
    original = resolve_original_rcept(filings, "00117212", 2020)
    assert original is not None
    assert original.rcept_no == "20210322001065"  # 최초 제출 = 원본
    assert "정정" not in original.report_name


def test_returns_none_when_no_annual_report():
    # 사업보고서가 없으면 None(분기·반기만 있는 경우).
    filings = _filings(
        [
            {
                "rcept_no": "20210515000001",
                "report_nm": "분기보고서 (2021.03)",
                "rcept_dt": "20210515",
            }
        ]
    )
    assert resolve_original_rcept(filings, "00117212", 2020) is None


def test_returns_none_on_empty():
    assert resolve_original_rcept(pd.DataFrame(), "00117212", 2020) is None
