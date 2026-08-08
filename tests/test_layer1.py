"""Task B6 — Layer 1 오케스트레이터(monkeypatch run_reader, live 호출 0)."""

from src.db.normalized import read_report_extracts
from src.notes.report_parts import ReportPart
from src.report import layer1
from src.report.layer1 import estimate_krw
from src.schemas.extract import ExtractedItem, ReaderOutput


def _parts():
    return [
        ReportPart("II", "II. 사업의 내용", "2. 주요 제품\n제품 매출 서술"),
        # III은 재무 수치가 아니라 주석 서술 때문에 리더 대상이다(2026-08 편입).
        ReportPart("III", "III. 재무", "3. 연결재무제표 주석\n특수관계자 거래 5,000억원"),
        ReportPart("XII", "XII. 상세표", "종속회사 상세"),  # 구조화 API 중복 — 스킵돼야
        ReportPart("XI", "XI. 투자자 보호", "제재현황 과징금 1,012억원 부과"),
    ]


def test_run_layer1_reads_notes_part_and_skips_excluded(monkeypatch, tmp_path):
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

    # III(주석)은 호출됨, XII(구조화 API 중복)만 스킵
    assert called_parts == ["II", "III", "XI"]
    assert result["status"] == "ok"
    assert len(result["extracts"]) == 3
    # usage 합산(3회 × 100/20)
    assert result["usage"]["input_tokens"] == 300
    assert result["usage"]["output_tokens"] == 60
    assert "elapsed_s" in result  # 경과시간 반환
    # report_extracts 저장 왕복
    rows = read_report_extracts("00126380", 2024, data_dir=tmp_path)
    assert {r["part"] for r in rows} == {"II", "III", "XI"}


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
    # 서술 파트 3개(II·III·XI)만큼 호출, XII는 제외
    assert [e["numeral"] for e in events] == ["II", "III", "XI"]
    assert [e["done"] for e in events] == [1, 2, 3]
    assert all(e["total"] == 3 for e in events)


def test_run_layer1_chunks_long_part_into_multiple_reader_calls(monkeypatch, tmp_path):
    # III이 길면(실측 최대 66만 자) 한 파트가 여러 번 호출된다 — 청킹 배선 확인.
    seen = []

    def fake_run_reader(part, focus, model_name=None):
        seen.append(part.title)
        return {"status": "ok", "output": ReaderOutput(items=[]), "usage": {}}

    monkeypatch.setattr(layer1, "run_reader", fake_run_reader)
    long_part = [ReportPart("III", "III. 재무", "주석 본문\n" * 30_000)]  # 18만 자
    layer1.run_layer1("00126380", 2024, parts=long_part, data_dir=tmp_path)

    assert len(seen) > 1
    assert all("III. 재무 (" in t for t in seen)


def test_estimate_krw_matches_assumed_pricing():
    # 입력 1e6 tok · 출력 0 → 1e6 × 2.5/1e6 × 1380 = ₩3450
    assert estimate_krw(1_000_000, 0) == 3450.0


def test_run_layer1_all_skipped_is_not_ok(monkeypatch, tmp_path):
    """전 파트 미실행(무키)은 "추출 0건"이 아니다 — status로 구분해 override 경고를 태운다."""

    def skipped_reader(part, focus, model_name=None):
        return {"status": "skipped", "output": None, "message": "무키"}

    monkeypatch.setattr(layer1, "run_reader", skipped_reader)

    result = layer1.run_layer1("00126380", 2024, parts=_parts(), data_dir=tmp_path)

    assert result["status"] == "skipped"
    assert result["extracts"] == []
    statuses = {p["part"]: p["status"] for p in result["per_part"]}
    assert statuses == {"II": "skipped", "III": "skipped", "XI": "skipped"}
    # 미실행은 저장하지 않는다 — 빈 테이블이 "실행됐고 0건"으로 위장하는 것 차단
    assert read_report_extracts("00126380", 2024, data_dir=tmp_path) == []


def test_run_layer1_all_errors_is_error_and_preserves_prior_extracts(monkeypatch, tmp_path):
    """전 파트 LLM 실패는 status=error — "0건"으로 위장 금지 + 이전 정상 추출분 보존.

    셀트리온 2019 오진의 재발 방지: 실패 실행이 빈 replace로 기존 데이터를 덮으면
    다음 세션엔 재조사할 증거가 없다."""

    def ok_reader(part, focus, model_name=None):
        out = ReaderOutput(
            items=[
                ExtractedItem(
                    part=part.numeral,
                    label="소송",
                    statement="손해배상 청구",
                    evidence="XI.1",
                    why_relevant="우발부채",
                )
            ]
        )
        return {"status": "ok", "output": out, "usage": {"input_tokens": 10, "output_tokens": 2}}

    monkeypatch.setattr(layer1, "run_reader", ok_reader)
    layer1.run_layer1("00126380", 2024, parts=_parts(), data_dir=tmp_path)
    assert len(read_report_extracts("00126380", 2024, data_dir=tmp_path)) == 3

    def error_reader(part, focus, model_name=None):
        return {"status": "error", "output": None, "message": "TimeoutError: ..."}

    monkeypatch.setattr(layer1, "run_reader", error_reader)
    result = layer1.run_layer1("00126380", 2024, parts=_parts(), data_dir=tmp_path)

    assert result["status"] == "error"
    assert "실행 실패" in result["message"]
    # 이전 정상 추출 3건이 빈 테이블로 덮이지 않았다
    assert len(read_report_extracts("00126380", 2024, data_dir=tmp_path)) == 3


def test_run_layer1_completed_zero_items_is_empty(monkeypatch, tmp_path):
    """리더가 정상 완주했는데 0건이면 "empty" — 대형사에서 감사관심 0건은 그 자체가 이상 신호."""

    def empty_reader(part, focus, model_name=None):
        return {"status": "ok", "output": ReaderOutput(items=[]), "usage": {}}

    monkeypatch.setattr(layer1, "run_reader", empty_reader)
    result = layer1.run_layer1("00126380", 2024, parts=_parts(), data_dir=tmp_path)

    assert result["status"] == "empty"
    # 완주했으므로 저장은 수행(빈 테이블 = "실행됐고 진짜 0건"의 증거)
    assert read_report_extracts("00126380", 2024, data_dir=tmp_path) == []
    assert any(w["anchor"] == "section_coverage" for w in result["warnings"])
