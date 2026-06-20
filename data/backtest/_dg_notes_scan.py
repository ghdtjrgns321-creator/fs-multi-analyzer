"""D-G: 주석(notes) 수집 현황 전수 스캔 (읽기전용 집계)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path("data/companies")


def main() -> None:
    total_company_years = 0
    companies = set()
    company_years_with_notes = []  # (corp, year, n_html, has_catjson, codes)
    note_code_counter: Counter[str] = Counter()
    catjson_count = 0

    for corp_dir in sorted(ROOT.iterdir()):
        if not corp_dir.is_dir():
            continue
        for year_dir in sorted(corp_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            raw = year_dir / "raw"
            if not raw.is_dir():
                continue
            total_company_years += 1
            companies.add(corp_dir.name)
            notes_dir = raw / "notes"
            if not notes_dir.is_dir():
                continue
            html_files = list(notes_dir.rglob("*.html"))
            has_catjson = (notes_dir / "note_categories.json").exists()
            if has_catjson:
                catjson_count += 1
            codes = sorted({p.stem for p in html_files})
            for c in codes:
                note_code_counter[c] += 1
            company_years_with_notes.append(
                (corp_dir.name, year_dir.name, len(html_files), has_catjson, codes)
            )

    print(f"총 회사 수(raw 보유): {len(companies)}")
    print(f"총 회사연도 수(raw 보유, 분모): {total_company_years}")
    print(f"주석(notes/) 보유 회사연도: {len(company_years_with_notes)}")
    print(f"note_categories.json 보유 회사연도: {catjson_count}")
    print()
    print("=== note code 분포(코드별 보유 회사연도 수) ===")
    for code, n in note_code_counter.most_common():
        print(f"  {code}: {n}")
    print()
    print("=== 주석 보유 회사연도 전수 목록 ===")
    by_corp: Counter[str] = Counter()
    for corp, year, n_html, has_cat, codes in company_years_with_notes:
        by_corp[corp] += 1
        print(f"  {corp}/{year}  html={n_html}  catjson={has_cat}  codes={codes}")
    print()
    print("=== 회사별 주석 보유 연도 수 ===")
    for corp, n in by_corp.most_common():
        print(f"  {corp}: {n}개 연도")

    # JSON 산출
    out = {
        "total_company_years_with_raw": total_company_years,
        "total_companies_with_raw": len(companies),
        "company_years_with_notes": len(company_years_with_notes),
        "catjson_count": catjson_count,
        "note_code_distribution": dict(note_code_counter),
        "detail": [
            {"corp": c, "year": y, "html": h, "catjson": hc, "codes": cd}
            for c, y, h, hc, cd in company_years_with_notes
        ],
        "by_corp": dict(by_corp),
    }
    Path("data/backtest/_dg_notes_scan.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
