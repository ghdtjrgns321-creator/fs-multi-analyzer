"""첫 화면 회사명 검색 — OpenDART 등록회사(약 12만개)를 회사명 substring으로 찾는다.

'삼성' 입력 → 삼성 관련 등록회사가 아래로 쭉(상장사 우선) → 클릭 시 corp_code 선택.
corp_codes 명단은 최초 1회만 로드(st.cache_data). 검색·필터는 프레젠테이션 관심사라
DartCollector(raw 조회)와 분리한다. corp_code·연도는 데이터에서 오고 하드코딩하지 않는다.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

# 결과 표시 상한 — '삼' 같은 광범위 쿼리는 수백건이라 상위만 카드로(전체는 쿼리를 좁혀 도달).
SEARCH_LIMIT = 30


@st.cache_data(show_spinner="회사 명단 로딩 중...")
def _corp_table() -> pd.DataFrame:
    """등록회사 명단을 1회 로드해 캐시(corp_code·corp_name·stock_code만)."""

    from src.collect.opendart import DartCollector

    table = DartCollector().corp_code_table()
    return table[["corp_code", "corp_name", "stock_code"]].copy()


def search_companies(query: str, limit: int = SEARCH_LIMIT) -> tuple[list[dict[str, str]], int]:
    """회사명 substring 검색. 반환 (상위 결과 list, 전체 매치 수). 상장사 우선 정렬.

    regex=False — 회사명의 괄호 등 특수문자를 리터럴로 취급(정규식 오폭주 차단).
    """

    return filter_companies(_corp_table(), query, limit)


def filter_companies(
    table: pd.DataFrame, query: str, limit: int = SEARCH_LIMIT
) -> tuple[list[dict[str, str]], int]:
    """순수 필터 — 명단 로드와 분리(테스트가 픽스처 DataFrame으로 직접 호출).

    regex=False — 회사명의 괄호 등 특수문자를 리터럴로 취급(정규식 오폭주 차단).
    """

    q = (query or "").strip()
    if not q:
        return [], 0
    matched = table[table["corp_name"].str.contains(q, regex=False, na=False)].copy()
    total = len(matched)
    if total == 0:
        return [], 0
    stock = matched["stock_code"].astype(str).str.strip()
    matched["_listed"] = stock.ne("") & stock.ne("nan")  # 종목코드 있으면 상장사
    matched = matched.sort_values(["_listed", "corp_name"], ascending=[False, True]).head(limit)
    results = [
        {
            "corp_code": str(row.corp_code),
            "corp_name": str(row.corp_name),
            "stock_code": str(row.stock_code).strip(),
        }
        for row in matched.itertuples()
    ]
    return results, total


def format_options(results: list[dict[str, str]]) -> list[tuple[str, str]]:
    """검색 결과를 드롭다운 (라벨, corp_code) 튜플로 — 순수(session_state·st 미사용).

    라벨: 회사명 + 상장(종목코드)/비상장 태그. value: 선택 시 반환될 corp_code.
    """

    return [
        (f"{r['corp_name']}  ·  {r['stock_code'] or '비상장'}", r["corp_code"]) for r in results
    ]


def _searchbox_options(searchterm: str) -> list[tuple[str, str]]:
    """st_searchbox 콜백 — 타이핑마다 호출. format_options로 (라벨, corp_code) 반환.

    선택 후 회사명 표시를 위해 corp_code→회사명을 session_state에 캐시한다.
    명단 로드 실패(키·네트워크)는 빈 리스트로 흡수(드롭다운만 비고 크래시 없음).
    """

    try:
        results, _ = search_companies(searchterm or "")
    except Exception:  # noqa: BLE001 — 콜백에서 예외 던지면 위젯이 깨짐 → 빈 결과로 흡수
        return []
    name_cache = st.session_state.setdefault("cs_name_by_code", {})
    for row in results:
        name_cache[row["corp_code"]] = row["corp_name"]
    return format_options(results)


def render_company_search() -> str | None:
    """실시간 회사명 검색(st_searchbox) — 타이핑마다 드롭다운. 선택된 corp_code 반환.

    st_searchbox가 keystroke마다 _searchbox_options를 호출해 드롭다운을 갱신하고,
    항목 선택 시 그 corp_code를 반환한다. 선택 상태는 session_state에 유지한다.
    """

    from streamlit_searchbox import st_searchbox

    selected = st_searchbox(
        _searchbox_options,
        placeholder="회사명 검색 (예: 삼성)",
        key="company_searchbox",
        rerun_on_update=True,
    )
    if selected:
        st.session_state["cs_selected_corp"] = selected
        name = st.session_state.get("cs_name_by_code", {}).get(selected, "")
        if name:
            st.session_state["cs_selected_name"] = name
    return st.session_state.get("cs_selected_corp")
