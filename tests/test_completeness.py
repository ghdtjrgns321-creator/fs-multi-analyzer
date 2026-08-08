"""Task B5 — 완결성 구조 결정론 앵커(섹션·가나다). anchor #3(물질금액)은 폐기(실측 catch 0)."""

from src.notes.report_parts import ReportPart
from src.report.completeness import completeness_warnings
from src.schemas.extract import ExtractedItem


def _item(part, statement, evidence="근거"):
    return ExtractedItem(
        part=part, label="x", statement=statement, evidence=evidence, why_relevant="y"
    )


def test_anchor_section_coverage_fires_on_empty_part():
    # II(서술파트)에 실질 subsection 있는데 추출물 0개 → section_coverage
    parts = [ReportPart("II", "II. 사업의 내용", "2. 주요 제품 및 서비스\n매출 내용 서술")]
    warns = completeness_warnings(parts, items=[])
    assert any(w["anchor"] == "section_coverage" and w["part"] == "II" for w in warns)


def test_anchor_ganada_fires_on_uncovered_ganada_subsection():
    parts = [
        ReportPart("VI", "VI. 이사회", "1. 이사회 운영\n가. 이사회 구성\n나. 주요 의결\n다. 위원회")
    ]
    warns = completeness_warnings(parts, items=[])
    ganada = [w for w in warns if w["anchor"] == "subsection_ganada" and w["part"] == "VI"]
    assert ganada, "가나다 항목 subsection 0추출 경고 없음"
    assert "가" in ganada[0]["reason"]


def test_covered_part_no_warning():
    # 추출물 있는 파트는 구조 앵커 경고 없음
    parts = [ReportPart("XI", "XI. 투자자 보호", "1. 제재\n가. 과징금\n나. 소송")]
    warns = completeness_warnings(parts, items=[_item("XI", "과징금 1,012억원")])
    assert warns == []


def test_excluded_part_out_of_scope():
    # XII(구조화 API 중복)는 앵커 대상 아님 — 0추출이어도 경고 없음
    parts = [ReportPart("XII", "XII. 상세표", "종속회사 상세 10,000억원")]
    warns = completeness_warnings(parts, items=[])
    assert warns == []


def test_notes_part_is_in_scope():
    # III은 리더 대상이 됐으므로(2026-08) 통째 0추출이면 누락 의심 경고를 받아야 한다.
    parts = [ReportPart("III", "III. 재무", "3. 연결재무제표 주석\n특수관계자 거래 5,000억원")]
    warns = completeness_warnings(parts, items=[])
    assert [w["part"] for w in warns] == ["III"]
