"""S7 Step4 — 온보딩 청크선별 모듈 테스트(LLM 호출 외 결정론 로직)."""

from pathlib import Path

import yaml

from src.notes.report_parts import ReportPart
from src.report import review_chunks as rc


def _parts() -> list[ReportPart]:
    return [
        ReportPart("II", "II. 사업의 내용", "마케팅 서술 보일러플레이트"),
        ReportPart("XI", "XI. 그 밖에 투자자 보호", "제재현황 과징금 3,915백만원 부과"),
        ReportPart("XII", "XII. 상세표", "기계적 상세표"),
    ]


def test_build_onboarding_input_excludes_marketing_and_detail_parts() -> None:
    body = rc.build_onboarding_input(_parts())

    assert "과징금" in body  # XI 포함
    assert "마케팅 서술" not in body  # II 제외
    assert "기계적 상세표" not in body  # XII 제외


def test_load_review_baseline_reads_disclosure_types() -> None:
    baseline = rc.load_review_baseline()

    assert "disclosure_types" in baseline
    assert "제재_규제" in baseline["disclosure_types"]


def test_baseline_hint_lists_disclosure_types() -> None:
    hint = rc._baseline_hint(rc.load_review_baseline())

    assert "제재_규제" in hint
    assert "메자닌_자금조달" in hint


def test_select_review_chunks_graceful_skip_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(rc.settings, "openai_api_key", "")

    result = rc.select_review_chunks(_parts(), "00100", "2022")

    assert result["status"] == "skipped"
    assert result["selection"] is None


def test_load_content_chunks_roundtrip_and_graceful(tmp_path: Path) -> None:
    path = tmp_path / "company_quirks.yaml"
    path.write_text("company_quirks: {}\n", encoding="utf-8")
    selection = rc.ReviewChunkSelection(
        corp_code="00200",
        year="2015",
        chunks=[
            rc.ReviewChunk(
                disclosure_type="담보_보증", part="III", evidence="담보 제공", why_review="검토"
            )
        ],
    )
    rc.persist_review_chunks("00200", "2015", selection, path=path)

    loaded = rc.load_content_chunks("00200", "2015", path=path)
    assert len(loaded) == 1 and loaded[0]["disclosure_type"] == "담보_보증"
    # 없는 회사/연도·없는 파일은 빈 리스트(graceful).
    assert rc.load_content_chunks("99999", "2099", path=path) == []
    assert rc.load_content_chunks("00200", "2015", path=tmp_path / "none.yaml") == []


def test_note_material_includes_report_review_chunks(tmp_path: Path) -> None:
    from src.report.materials import note_material

    path = tmp_path / "company_quirks.yaml"
    path.write_text("company_quirks: {}\n", encoding="utf-8")
    selection = rc.ReviewChunkSelection(
        corp_code="00300",
        year="2023",
        chunks=[
            rc.ReviewChunk(
                disclosure_type="제재_규제", part="XI", evidence="과징금", why_review="검토"
            )
        ],
    )
    rc.persist_review_chunks("00300", "2023", selection, path=path)

    # content_chunks 있는 회사(신시대): material에 실린다.
    mat = note_material("00300", 2023, quirks_path=path)
    assert mat["report_review_chunks"][0]["disclosure_type"] == "제재_규제"
    assert "report_review_role" in mat
    # 선별 없는 회사: 빈 리스트 + S7 미선별 경고(fallback 제거 — silent 0 금지 §9).
    mat_empty = note_material("00999", 2015, quirks_path=path)
    assert mat_empty["report_review_chunks"] == []
    assert "S7" in mat_empty["report_review_role"]
    assert "미선별" in mat_empty["report_review_role"]


def test_persist_review_chunks_writes_content_chunks(tmp_path: Path) -> None:
    path = tmp_path / "company_quirks.yaml"
    path.write_text("# header comment\ncompany_quirks: {}\n", encoding="utf-8")
    selection = rc.ReviewChunkSelection(
        corp_code="00100",
        year="2022",
        chunks=[
            rc.ReviewChunk(
                disclosure_type="제재_규제",
                part="XI",
                evidence="과징금 3,915백만원 부과",
                why_review="제재 발생 — 정상 설명 가능성 전제",
            )
        ],
    )

    quirks = rc.persist_review_chunks("00100", "2022", selection, path=path)

    assert quirks["00100"]["2022"]["content_chunks"][0]["disclosure_type"] == "제재_규제"
    # 재로드: 파일에 실제 기록 + 헤더 주석 보존.
    reloaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert reloaded["company_quirks"]["00100"]["2022"]["content_chunks"][0]["part"] == "XI"
    assert path.read_text(encoding="utf-8").startswith("# header comment")
