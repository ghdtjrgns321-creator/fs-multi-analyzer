"""S7 — 사업보고서 원문(business report) 수집기.

XBRL이 못 긁는 narrative(주석 서술·우발부채·대주주거래·연결범위 등)를 담은
사업보고서 전체 XML을 모아둔다. PART 추출(Step2)·LLM 투입(Step5)은 별도 단계이며,
여기서는 robust하게 *모아두기*만 한다(35 서식버전을 통째 XML로 흡수).

저장: data/companies/{corp}/{year}/raw/report_doc/business_report.xml
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from config.settings import settings
from src.collect.opendart import DartCollector

_REPORT_DOC_FILE = "business_report.xml"


def report_doc_dir(data_dir: Path, corp_code: str, year: int | str) -> Path:
    """Return and create the company/year report_doc directory."""

    path = data_dir / corp_code / str(year) / "raw" / "report_doc"
    path.mkdir(parents=True, exist_ok=True)
    return path


def report_doc_path(data_dir: Path, corp_code: str, year: int | str) -> Path:
    """Return the business report XML file path (does not create)."""

    return data_dir / corp_code / str(year) / "raw" / "report_doc" / _REPORT_DOC_FILE


def collect_report_doc(
    collector: DartCollector, corp_code: str, year: int, data_dir: Path
) -> dict[str, object]:
    """Fetch and store one company-year business report document.

    부재(보고서 없음/원문 미제공)는 예외가 아니라 status="absent"로 흡수한다.
    """

    report = collector.annual_report(corp_code, year)
    if report is None:
        return {"corp_code": corp_code, "year": year, "status": "absent", "reason": "no_report"}

    text = collector.document(report.rcept_no)
    if not text:
        return {
            "corp_code": corp_code,
            "year": year,
            "status": "absent",
            "reason": "dart_no_doc",
            "rcept_no": report.rcept_no,
        }

    path = report_doc_dir(data_dir, corp_code, year) / _REPORT_DOC_FILE
    path.write_text(text, encoding="utf-8")
    return {
        "corp_code": corp_code,
        "year": year,
        "status": "ok",
        "rcept_no": report.rcept_no,
        "bytes": len(text),
        "path": str(path),
    }


def collect_report_docs(
    items: list[tuple[str, int]],
    data_dir: Path | None = None,
    collector: DartCollector | None = None,
    workers: int = 8,
) -> list[dict[str, object]]:
    """Fetch many company-year business reports concurrently (ThreadPool).

    OpenDartReader 인스턴스는 thread-safe하게 공유 가능(probe 41.8 doc/s 실측).
    """

    root = data_dir or settings.data_dir
    api = collector or DartCollector()
    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(collect_report_doc, api, corp_code, year, root)
            for corp_code, year in items
        ]
        for future in as_completed(futures):
            results.append(future.result())
    return results
