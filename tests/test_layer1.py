"""Task B6 — Layer 1 오케스트레이터(monkeypatch run_reader, live 호출 0)."""

from src.db.normalized import read_report_extracts
from src.notes.report_parts import ReportPart
from src.report import layer1
from src.report.layer1 import estimate_krw
from src.schemas.extract import ExtractedItem, ReaderOutput


def _parts():
    return [
        ReportPart("II", "II. 사업의 내용", "2. 주요 제품\n제품 매출 서술"),
        ReportPart("III", "III. 재무", "1. 요약재무\n매출 5,000억원"),  # 재무결정론 — 스킵돼야
        ReportPart("XI", "XI. 투자자 보호", "제재현황 과징금 1,012억원 부과"),
    ]


def test_run_layer1_skips_financial_part_and_persists(monkeypatch, tmp_path):
    called_parts = []

    def fake_run_reader(part, focus, model_name=None):
        called_parts.append(part.numeral)
        out = ReaderOutput(
            items=[
                ExtractedItem(
                    part=part.numeral,
                    label="x",
                    statement=f"{part.numeral} 항목",
                    evidence=f"{part.numeral}.1",
                    why_relevant="검토",
                ),
            ]
        )
        return {"status": "ok", "output": out, "usage": {"input_tokens": 100, "output_tokens": 20}}

    monkeypatch.setattr(layer1, "run_reader", fake_run_reader)

    result = layer1.run_layer1("00126380", 2024, parts=_parts(), data_dir=tmp_path)

    # III(재무결정론)은 run_reader 호출 안 됨, 서술 II·XI만
    assert called_parts == ["II", "XI"]
    assert result["status"] == "ok"
    assert len(result["extracts"]) == 2
    # usage 합산(2회 × 100/20)
    assert result["usage"]["input_tokens"] == 200
    assert result["usage"]["output_tokens"] == 40
    assert "elapsed_s" in result  # 경과시간 반환
    # report_extracts 저장 왕복
    rows = read_report_extracts("00126380", 2024, data_dir=tmp_path)
    assert {r["part"] for r in rows} == {"II", "XI"}


def test_run_layer1_on_progress_called_per_narrative_part(monkeypatch, tmp_path):
    def fake_run_reader(part, focus, model_name=None):
        return {"status": "ok", "output": ReaderOutput(items=[]), "usage": {}}

    monkeypatch.setattr(layer1, "run_reader", fake_run_reader)

    events = []
    layer1.run_layer1(
        "00126380",
        2024,
        parts=_parts(),
        data_dir=tmp_path,
        on_progress=lambda p: events.append(p),
    )
    # 서술 파트 2개(II·XI)만큼 호출, III은 제외
    assert [e["numeral"] for e in events] == ["II", "XI"]
    assert [e["done"] for e in events] == [1, 2]
    assert all(e["total"] == 2 for e in events)


def test_estimate_krw_matches_assumed_pricing():
    # 입력 1e6 tok · 출력 0 → 1e6 × 2.5/1e6 × 1380 = ₩3450
    assert estimate_krw(1_000_000, 0) == 3450.0


def test_run_layer1_graceful_when_reader_skipped(monkeypatch, tmp_path):
    def skipped_reader(part, focus, model_name=None):
        return {"status": "skipped", "output": None, "message": "무키"}

    monkeypatch.setattr(layer1, "run_reader", skipped_reader)

    result = layer1.run_layer1("00126380", 2024, parts=_parts(), data_dir=tmp_path)

    assert result["status"] == "ok"
    assert result["extracts"] == []
    # 서술 파트는 per_part에 skipped로 기록(III 제외)
    statuses = {p["part"]: p["status"] for p in result["per_part"]}
    assert statuses == {"II": "skipped", "XI": "skipped"}
    # 0추출이므로 완결성 경고 발생(section_coverage)
    assert any(w["anchor"] == "section_coverage" for w in result["warnings"])
