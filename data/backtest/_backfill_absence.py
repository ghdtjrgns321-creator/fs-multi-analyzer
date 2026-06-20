"""Backfill collection absence manifests for existing company-year raw folders.

This script records why source data is absent without re-downloading raw payloads.
It uses existing collection summaries, file metadata, and the note collection log.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.collect.storage import write_json

ROOT = Path("data/companies")
NOTE_LOG = Path("data/backtest/_dg_collect_all.jsonl")
EXPECTED_FS_ABSENCE = 347
EXPECTED_XBRL_ABSENCE = 163


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _csv_rows(path: Path) -> int:
    if not path.exists() or path.stat().st_size <= 5:
        return 0
    with path.open(encoding="utf-8-sig", errors="ignore") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def _load_note_statuses(path: Path = NOTE_LOG) -> dict[tuple[str, str], str]:
    statuses: dict[tuple[str, str], str] = {}
    if not path.exists():
        return statuses
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        corp, year, status = rec.get("corp"), rec.get("year"), rec.get("status")
        if corp and year and status:
            statuses[(str(corp), str(year))] = str(status)
    return statuses


def _statement_rows(summary: dict[str, Any], raw_dir: Path) -> int:
    fs_summary = summary.get("financial_statements")
    if isinstance(fs_summary, dict) and fs_summary:
        total = 0
        for value in fs_summary.values():
            if isinstance(value, dict):
                total += int(value.get("rows") or 0)
        return total
    return sum(_csv_rows(raw_dir / f"finstate_all_{fs}.csv") for fs in ("CFS", "OFS"))


def _ensure_statement_summary(summary: dict[str, Any], raw_dir: Path) -> None:
    fs_summary = summary.setdefault("financial_statements", {})
    if not isinstance(fs_summary, dict):
        summary["financial_statements"] = {}
        fs_summary = summary["financial_statements"]
    for fs in ("CFS", "OFS"):
        fs_summary.setdefault(
            fs,
            {
                "rows": _csv_rows(raw_dir / f"finstate_all_{fs}.csv"),
                "columns": [],
            },
        )


def _fs_absence(rows: int, note_status: str | None) -> str:
    if rows > 0:
        return "ok"
    if note_status == "no_report":
        return "no_report"
    return "dart_no_data"


def _xbrl_absence(raw_dir: Path, fs_reason: str, note_status: str | None) -> str:
    note_tsv = raw_dir / "notes_xbrl" / "note_facts.tsv"
    zip_path = raw_dir / "financial_statement_xbrl.zip"
    if note_tsv.exists() or (zip_path.exists() and zip_path.stat().st_size > 0):
        return "ok"
    if note_status == "no_report" or fs_reason == "no_report":
        return "no_report"
    if note_status == "no_zip":
        return "dart_no_xbrl"
    return "dart_no_xbrl"


def backfill(root: Path = ROOT) -> dict[str, int]:
    statuses = _load_note_statuses()
    counts = {
        "company_years": 0,
        "written": 0,
        "fs_absence": 0,
        "fs_no_report": 0,
        "fs_dart_no_data": 0,
        "xbrl_absence": 0,
        "xbrl_no_report": 0,
        "xbrl_dart_no_xbrl": 0,
    }
    for corp_dir in sorted(root.iterdir()):
        if not (corp_dir.is_dir() and corp_dir.name.isdigit()):
            continue
        for year_dir in sorted(corp_dir.iterdir()):
            if not (year_dir.is_dir() and year_dir.name.isdigit()):
                continue
            raw_dir = year_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            summary_path = raw_dir / "collection_summary.json"
            summary = _read_json(summary_path)
            _ensure_statement_summary(summary, raw_dir)
            rows = _statement_rows(summary, raw_dir)
            note_status = statuses.get((corp_dir.name, year_dir.name))
            fs_reason = _fs_absence(rows, note_status)
            xbrl_reason = _xbrl_absence(raw_dir, fs_reason, note_status)
            previous = summary.get("absence")
            summary["absence"] = {"fs": fs_reason, "xbrl_zip": xbrl_reason}
            summary.setdefault("xbrl_zip", None)
            summary.setdefault("notes", {"categories": 0, "details": {}})
            counts["company_years"] += 1
            if fs_reason != "ok":
                counts["fs_absence"] += 1
                counts[f"fs_{fs_reason}"] += 1
            if xbrl_reason != "ok":
                counts["xbrl_absence"] += 1
                counts[f"xbrl_{xbrl_reason}"] += 1
            if previous != summary["absence"] or not summary_path.exists():
                write_json(summary, summary_path)
                counts["written"] += 1
    return counts


def main() -> None:
    counts = backfill()
    print(
        "[absence-backfill] "
        f"company_years={counts['company_years']} written={counts['written']} "
        f"fs_absence={counts['fs_absence']} "
        f"(no_report={counts['fs_no_report']}, dart_no_data={counts['fs_dart_no_data']}) "
        f"expected_fs={EXPECTED_FS_ABSENCE} "
        f"xbrl_absence={counts['xbrl_absence']} "
        f"(no_report={counts['xbrl_no_report']}, dart_no_xbrl={counts['xbrl_dart_no_xbrl']}) "
        f"expected_xbrl={EXPECTED_XBRL_ABSENCE}"
    )


if __name__ == "__main__":
    main()
