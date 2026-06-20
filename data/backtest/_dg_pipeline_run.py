"""표본 수집 실행: notes_xbrl 파이프라인(정정 대응 보고서 탐색 → XBRL 다운로드 →
Arelle 주석 추출 → TSV 저장)을 분식 표본에 돌려 받아진 주석 수·종류를 수치화.

저장 위치: data/companies/{corp}/{year}/raw/notes_xbrl/note_facts.tsv
재현: PYTHONPATH=. uv run python data/backtest/_dg_pipeline_run.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from config.settings import settings
from src.collect.notes_xbrl import extract_note_facts, find_annual_report, save_note_facts
from src.collect.opendart import DartCollector

sys.path.insert(0, str(Path(__file__).parent))
from _dg_arelle_probe import NOTE_KEYWORDS  # noqa: E402

# 분식 표본(소형사 위주) — 회사명은 백테스트 결과 corp_code.
SAMPLES = [
    ("00409681", 2018, "아스트(정정)"),
    ("00409681", 2019, "아스트(정정)"),
    ("01091382", 2020, "세토피아"),
    ("00127699", 2020, "유네코"),
    ("00526696", 2021, "웨이브일렉트로닉스"),
    ("00141273", 2020, "웰바이오텍"),
    ("00116426", 2019, "이렘"),
    ("00163716", 2019, "한창"),
    ("00118345", 2020, "디아이동일"),
    ("00657783", 2022, "모델솔루션"),
]


def note_category_counts(facts) -> dict[str, int]:
    counts = Counter()
    for f in facts:
        hay = f"{f.concept} {f.label_ko}"
        for cat, kws in NOTE_KEYWORDS.items():
            if any(kw in hay for kw in kws):
                counts[cat] += 1
    return {k: counts.get(k, 0) for k in NOTE_KEYWORDS}


def main() -> None:
    if not settings.dart_api_key:
        print("DART_API_KEY 미설정")
        return
    collector = DartCollector()
    root = settings.data_dir
    results = []
    for corp, year, name in SAMPLES:
        row: dict = {"corp": corp, "name": name, "year": year}
        report = find_annual_report(collector, corp, year)
        if report is None:
            row["report_found"] = False
            results.append(row)
            print(f"{name}/{year}: 사업보고서 없음(정정 포함 탐색)")
            continue
        row["report_found"] = True
        row["report_name"] = report.report_name
        zip_path = root / corp / str(year) / "raw" / "financial_statement_xbrl.zip"
        ok = collector.save_xbrl_zip(report, zip_path)
        if not (ok and zip_path.exists() and zip_path.stat().st_size > 0):
            row["downloaded"] = False
            results.append(row)
            print(f"{name}/{year}: zip 미수신")
            continue
        row["downloaded"] = True
        row["zip_kb"] = zip_path.stat().st_size // 1024
        facts = extract_note_facts(zip_path)
        out_dir = zip_path.parent / "notes_xbrl"
        stats = save_note_facts(facts, out_dir)
        cats = note_category_counts(facts)
        row.update(stats)
        row["note_categories"] = cats
        row["note_total"] = sum(cats.values())
        results.append(row)
        print(
            f"{name}/{year}: {row['report_name'][:24]} | zip {row['zip_kb']}KB | "
            f"facts={stats['fact_count']} 개념={stats['distinct_concepts']} "
            f"주석적중={row['note_total']} → {out_dir.name}/note_facts.tsv"
        )

    out = Path("data/backtest/_dg_pipeline_run.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(results)
    found = sum(1 for r in results if r.get("report_found"))
    dl = sum(1 for r in results if r.get("downloaded"))
    notes = sum(1 for r in results if r.get("note_total", 0) > 0)
    print(f"\n[표본 {n}사연도] 사업보고서존재={found} zip다운로드={dl} 비금융주석저장={notes}")
    print(f"결과: {out}")


if __name__ == "__main__":
    main()
