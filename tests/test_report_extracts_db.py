"""Task B4 — report_extracts DuckDB 저장/로드 왕복·격리·graceful."""

from src.db.normalized import read_report_extracts, write_report_extracts
from src.schemas.extract import ExtractedItem


def _items():
    return [
        ExtractedItem(
            part="XI",
            label="제재",
            statement="과징금 1,012억원",
            evidence="XI.3",
            why_relevant="고위험",
        ),
        ExtractedItem(
            part="VIII",
            label="특수관계",
            statement="이재용 등기임원",
            evidence="VIII.1",
            why_relevant="지배구조",
        ),
        ExtractedItem(
            part="V",
            label="KAM",
            statement="재고 순실현가치 평가",
            evidence="V.2",
            why_relevant="감사인 지적",
        ),
    ]


def test_roundtrip_preserves_rows(tmp_path):
    write_report_extracts(_items(), "00126380", 2024, data_dir=tmp_path)
    rows = read_report_extracts("00126380", 2024, data_dir=tmp_path)

    assert len(rows) == 3
    by_label = {r["label"]: r for r in rows}
    assert by_label["제재"]["statement"] == "과징금 1,012억원"
    assert by_label["제재"]["part"] == "XI"
    assert by_label["KAM"]["evidence"] == "V.2"


def test_company_year_isolation(tmp_path):
    write_report_extracts(_items(), "00126380", 2024, data_dir=tmp_path)
    # 다른 회사·연도는 미혼입(빈 결과)
    assert read_report_extracts("00112457", 2024, data_dir=tmp_path) == []
    assert read_report_extracts("00126380", 2023, data_dir=tmp_path) == []


def test_missing_db_and_empty_items_graceful(tmp_path):
    # 없는 DB → []
    assert read_report_extracts("99999", 2099, data_dir=tmp_path) == []
    # 빈 items write → read []
    write_report_extracts([], "00126380", 2024, data_dir=tmp_path)
    assert read_report_extracts("00126380", 2024, data_dir=tmp_path) == []
