"""분석 리포트 뷰 순수 HTML 함수 2케이스 검증 — Streamlit 런타임 불필요.

케이스A(findings 존재): 기대 앵커(회사명·계정·risk·표수·issue_type.value) 포함 확인.
케이스B(빈 입력): '없음/0건' 류 안내 문구 포함 확인(hollow 렌더 방지 §9).
"""

from __future__ import annotations

import pytest

from dashboard.report_view import (
    render_card_html,
    render_cards_section_html,
    render_header_html,
    render_queue_html,
    render_ratio_html,
    window_for_year,
)
from src.schemas.findings import AccountFinding, IssueType


# ── 연도 윈도우 순수함수 (연도 드롭다운 → 분석 윈도우) ─────────────────────
def test_window_for_year_target_is_max():
    # 2024 선택 → 이하 최근 4개(2024 포함). 2025는 제외(선택연도 초과).
    assert window_for_year([2022, 2023, 2024, 2025], 2024) == [2022, 2023, 2024]


def test_window_for_year_earlier_year_includes_priors():
    assert window_for_year([2022, 2023, 2024, 2025], 2023) == [2022, 2023]


def test_window_for_year_caps_size():
    assert window_for_year([2019, 2020, 2021, 2022, 2023], 2023, size=4) == [2020, 2021, 2022, 2023]


def test_window_for_year_empty():
    assert window_for_year([], 2024) == []


def test_available_norm_years_unknown_corp_empty():
    from src.report.company_report import available_norm_years

    assert available_norm_years("00000000_no_such") == []


ANNUAL_FS_CAPTION = (
    "연차별(사업연도) 재무제표 기준 분석입니다. 분기·반기 보고서는 지원하지 않습니다."
)


@pytest.mark.integration
def test_year_dropdown_and_annual_fs_caption_render():
    """회사 선택 상태에서 페이지가 (1) 연도 selectbox(최신 first) (2) 연차FS 안내(selectbox 옆 텍스트)를 렌더.

    로컬 정규화 데이터 필요 → 없으면 skip. 실패조건: 안내 문자열 불일치 또는 selectbox 미렌더.
    """

    from streamlit.testing.v1 import AppTest

    from src.report.company_report import available_norm_years

    corp = "00126380"
    if not available_norm_years(corp):
        pytest.skip("로컬 정규화 데이터 없음(00126380)")

    at = AppTest.from_file("dashboard/app.py", default_timeout=30)
    at.session_state["cs_selected_corp"] = corp
    at.session_state["cs_selected_name"] = "삼성전자"
    at.run()

    assert not at.exception
    assert len(at.selectbox) == 1
    assert any(ANNUAL_FS_CAPTION in m.value for m in at.markdown)
    opts = at.selectbox[0].options
    assert opts == sorted(opts, reverse=True)  # 최신 연도 first


# ── 케이스A 픽스처 ────────────────────────────────────────────────────────
FINDING_FULL = AccountFinding(
    account="매출채권",
    issue_type=IssueType.REVENUE_RECEIVABLES,
    subtype="회전율 급락",
    materiality_score=1_234_567.0,
    anomaly_score=2.5,
    confidence="High",
    counter_evidence=["현금흐름은 전기 대비 오히려 개선"],
    normal_explanation=["대형 수주 후 결제조건 연장 가능성"],
    confirm_question=["채권 연령분석표를 확인했는가?"],
    next_procedure=["주요 거래처 조회서 발송"],
    risk_level="High",
    vote_count=3,
    internal_total=4,
    reference_badges=["외부검색", "동종비교"],
    rebuttal_verdict="normal_dominant",
    prior_value="1,000,000",
    prior_year="2023",
    related_accounts=["매출", "대손충당금"],
)
FINDING_MIN = AccountFinding(
    account="재고자산",
    issue_type=IssueType.COST_INVENTORY,
    materiality_score=10.0,
    anomaly_score=0.5,
    confidence="Low",
    risk_level="Low",
    vote_count=1,
    internal_total=4,
)
QUEUE_ITEMS = [
    {
        "subject": "매출채권",
        "item_type": "account_finding",
        "issue": "revenue_receivables",
        "risk_level": "High",
        "materiality_score": 0.92,
        "key_evidence": "2024: 120,000,000",
        "audit_basis": ["ISA/KSA 315", "ISA/KSA 500"],
        "source_url": None,
    },
    {
        "subject": "유동비율",
        "item_type": "financial_ratio",
        "issue": "안정성 지표",
        "risk_level": "Low",
        "materiality_score": 1.35,
        "key_evidence": "2024: 1.35",
        "audit_basis": ["ISA/KSA 520"],
        "source_url": "https://example.test/ratio",
    },
]
RATIO_SUMMARY = {
    "수익성": {"영업이익률": 12.34, "순이익률": 8.1},
    "안정성": {"부채비율": 85.12},
}
SCOPE = {"accounts_reviewed": 12, "perspectives_run": 6, "unaccounted_cells": 3}


# ── render_header_html ───────────────────────────────────────────────────
def test_header_case_a_anchors() -> None:
    out = render_header_html("테스트기업", 2024, SCOPE)
    assert isinstance(out, str)
    assert "테스트기업" in out
    assert "2024" in out
    assert "계정 12개" in out and "관점 6개" in out
    assert "커버리지 경고" in out and "3건" in out  # unaccounted>0 표면화


def test_header_case_b_empty_scope() -> None:
    out = render_header_html("", None, {})
    assert isinstance(out, str)
    assert "계정 0개" in out and "관점 0개" in out
    assert "커버리지 경고" not in out  # unaccounted=0이면 경고 없음


# ── render_queue_html ────────────────────────────────────────────────────
def test_queue_case_a_anchors() -> None:
    out = render_queue_html(QUEUE_ITEMS)
    assert isinstance(out, str)
    assert "매출채권" in out and "유동비율" in out
    assert "account_finding" in out
    assert "High" in out and "Low" in out
    assert "120,000,000" in out
    assert "ISA/KSA 315" in out


def test_queue_case_b_empty() -> None:
    out = render_queue_html([])
    assert isinstance(out, str)
    assert "검토 큐 항목 없음" in out


# ── render_ratio_html ────────────────────────────────────────────────────
def test_ratio_case_a_anchors() -> None:
    out = render_ratio_html(RATIO_SUMMARY)
    assert isinstance(out, str)
    assert "수익성" in out and "안정성" in out
    assert "영업이익률" in out and "부채비율" in out
    assert "12.34" in out and "85.12" in out


def test_ratio_case_b_empty() -> None:
    out = render_ratio_html({})
    assert isinstance(out, str)
    assert "없음" in out


# ── render_card_html ─────────────────────────────────────────────────────
def test_card_full_object_anchors() -> None:
    out = render_card_html(FINDING_FULL)
    assert isinstance(out, str)
    assert "매출채권" in out
    assert IssueType.REVENUE_RECEIVABLES.value in out
    assert "회전율 급락" in out  # subtype 병기
    assert "표수 3/4" in out
    assert "High" in out
    assert "정상설명 우세" in out  # rebuttal_verdict 라벨
    assert "전기 2023" in out and "1,000,000" in out  # 전기값 병기
    assert "외부검색" in out
    assert "숫자상 반대 가능성" in out and "다음 절차" in out


def test_card_full_dict_input() -> None:
    # dict 입력도 동일 앵커 — _get이 객체/dict 양쪽을 지원해야 한다.
    out = render_card_html(FINDING_FULL.model_dump())
    assert isinstance(out, str)
    assert "매출채권" in out and "표수 3/4" in out and "정상설명 우세" in out


def test_card_min_empty_rebuttal() -> None:
    out = render_card_html(FINDING_MIN)
    assert isinstance(out, str)
    assert "재고자산" in out
    assert "반박 미수행" in out  # verdict None을 빈칸으로 숨기지 않음
    assert "세부 근거 목록 없음" in out  # 본문 4요소 전부 빈 리스트


# ── render_cards_section_html ────────────────────────────────────────────
def test_cards_section_case_a_anchors() -> None:
    out = render_cards_section_html("계정별 의심 후보", [FINDING_FULL, FINDING_MIN])
    assert isinstance(out, str)
    assert "계정별 의심 후보" in out
    assert "매출채권" in out and "재고자산" in out


def test_cards_section_case_b_empty() -> None:
    out = render_cards_section_html("회사 전체 이슈", [])
    assert isinstance(out, str)
    assert "회사 전체 이슈" in out
    assert "0건" in out  # 빈 섹션도 0건 명시(빈화면 금지)
