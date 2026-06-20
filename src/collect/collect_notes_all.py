"""전수 주석(XBRL) 수집 직렬 러너.

data/companies의 모든 회사연도에 대해 사업보고서 XBRL zip을 받아 Arelle로 주석을 추출·저장한다.
- resume: 이미 notes_xbrl/note_facts.tsv가 있으면 건너뛴다(중단 후 재개 안전).
- API 절감: 회사단위 list 1회로 전 연도 사업보고서를 매칭한다.
- 결과: data/backtest/_dg_collect_all.jsonl (회사연도별 status append).

실행: PYTHONPATH=. uv run python -m src.collect.collect_notes_all          (전수)
      PYTHONPATH=. uv run python -m src.collect.collect_notes_all 00118345  (특정 회사만)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from config.settings import settings
from src.collect.notes_xbrl import (
    extract_note_facts,
    find_annual_reports_for_company,
    save_note_facts,
)
from src.collect.opendart import DartCollector

RESULT_PATH = Path("data/backtest/_dg_collect_all.jsonl")


def company_years(root: Path, corp: str) -> list[int]:
    return sorted(int(y.name) for y in (root / corp).iterdir() if y.is_dir() and y.name.isdigit())


def already_done(root: Path, corp: str, year: int) -> bool:
    return (root / corp / str(year) / "raw" / "notes_xbrl" / "note_facts.tsv").exists()


def run(corps: list[str] | None = None, log_every: int = 25) -> dict[str, int]:
    if not settings.dart_api_key:
        print("DART_API_KEY 미설정")
        return {}
    collector = DartCollector()
    root = settings.data_dir
    all_corps = corps or sorted(d.name for d in root.iterdir() if d.is_dir() and d.name.isdigit())
    counts = {"ok": 0, "no_report": 0, "no_zip": 0, "skip": 0}
    total_zip = 0
    total_cy = sum(len(company_years(root, c)) for c in all_corps)
    processed = 0
    t0 = time.perf_counter()

    with RESULT_PATH.open("a", encoding="utf-8") as out:
        for idx, corp in enumerate(all_corps):
            years = company_years(root, corp)
            pending = [y for y in years if not already_done(root, corp, y)]
            counts["skip"] += len(years) - len(pending)
            processed += len(years) - len(pending)
            if not pending:
                continue

            reports = find_annual_reports_for_company(collector, corp, pending)
            for year in pending:
                processed += 1
                rec: dict = {"corp": corp, "year": year}
                report = reports.get(year)
                if report is None:
                    rec["status"] = "no_report"
                    counts["no_report"] += 1
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    continue
                zip_path = root / corp / str(year) / "raw" / "financial_statement_xbrl.zip"
                ok = collector.save_xbrl_zip(report, zip_path)
                if not (ok and zip_path.exists() and zip_path.stat().st_size > 0):
                    rec["status"] = "no_zip"
                    counts["no_zip"] += 1
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    continue
                facts = extract_note_facts(zip_path)
                stats = save_note_facts(facts, zip_path.parent / "notes_xbrl")
                total_zip += zip_path.stat().st_size
                rec.update(
                    status="ok", facts=stats["fact_count"], zip_bytes=zip_path.stat().st_size
                )
                counts["ok"] += 1
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()

            if (idx + 1) % log_every == 0:
                el = (time.perf_counter() - t0) / 60
                print(
                    f"[{processed}/{total_cy}] 회사 {idx + 1}/{len(all_corps)} | "
                    f"ok={counts['ok']} no_report={counts['no_report']} "
                    f"no_zip={counts['no_zip']} skip={counts['skip']} | {el:.1f}분",
                    flush=True,
                )

    el = (time.perf_counter() - t0) / 60
    print(
        f"\n[완료] 처리 {processed}/{total_cy} | ok={counts['ok']} "
        f"no_report={counts['no_report']} no_zip={counts['no_zip']} skip={counts['skip']}"
    )
    print(f"신규 수집 zip {total_zip / 1e9:.2f}GB | {el:.1f}분 | 로그 {RESULT_PATH}")
    return counts


def main() -> None:
    run(sys.argv[1:] or None)


if __name__ == "__main__":
    main()
