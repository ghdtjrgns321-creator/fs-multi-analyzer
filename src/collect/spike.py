"""L0 collection spike for Samsung Electronics.

Run:
    uv run python -m src.collect.spike
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from config.settings import settings
from src.collect.correction import collect_corrections
from src.collect.events import collect_events, collect_reports
from src.collect.opendart import DartCollector
from src.collect.storage import write_frame, write_json, year_dir

DEFAULT_CORP_CODE = "00126380"
DEFAULT_YEARS = (2025, 2024, 2023, 2022)
FS_DIVS = ("CFS", "OFS")


def collect_company_years(
    corp_code: str = DEFAULT_CORP_CODE,
    years: tuple[int, ...] = DEFAULT_YEARS,
    data_dir: Path | None = None,
    include_xbrl: bool = True,
    include_corrections: bool = True,
    include_events: bool = True,
) -> dict[str, object]:
    """Collect raw financial statements and XBRL zip files for a company."""

    if not settings.dart_api_key:
        return {"status": "skipped", "reason": "DART_API_KEY is not configured"}

    collector = DartCollector()
    root = data_dir or settings.data_dir
    summary: dict[str, object] = {"status": "ok", "corp_code": corp_code, "years": {}}
    years_payload: dict[str, object] = {}

    for year in years:
        raw_dir = year_dir(root, corp_code, year)
        report = collector.annual_report(corp_code, year) if include_xbrl else None
        year_summary: dict[str, object] = {
            "financial_statements": {},
            "xbrl_zip": None,
            "absence": {"fs": "ok", "xbrl_zip": "ok"},
        }

        fs_rows = 0
        for fs_div in FS_DIVS:
            frame = collector.finstate_all(corp_code, year, fs_div)
            fs_rows += len(frame)
            write_frame(frame, raw_dir / f"finstate_all_{fs_div}")
            year_summary["financial_statements"][fs_div] = {
                "rows": int(len(frame)),
                "columns": list(frame.columns),
            }
        if fs_rows == 0:
            year_summary["absence"]["fs"] = (  # type: ignore[index]
                "no_report" if include_xbrl and report is None else "dart_no_data"
            )

        if include_xbrl and report is None:
            year_summary["absence"]["xbrl_zip"] = "no_report"  # type: ignore[index]
        elif include_xbrl and report is not None:
            zip_path = raw_dir / "financial_statement_xbrl.zip"
            ok = collector.save_xbrl_zip(report, zip_path)
            if ok and zip_path.exists() and zip_path.stat().st_size > 0:
                year_summary["xbrl_zip"] = {
                    "rcept_no": report.rcept_no,
                    "report_name": report.report_name,
                    "path": str(zip_path),
                }
            else:
                year_summary["absence"]["xbrl_zip"] = "dart_no_xbrl"  # type: ignore[index]

        write_json(year_summary, raw_dir / "collection_summary.json")
        years_payload[str(year)] = year_summary

    summary["years"] = years_payload

    # S9: 정정공시 이력(데이터 출처: 원본/정정본·무엇이 바뀜). corp 단위 1회, 과거연도만 상세.
    if include_corrections:
        corrections = collect_corrections(collector, corp_code, past_year_only=True, data_dir=root)
        summary["corrections"] = {
            "count": len(corrections),
            "restated_years": sorted(
                {
                    c["period_year"]
                    for c in corrections
                    if "재작성" in str(c.get("correction_reason", "")) and c.get("period_year")
                }
            ),
        }

    # S10: 주요사항보고서 event(시점+조건) + 정기보고서 주요정보 report. 별도 참조 저장(재무DB 미연결).
    if include_events:
        events = collect_events(collector, corp_code, data_dir=root)
        reports = collect_reports(collector, corp_code, years, data_dir=root)
        summary["events"] = {"event_types": len(events), "report_types": len(reports)}

    write_json(
        {"collected_at": date.today().isoformat(), **summary},
        (root / corp_code / "collection_summary.json"),
    )
    return summary


def main() -> None:
    result = collect_company_years()
    print(result["status"])
    if result["status"] == "skipped":
        print(result["reason"])


if __name__ == "__main__":
    main()
