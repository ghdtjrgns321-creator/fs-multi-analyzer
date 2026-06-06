"""L0 collection spike for Samsung Electronics.

Run:
    uv run python -m src.collect.spike
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from config.settings import settings
from src.collect.notes import TOCS, NoteCollector, write_note_detail
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
    include_notes: bool = True,
) -> dict[str, object]:
    """Collect raw financial statements and XBRL zip files for a company."""

    if not settings.dart_api_key:
        return {"status": "skipped", "reason": "DART_API_KEY is not configured"}

    collector = DartCollector()
    note_collector = NoteCollector() if include_notes else None
    note_categories = note_collector.categories() if note_collector else []
    root = data_dir or settings.data_dir
    summary: dict[str, object] = {"status": "ok", "corp_code": corp_code, "years": {}}
    years_payload: dict[str, object] = {}

    for year in years:
        raw_dir = year_dir(root, corp_code, year)
        year_summary: dict[str, object] = {
            "financial_statements": {},
            "xbrl_zip": None,
            "notes": {"categories": len(note_categories), "details": {}},
        }

        for fs_div in FS_DIVS:
            frame = collector.finstate_all(corp_code, year, fs_div)
            write_frame(frame, raw_dir / f"finstate_all_{fs_div}")
            year_summary["financial_statements"][fs_div] = {
                "rows": int(len(frame)),
                "columns": list(frame.columns),
            }

        report = collector.annual_report(corp_code, year) if include_xbrl else None
        if include_xbrl and report is not None:
            zip_path = raw_dir / "financial_statement_xbrl.zip"
            collector.save_xbrl_zip(report, zip_path)
            year_summary["xbrl_zip"] = {
                "rcept_no": report.rcept_no,
                "report_name": report.report_name,
                "path": str(zip_path),
            }

        if note_collector:
            note_dir = raw_dir / "notes"
            write_json(
                {"categories": [category.__dict__ for category in note_categories]},
                note_dir / "note_categories.json",
            )
            detail_summary: dict[str, object] = {}
            for fs_div, toc in TOCS.items():
                fs_summary: dict[str, object] = {}
                for category in note_categories:
                    html = note_collector.detail_html(corp_code, year, toc, category.code)
                    stats = write_note_detail(
                        html,
                        note_dir / fs_div / category.code,
                    )
                    fs_summary[category.code] = {"name": category.name, **stats}
                detail_summary[fs_div] = fs_summary
            year_summary["notes"]["details"] = detail_summary

        write_json(year_summary, raw_dir / "collection_summary.json")
        years_payload[str(year)] = year_summary

    summary["years"] = years_payload
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
