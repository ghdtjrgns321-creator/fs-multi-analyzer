from pathlib import Path
from types import SimpleNamespace

import duckdb
import pandas as pd

from src.collect.opendart import AnnualReport
from src.collect.spike import collect_company_years
from src.collect.storage import write_frame, write_json, year_dir


def test_year_dir_uses_company_year_raw_path(tmp_path: Path) -> None:
    path = year_dir(tmp_path, "00126380", 2024)

    assert path == tmp_path / "00126380" / "2024" / "raw"
    assert path.exists()


def test_write_frame_persists_csv_and_json(tmp_path: Path) -> None:
    frame = pd.DataFrame([{"account_nm": "자산총계", "thstrm_amount": "100"}])

    write_frame(frame, tmp_path / "finstate_all_CFS")

    assert (tmp_path / "finstate_all_CFS.csv").exists()
    assert (tmp_path / "finstate_all_CFS.json").exists()


def test_write_json_persists_utf8(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"

    write_json({"account_nm": "매출채권"}, path)

    assert "매출채권" in path.read_text(encoding="utf-8")


class _FakeDartCollector:
    reports: dict[int, AnnualReport | None] = {}
    frames: dict[tuple[int, str], pd.DataFrame] = {}
    zip_ok: bool = True

    def finstate_all(self, corp_code: str, year: int, fs_div: str) -> pd.DataFrame:
        return self.frames.get((year, fs_div), pd.DataFrame())

    def annual_report(self, corp_code: str, year: int) -> AnnualReport | None:
        return self.reports.get(year)

    def save_xbrl_zip(self, report: AnnualReport, path: Path) -> bool:
        if self.zip_ok:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"zip")
        return self.zip_ok

    def filings(self, corp_code: str, start: str, end: str) -> pd.DataFrame:
        return pd.DataFrame()

    def document(self, rcept_no: str) -> str:
        return ""

    def event(self, corp_code: str, key_word: str, start: str, end: str) -> pd.DataFrame:
        return pd.DataFrame()

    def report(self, corp_code: str, key_word: str, year: int) -> pd.DataFrame:
        return pd.DataFrame()


def test_collect_summary_absence_marks_dart_no_data_and_zip_failure(
    tmp_path: Path, monkeypatch
) -> None:
    report = AnnualReport("00123456", 2020, "20210331000001", "사업보고서")
    _FakeDartCollector.reports = {2020: report}
    _FakeDartCollector.frames = {(2020, "CFS"): pd.DataFrame(), (2020, "OFS"): pd.DataFrame()}
    _FakeDartCollector.zip_ok = False
    monkeypatch.setattr("src.collect.spike.DartCollector", _FakeDartCollector)
    monkeypatch.setattr("src.collect.spike.settings", SimpleNamespace(dart_api_key="x"))

    result = collect_company_years(
        "00123456",
        (2020,),
        data_dir=tmp_path,
        include_xbrl=True,
        include_notes=False,
    )

    year_summary = result["years"]["2020"]
    assert year_summary["absence"] == {"fs": "dart_no_data", "xbrl_zip": "dart_no_xbrl"}
    assert (tmp_path / "00123456" / "2020" / "raw" / "collection_summary.json").exists()


def test_collect_company_years_wires_corrections(tmp_path: Path, monkeypatch) -> None:
    report = AnnualReport("00123456", 2020, "20210331000001", "사업보고서")
    _FakeDartCollector.reports = {2020: report}
    _FakeDartCollector.frames = {(2020, "CFS"): pd.DataFrame(), (2020, "OFS"): pd.DataFrame()}
    _FakeDartCollector.zip_ok = True

    # 정정 이력: 2018 사업보고서를 2022에 재작성 재제출.
    def fake_filings(self, corp_code, start, end):
        return pd.DataFrame(
            [
                {
                    "report_nm": "[기재정정]사업보고서 (2018.12)",
                    "rcept_no": "RC18",
                    "rcept_dt": "20220512",
                }
            ]
        )

    def fake_document(self, rcept_no):
        return "정정대상 공시서류 : 사업보고서 정정사유 : 재무제표 재작성 정정사항 표 【 대표이사 등의 확인 】"

    monkeypatch.setattr(_FakeDartCollector, "filings", fake_filings, raising=False)
    monkeypatch.setattr(_FakeDartCollector, "document", fake_document, raising=False)
    monkeypatch.setattr("src.collect.spike.DartCollector", _FakeDartCollector)
    monkeypatch.setattr("src.collect.spike.settings", SimpleNamespace(dart_api_key="x"))

    result = collect_company_years(
        "00123456", (2020,), data_dir=tmp_path, include_xbrl=False, include_notes=False
    )

    assert result["corrections"]["restated_years"] == [2018]
    assert (tmp_path / "00123456" / "raw" / "corrections.json").exists()


def test_collect_summary_absence_marks_no_report(tmp_path: Path, monkeypatch) -> None:
    _FakeDartCollector.reports = {2020: None}
    _FakeDartCollector.frames = {(2020, "CFS"): pd.DataFrame(), (2020, "OFS"): pd.DataFrame()}
    _FakeDartCollector.zip_ok = False
    monkeypatch.setattr("src.collect.spike.DartCollector", _FakeDartCollector)
    monkeypatch.setattr("src.collect.spike.settings", SimpleNamespace(dart_api_key="x"))

    result = collect_company_years(
        "00123456",
        (2020,),
        data_dir=tmp_path,
        include_xbrl=True,
        include_notes=False,
    )

    assert result["years"]["2020"]["absence"] == {"fs": "no_report", "xbrl_zip": "no_report"}


def test_gap_machine_checks_uses_absence_manifest_for_missing_db(
    tmp_path: Path, monkeypatch
) -> None:
    import data.backtest._p1_review_all as review_all

    raw = tmp_path / "data" / "companies" / "00123456" / "2020" / "raw"
    raw.mkdir(parents=True)
    write_json(
        {"absence": {"fs": "dart_no_data", "xbrl_zip": "dart_no_xbrl"}},
        raw / "collection_summary.json",
    )
    monkeypatch.setattr(review_all, "PROJECT_ROOT", tmp_path)

    result = review_all.machine_checks("00123456", "2020")

    assert result["완결성"] == "미제공(dart_no_data)"


def test_gap_machine_checks_treats_known_missing_notes_as_provided_gap(
    tmp_path: Path, monkeypatch
) -> None:
    import data.backtest._p1_review_all as review_all

    raw = tmp_path / "data" / "companies" / "00123456" / "2020" / "raw"
    raw.mkdir(parents=True)
    write_json(
        {"absence": {"fs": "ok", "xbrl_zip": "dart_no_xbrl"}}, raw / "collection_summary.json"
    )
    db_name = "analysis" + ".duckdb"
    db = tmp_path / "data" / "companies" / "00123456" / "2020" / db_name
    con = duckdb.connect(str(db))
    try:
        con.execute(
            """
            CREATE TABLE normalized_financials AS
            SELECT '자산총계' canonical, 'CFS' fs_div, 'BS' sj_div, 100.0 amount
            UNION ALL SELECT '부채총계', 'CFS', 'BS', 40.0
            UNION ALL SELECT '자본총계', 'CFS', 'BS', 60.0
            UNION ALL SELECT '당기순이익', 'CFS', 'IS', 1.0
            UNION ALL SELECT '영업활동현금흐름', 'CFS', 'CF', 1.0
            """
        )
        con.execute("CREATE TABLE sce_equity_components AS SELECT 1 amount")
    finally:
        con.close()
    monkeypatch.setattr(review_all, "PROJECT_ROOT", tmp_path)

    result = review_all.machine_checks("00123456", "2020")

    assert result["완결성"] == "OK(주석미제공(dart_no_xbrl))"
    assert result["주석행"] == "미제공(dart_no_xbrl)"


def test_rawconflict_summary_parser_extracts_source_conflict_count() -> None:
    import data.backtest._p1_review_all as review_all

    parsed = review_all._parse_summary(
        "[기계요약] 완결성=OK 소실후보=0 전기소실=0 부호반전=0 "
        "병합다중라벨=0 원공시모순=2 SCE표준화=OK SCE검산=FAIL(1) 주석행=0/?"
    )

    assert parsed["원공시모순"] == 2


def test_f1_deduction_positive_raw_component_matches_negative_bare() -> None:
    import data.backtest._p1_review_all as review_all

    frame = pd.DataFrame(
        [
            {
                "fs_div": "CFS",
                "change_label": "배당",
                "account_id": "ifrs-full_DividendsPaid",
                "change_canonical": "배당금의 지급",
                "component_std": "-",
                "component_role": "marker",
                "amount": -100.0,
            },
            {
                "fs_div": "CFS",
                "change_label": "배당",
                "account_id": "ifrs-full_DividendsPaid",
                "change_canonical": "배당금의 지급",
                "component_std": "이익잉여금",
                "component_role": "leaf",
                "amount": 100.0,
            },
        ]
    )

    assert review_all.sce_raw_conflict_count(frame) == 0


def test_f1_excludes_unmatched_component_that_equals_other_component_sum() -> None:
    import data.backtest._p1_review_all as review_all

    frame = pd.DataFrame(
        [
            {
                "fs_div": "CFS",
                "change_label": "총포괄손익",
                "account_id": "",
                "change_canonical": "총포괄손익",
                "component_std": "-",
                "component_role": "marker",
                "amount": 30.0,
            },
            {
                "fs_div": "CFS",
                "change_label": "총포괄손익",
                "account_id": "",
                "change_canonical": "총포괄손익",
                "component_std": "이익잉여금",
                "component_role": "leaf",
                "amount": 10.0,
            },
            {
                "fs_div": "CFS",
                "change_label": "총포괄손익",
                "account_id": "",
                "change_canonical": "총포괄손익",
                "component_std": "기타포괄손익누계액",
                "component_role": "leaf",
                "amount": 20.0,
            },
            {
                "fs_div": "CFS",
                "change_label": "총포괄손익",
                "account_id": "",
                "change_canonical": "총포괄손익",
                "component_std": "지배기업 소유주지분",
                "component_role": "unmatched",
                "amount": 30.0,
            },
        ]
    )

    assert review_all.sce_raw_conflict_count(frame) == 0


def test_f1_real_source_contradiction_still_counts() -> None:
    import data.backtest._p1_review_all as review_all

    frame = pd.DataFrame(
        [
            {
                "fs_div": "CFS",
                "change_label": "오태깅",
                "account_id": "",
                "change_canonical": "기타 중요 계정",
                "component_std": "-",
                "component_role": "marker",
                "amount": 10.0,
            },
            {
                "fs_div": "CFS",
                "change_label": "오태깅",
                "account_id": "",
                "change_canonical": "기타 중요 계정",
                "component_std": "이익잉여금",
                "component_role": "leaf",
                "amount": -10.0,
            },
        ]
    )

    assert review_all.sce_raw_conflict_count(frame) == 1
