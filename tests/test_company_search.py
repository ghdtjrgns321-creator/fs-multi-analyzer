"""회사명 검색 필터 검증 — 순수 filter_companies는 픽스처로, 실데이터는 통합 테스트로.

포지셔닝: 검색은 raw 명단 조회일 뿐(분석·판정 아님). 상장사 우선 정렬·빈쿼리 방어만 검증.
"""

from __future__ import annotations

import pandas as pd
import pytest

from dashboard.company_search import filter_companies, format_options


def _fixture_table() -> pd.DataFrame:
    # 상장(stock_code 有)·비상장 혼재 + 무관 회사. '삼성' 매치 3건 중 상장 2건.
    return pd.DataFrame(
        [
            {"corp_code": "00000001", "corp_name": "삼성전자", "stock_code": "005930"},
            {"corp_code": "00000002", "corp_name": "삼성물산", "stock_code": "028260"},
            {"corp_code": "00000003", "corp_name": "삼성비상장유동화", "stock_code": ""},
            {"corp_code": "00000004", "corp_name": "현대자동차", "stock_code": "005380"},
        ]
    )


def test_match_returns_hits_and_total():
    results, total = filter_companies(_fixture_table(), "삼성")
    assert total == 3
    codes = [r["corp_code"] for r in results]
    assert set(codes) == {"00000001", "00000002", "00000003"}


def test_listed_first_ordering():
    results, _ = filter_companies(_fixture_table(), "삼성")
    # 상장사(종목코드 有) 2건이 비상장보다 앞. 마지막은 비상장.
    assert results[-1]["corp_code"] == "00000003"
    assert all(r["stock_code"] for r in results[:2])


def test_empty_query_returns_empty():
    assert filter_companies(_fixture_table(), "") == ([], 0)
    assert filter_companies(_fixture_table(), "   ") == ([], 0)


def test_no_match_returns_empty():
    assert filter_companies(_fixture_table(), "없는회사명절대없음zzz") == ([], 0)


def test_limit_caps_results():
    results, total = filter_companies(_fixture_table(), "삼성", limit=1)
    assert len(results) == 1
    assert total == 3  # 전체 매치 수는 상한과 무관하게 실제 개수


def test_regex_chars_are_literal():
    table = pd.DataFrame(
        [{"corp_code": "00000009", "corp_name": "에이(비)씨", "stock_code": "000000"}]
    )
    results, total = filter_companies(table, "(비)")  # 정규식이면 폭주, 리터럴이면 1건
    assert total == 1 and results[0]["corp_code"] == "00000009"


def test_format_options_label_and_value():
    """드롭다운 (라벨, corp_code) — 라벨에 회사명+상장태그, value는 corp_code."""

    results = [
        {"corp_code": "00000001", "corp_name": "삼성전자", "stock_code": "005930"},
        {"corp_code": "00000003", "corp_name": "삼성비상장", "stock_code": ""},
    ]
    opts = format_options(results)
    assert opts[0] == ("삼성전자  ·  005930", "00000001")
    assert opts[1] == ("삼성비상장  ·  비상장", "00000003")


def test_format_options_empty():
    assert format_options([]) == []


@pytest.mark.integration
def test_real_data_finds_samsung_electronics():
    """실데이터 통합 — '삼성전자' 검색·포맷 결과에 삼성전자(00126380)가 포함되어야 한다.

    DART_API_KEY·네트워크 필요. 미구성 시 skip(단위 테스트는 위에서 커버).
    """

    try:
        from src.collect.opendart import DartCollector

        table = DartCollector().corp_code_table()
    except Exception as exc:  # noqa: BLE001 — 키·네트워크 부재는 skip
        pytest.skip(f"corp 명단 로드 불가: {type(exc).__name__}: {exc}")

    results, total = filter_companies(table, "삼성전자", limit=30)
    codes = [code for _, code in format_options(results)]
    assert "00126380" in codes, f"삼성전자 미포함 (총 {total}건, 상위: {codes[:5]})"
