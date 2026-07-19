"""Streamlit 진입점 — 첫 화면이 곧 분석 리포트다(탭 없음).

실행: uv run python -m streamlit run dashboard/app.py
정비 페이지(게이트 검문·이탈 등록)는 별도 실행: uv run python -m streamlit run dashboard/onboarding.py
"""

from __future__ import annotations

import streamlit as st

from dashboard import report_view


def main() -> None:
    st.set_page_config(page_title="Disclosure Review Agent", layout="wide")
    report_view.render()


if __name__ == "__main__":
    main()
