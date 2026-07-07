"""해체 엔진 Plan A — subsection 분할 + 주제 라우팅 + 커버리지 장부 테스트.

전부 결정론(LLM 0). 실데이터 2사(대주·삼성)로 항등식·라우팅 검증(ripple).
설계 §6·§8·§9(DISCLOSURE_DECOMPOSITION_DESIGN.md), 플랜 DECOMPOSITION_PLAN.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.notes.report_parts import ReportPart, SubSection, extract_parts, split_subsections
from src.report.section_router import (
    DEFAULT_ROUTING_PATH,
    is_empty_section,
    load_routing,
    route_report,
    route_title,
)


# ── Task 1: config 로더 ────────────────────────────────────────────────────
def test_load_routing_has_topics():
    routing = load_routing()
    assert "topics" in routing
    assert "revenue_receivables" in routing["topics"]
    assert "매출" in routing["topics"]["revenue_receivables"]
    assert DEFAULT_ROUTING_PATH.exists()


# ── Task 2: subsection 분할 ────────────────────────────────────────────────
def test_split_subsections_by_numbered_heading():
    part = ReportPart(
        numeral="I",
        title="I. 회사의 개요",
        text="1. 회사의 개요\n가나다 본문\n2. 회사의 연혁\n라마바 본문\n3. 자본금 변동사항\n사아자",
    )
    subs = split_subsections(part)
    assert [s.index for s in subs] == [1, 2, 3]
    assert subs[0].title == "회사의 개요"
    assert "가나다" in subs[0].text
    assert subs[1].title == "회사의 연혁"
    assert subs[2].numeral == "I"


def test_split_subsections_ignores_table_number_cells():
    part = ReportPart(numeral="X", title="X", text="1. 진짜 제목\n1\n2,000,000\n내용")
    subs = split_subsections(part)
    assert len(subs) == 1
    assert subs[0].title == "진짜 제목"


def test_split_subsections_no_header_single_block():
    part = ReportPart(numeral="Z", title="Z. 제목없음", text="헤더 없는 본문만")
    subs = split_subsections(part)
    assert len(subs) == 1
    assert subs[0].index == 0


# ── Task 3: 라우팅 + 해당없음 ───────────────────────────────────────────────
def test_route_title_matches_topic():
    routing = load_routing()
    assert route_title("주요 제품 및 서비스", routing) == "revenue_receivables"
    assert route_title("자본금 변동사항", routing) == "equity_capital"
    assert route_title("우발부채 등에 관한 사항", routing) == "contingency_related_party"


def test_route_title_unmatched_returns_none():
    assert route_title("듣도보도 못한 제목", load_routing()) is None


def test_is_empty_section_detects_해당없음():
    assert is_empty_section("- 해당사항 없음") is True
    assert is_empty_section("해당사항이 없습니다.") is True
    assert is_empty_section("소송가액 100억원 계류 중") is False


# ── Task 4: route_report + 장부 항등식 ─────────────────────────────────────
def _part(numeral, title, text):
    return ReportPart(numeral=numeral, title=title, text=text)


def test_route_report_ledger_identity():
    parts = [
        _part("II", "II. 사업의 내용", "2. 주요 제품 및 서비스\n매출 표\n9. 없는주제\n내용"),
        _part("XI", "XI. 투자자 보호", "1. 공시내용 진행 및 변경사항\n- 해당사항 없음"),
    ]
    result = route_report(parts)
    total = result.ledger["population"]
    accounted = result.ledger["routed"] + result.ledger["ignored"] + result.ledger["other"]
    assert total == accounted
    assert result.ledger["identity_ok"] is True
    assert "revenue_receivables" in result.routed
    assert any(s.title.startswith("없는주제") for s in result.other)
    assert any("공시내용" in s.title for s in result.ignored)


# ── Task 5: 실데이터 2사 통합(ripple) ──────────────────────────────────────
_REPORTS = {
    "대주": "data/companies/00112457/2024/raw/report_doc/business_report.xml",
    "삼성": "data/companies/00126380/2024/raw/report_doc/business_report.xml",
}


@pytest.mark.integration
@pytest.mark.parametrize("name,path", list(_REPORTS.items()))
def test_route_report_real_identity_and_routing(name, path):
    p = Path(path)
    if not p.exists():
        pytest.skip(f"{name} 원문 미보유")
    parts = extract_parts(p.read_text(encoding="utf-8"))
    result = route_report(parts)
    assert result.ledger["identity_ok"], f"{name} 장부 불일치: {result.ledger}"
    assert "revenue_receivables" in result.routed, f"{name} 매출 미라우팅"
    assert "contingency_related_party" in result.routed, f"{name} 특수관계 미라우팅"
    other_ratio = result.ledger["other"] / max(result.ledger["population"], 1)
    assert other_ratio < 0.5, f"{name} 기타 과다 {other_ratio:.0%} — 매핑 보강 필요"
