"""Streamlit 진입점 (스캐폴딩). import smoke 통과용 최소 구현.

실행: uv run streamlit run dashboard/app.py
"""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Disclosure Review Agent", layout="wide")
    st.title("Disclosure Review Agent")
    st.caption("공시 재무제표·주석 변화 리뷰 — 감사인 검토 후보 제시 (스캐폴딩)")
    st.info("뼈대 단계입니다. L0~L4 파이프라인 구현 후 리포트가 표시됩니다.")


if __name__ == "__main__":
    main()
