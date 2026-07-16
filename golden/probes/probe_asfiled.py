"""as-filed 원본 서빙 재현 실측(전후꼬임 해소 근거, DESIGN §1.1).

DART가 정정 후에도 원본 접수분(본문·XBRL)을 서빙하는지 실제 API로 확인한다.
검사2 벤치마크 등록 전 "원본을 가져올 수 있는가"의 재현 스크립트.

실행: PYTHONPATH=. uv run python golden/probes/probe_asfiled.py <corp> <year> <corrected_rcept>
예:   PYTHONPATH=. uv run python golden/probes/probe_asfiled.py 00117212 2020 20240418000399
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from src.collect.opendart import AnnualReport, DartCollector

SCRATCH = Path(__file__).parent


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:12]


def probe(corp: str, year: int, corrected_rcept: str) -> None:
    collector = DartCollector()
    submitted_year = year + 1

    # 1. 원본 접수번호 식별 — 정정 이력 포함 목록(final=False)에서 "정정" 미포함 행.
    filings = collector.filings(corp, f"{submitted_year}-01-01", f"{submitted_year}-12-31")
    annual = filings[filings["report_nm"].astype(str).str.contains("사업보고서", regex=False)]
    print("== 제출 사업보고서 목록 ==")
    print(annual[["rcept_no", "report_nm", "rcept_dt"]].to_string(index=False))

    original = annual[~annual["report_nm"].astype(str).str.contains("정정", regex=False)]
    if original.empty:
        raise SystemExit("원본(무정정) 행을 찾지 못함")
    original_rcept = str(original.iloc[0]["rcept_no"])
    print(f"\n원본 rcept_no: {original_rcept}")

    # 2. 원본 본문 fetch.
    original_doc = collector.document(original_rcept)
    print(
        f"원본 document: len={len(original_doc):,}  "
        f"재무제표 포함={'재무제표' in original_doc}  주석 포함={'주석' in original_doc}"
    )

    # 3. 원본 XBRL fetch.
    xbrl_path = SCRATCH / f"xbrl_orig_{original_rcept}.zip"
    report = AnnualReport(
        corp_code=corp, business_year=year, rcept_no=original_rcept, report_name="원본"
    )
    ok = collector.save_xbrl_zip(report, xbrl_path)
    size = xbrl_path.stat().st_size if xbrl_path.exists() else 0
    print(f"원본 XBRL zip: 성공={ok}  size={size:,} bytes")

    # 4. 정정본과 대조(별개 버전 서빙 확인).
    corrected_doc = collector.document(corrected_rcept)
    print(f"\n정정본 document: len={len(corrected_doc):,}")
    print(
        f"원본 hash={_short_hash(original_doc)}  정정본 hash={_short_hash(corrected_doc)}  "
        f"동일={_short_hash(original_doc) == _short_hash(corrected_doc)}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: probe_asfiled.py <corp> <year> <corrected_rcept>")
    probe(sys.argv[1], int(sys.argv[2]), sys.argv[3])
