"""Task B5 — 완결성 3중 결정론 앵커."""

from src.notes.report_parts import ReportPart
from src.report.completeness import completeness_warnings
from src.schemas.extract import ExtractedItem

_MAT = 1e8  # 물질성 임계 1억원


def _item(part, statement, evidence="근거"):
    return ExtractedItem(
        part=part, label="x", statement=statement, evidence=evidence, why_relevant="y"
    )


def test_anchor_section_coverage_fires_on_empty_part():
    # II(서술파트)에 실질 subsection 있는데 추출물 0개 → section_coverage
    parts = [ReportPart("II", "II. 사업의 내용", "2. 주요 제품 및 서비스\n매출 내용 서술")]
    warns = completeness_warnings(parts, items=[], materiality=_MAT)
    assert any(w["anchor"] == "section_coverage" and w["part"] == "II" for w in warns)


def test_anchor_ganada_fires_on_uncovered_ganada_subsection():
    parts = [
        ReportPart("VI", "VI. 이사회", "1. 이사회 운영\n가. 이사회 구성\n나. 주요 의결\n다. 위원회")
    ]
    warns = completeness_warnings(parts, items=[], materiality=_MAT)
    ganada = [w for w in warns if w["anchor"] == "subsection_ganada" and w["part"] == "VI"]
    assert ganada, "가나다 항목 subsection 0추출 경고 없음"
    assert "가" in ganada[0]["reason"]


def test_anchor_material_amount_fires_when_absent_and_silent_when_present():
    part = ReportPart("XI", "XI. 투자자 보호", "제재현황 과징금 1,012억원 부과")
    # 추출물이 그 금액을 담지 않음 → material_amount 경고
    absent = completeness_warnings([part], items=[_item("XI", "제재가 있었음")], materiality=_MAT)
    assert any(w["anchor"] == "material_amount" for w in absent)
    # 추출물이 그 금액을 인용 → 무경고(역grounding 매칭)
    present = completeness_warnings(
        [part], items=[_item("XI", "과징금 1,012억원 부과")], materiality=_MAT
    )
    assert not any(w["anchor"] == "material_amount" for w in present)


def test_material_anchor_silent_on_no_amount_narrative():
    # 금액 없는 순수 서술 → material_amount 앵커 무경고(정직한 잔여 한계)
    part = ReportPart("V", "V. 감사의견", "핵심감사사항은 재고 순실현가치 평가의 적정성이다")
    warns = completeness_warnings([part], items=[_item("V", "다른 내용")], materiality=_MAT)
    assert not any(w["anchor"] == "material_amount" for w in warns)


def test_financial_and_excluded_parts_out_of_scope():
    # III(재무결정론)·XII(제외)는 앵커 대상 아님 — 0추출이어도 경고 없음
    parts = [
        ReportPart("III", "III. 재무", "1. 요약재무\n매출 5,000억원"),
        ReportPart("XII", "XII. 상세표", "종속회사 상세 10,000억원"),
    ]
    warns = completeness_warnings(parts, items=[], materiality=_MAT)
    assert warns == []
