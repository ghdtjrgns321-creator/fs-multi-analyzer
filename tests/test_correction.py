"""S9 — 정정공시 이력 수집 테스트(파싱 결정론 + 통합)."""

from pathlib import Path

import pandas as pd

from src.collect.correction import (
    collect_corrections,
    extract_correction_header,
    parse_corrections,
)


def _filings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            # 과거연도 재무 재작성(2019 사업보고서를 2022에 재제출).
            {
                "report_nm": "[기재정정]사업보고서 (2019.12)",
                "rcept_no": "R19",
                "rcept_dt": "20220512",
            },
            # 당해연도 사소 첨부정정(2021 보고서를 2022에).
            {
                "report_nm": "[첨부정정]반기보고서 (2022.06)",
                "rcept_no": "R22",
                "rcept_dt": "20220815",
            },
            # 정정 아님(원본) — 제외.
            {"report_nm": "사업보고서 (2021.12)", "rcept_no": "R21", "rcept_dt": "20220308"},
            # 재무류 아님(정정이지만 주요사항) — 제외.
            {"report_nm": "[기재정정]유상증자결정", "rcept_no": "RX", "rcept_dt": "20220601"},
        ]
    )


def test_parse_corrections_filters_and_classifies() -> None:
    rows = parse_corrections(_filings(), "00100")

    assert len(rows) == 2  # 재무류 정정 2건만(원본·유상증자 제외)
    by_no = {r.rcept_no: r for r in rows}
    assert by_no["R19"].report_kind == "사업보고서"
    assert by_no["R19"].period_year == 2019
    assert by_no["R19"].correction_type == "기재정정"
    assert by_no["R19"].is_past_year is True  # 2019 <= 2022-2
    assert by_no["R22"].is_past_year is False  # 2022 당해


def test_parse_corrections_graceful_on_empty() -> None:
    assert parse_corrections(pd.DataFrame(), "00100") == []
    assert parse_corrections(None, "00100") == []


def test_extract_correction_header_substantive_restatement() -> None:
    doc = (
        "<P>정정대상 공시서류 : 사업보고서 (2021.12) "
        "최초제출일 : 2022년 3월 8일 "
        "정정사유 : 재무제표 재작성에 따른 감사보고서 및 사업보고서 정정 "
        "정정사항 항목 정정 전 정정 후 자본위험 관리 ... 총차입금 736,971 768,890 "
        "【 대표이사 등의 확인 】 사 업 보 고 서 본문 시작 ...</P>"
    )

    header = extract_correction_header(doc)

    assert "재무제표 재작성" in header["correction_reason"]
    assert "정정사항" in header["change_summary"]
    assert "본문 시작" not in header["change_summary"]  # 본문 경계 차단


def test_extract_correction_header_graceful_when_absent() -> None:
    header = extract_correction_header("<P>일반 사업보고서 본문, 정정 헤더 없음</P>")
    assert header == {"correction_reason": "", "change_summary": ""}


class _FakeCollector:
    def __init__(self, filings: pd.DataFrame, docs: dict[str, str]) -> None:
        self._filings = filings
        self._docs = docs

    def filings(self, corp_code: str, start: str, end: str) -> pd.DataFrame:
        return self._filings

    def document(self, rcept_no: str) -> str:
        return self._docs.get(rcept_no, "")


def test_collect_corrections_integrates_and_saves(tmp_path: Path) -> None:
    docs = {
        "R19": "정정대상 공시서류 : 사업보고서 (2019.12) 정정사유 : 재무제표 재작성 정정사항 표 【 대표이사 등의 확인 】",
        "R22": "정정대상 공시서류 : 반기보고서 (2022.06) 정정사유 : 첨부정정 정정사항 첨부파일 교체 【 대표이사 등의 확인 】",
    }
    collector = _FakeCollector(_filings(), docs)

    records = collect_corrections(collector, "00100", data_dir=tmp_path)

    assert len(records) == 2
    r19 = next(r for r in records if r["rcept_no"] == "R19")
    assert "재무제표 재작성" in r19["correction_reason"]
    assert r19["is_past_year"] is True
    # 저장 확인.
    saved = tmp_path / "00100" / "raw" / "corrections.json"
    assert saved.exists()


def test_load_and_restated_years_roundtrip(tmp_path: Path) -> None:
    from src.collect.correction import load_corrections, restated_years

    docs = {
        "R19": "정정대상 공시서류 : 사업보고서 정정사유 : 재무제표 재작성 정정사항 표 【 대표이사 등의 확인 】",
        "R22": "정정대상 공시서류 : 반기보고서 정정사유 : 첨부정정 정정사항 첨부 【 대표이사 등의 확인 】",
    }
    collector = _FakeCollector(_filings(), docs)
    collect_corrections(collector, "00100", data_dir=tmp_path)

    assert len(load_corrections("00100", tmp_path)) == 2
    # 재작성(재무) 연도만 → 2019. 첨부정정(2022 반기)은 제외.
    assert restated_years("00100", tmp_path) == {2019}
    # 미수집 회사 graceful.
    assert load_corrections("99999", tmp_path) == []
    assert restated_years("99999", tmp_path) == set()


def test_collect_corrections_past_year_only_skips_detail_fetch(tmp_path: Path) -> None:
    # past_year_only=True면 당해 정정(R22)은 상세(정정사유) fetch 생략.
    docs = {
        "R19": "정정대상 공시서류 : 사업보고서 정정사유 : 재무제표 재작성 정정사항 표 【 대표이사 등의 확인 】"
    }
    collector = _FakeCollector(_filings(), docs)

    records = collect_corrections(collector, "00100", past_year_only=True, data_dir=tmp_path)

    r22 = next(r for r in records if r["rcept_no"] == "R22")
    assert r22["correction_reason"] == ""  # 당해는 상세 생략
    r19 = next(r for r in records if r["rcept_no"] == "R19")
    assert "재무제표 재작성" in r19["correction_reason"]  # 과거연도는 상세 수집
