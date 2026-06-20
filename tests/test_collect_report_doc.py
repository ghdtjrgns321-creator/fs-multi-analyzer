"""S7 Step1 — 사업보고서 원문 수집기 테스트.

document() 오류 흡수 + report_doc 단건/동시 batch 수집·저장 검증.
"""

from pathlib import Path

from src.collect.report_doc import (
    collect_report_doc,
    collect_report_docs,
    report_doc_path,
)

from src.collect.opendart import AnnualReport, DartCollector


class _FakeReader:
    """OpenDartReader 대역 — document만 흉내."""

    def __init__(self, payloads: dict[str, object]) -> None:
        self._payloads = payloads

    def document(self, rcept_no: str) -> object:
        value = self._payloads[rcept_no]
        if isinstance(value, Exception):
            raise value
        return value


def _collector(payloads: dict[str, object]) -> DartCollector:
    collector = DartCollector(api_key="x")
    collector._dart = _FakeReader(payloads)
    return collector


def test_document_returns_full_xml_text() -> None:
    collector = _collector({"R1": "<DOCUMENT>사업보고서</DOCUMENT>"})

    assert collector.document("R1") == "<DOCUMENT>사업보고서</DOCUMENT>"


def test_document_absorbs_valueerror_as_empty() -> None:
    # OpenDART는 원문 미제공 보고서에 ValueError를 던진다 → 부재이므로 ""로 흡수.
    collector = _collector({"R2": ValueError("no file")})

    assert collector.document("R2") == ""


class _FakeCollector:
    """annual_report + document 대역."""

    def __init__(
        self, reports: dict[tuple[str, int], AnnualReport | None], docs: dict[str, str]
    ) -> None:
        self._reports = reports
        self._docs = docs

    def annual_report(self, corp_code: str, year: int) -> AnnualReport | None:
        return self._reports.get((corp_code, year))

    def document(self, rcept_no: str) -> str:
        return self._docs.get(rcept_no, "")


def test_collect_report_doc_saves_xml_and_returns_ok(tmp_path: Path) -> None:
    report = AnnualReport("00100", 2022, "RC1", "사업보고서")
    collector = _FakeCollector({("00100", 2022): report}, {"RC1": "<DOC>본문</DOC>"})

    result = collect_report_doc(collector, "00100", 2022, tmp_path)

    assert result["status"] == "ok"
    assert result["rcept_no"] == "RC1"
    saved = report_doc_path(tmp_path, "00100", 2022)
    assert saved.exists()
    assert saved.read_text(encoding="utf-8") == "<DOC>본문</DOC>"


def test_collect_report_doc_absent_when_no_report(tmp_path: Path) -> None:
    collector = _FakeCollector({("00100", 2022): None}, {})

    result = collect_report_doc(collector, "00100", 2022, tmp_path)

    assert result["status"] == "absent"
    assert result["reason"] == "no_report"
    assert not report_doc_path(tmp_path, "00100", 2022).exists()


def test_collect_report_doc_absent_when_document_empty(tmp_path: Path) -> None:
    report = AnnualReport("00100", 2022, "RC1", "사업보고서")
    collector = _FakeCollector({("00100", 2022): report}, {"RC1": ""})

    result = collect_report_doc(collector, "00100", 2022, tmp_path)

    assert result["status"] == "absent"
    assert result["reason"] == "dart_no_doc"


def test_collect_report_docs_batch_concurrent(tmp_path: Path) -> None:
    # ripple: 서로 다른 corp/year 2건 동시 수집 + 부재 1건 혼재.
    reports = {
        ("00100", 2022): AnnualReport("00100", 2022, "RC1", "사업보고서"),
        ("00200", 2023): AnnualReport("00200", 2023, "RC2", "사업보고서"),
        ("00300", 2021): None,
    }
    docs = {"RC1": "<DOC>A</DOC>", "RC2": "<DOC>B</DOC>"}
    collector = _FakeCollector(reports, docs)

    results = collect_report_docs(
        [("00100", 2022), ("00200", 2023), ("00300", 2021)],
        tmp_path,
        collector=collector,
        workers=3,
    )

    by_corp = {r["corp_code"]: r for r in results}
    assert by_corp["00100"]["status"] == "ok"
    assert by_corp["00200"]["status"] == "ok"
    assert by_corp["00300"]["status"] == "absent"
    assert report_doc_path(tmp_path, "00100", 2022).read_text(encoding="utf-8") == "<DOC>A</DOC>"
    assert report_doc_path(tmp_path, "00200", 2023).read_text(encoding="utf-8") == "<DOC>B</DOC>"
