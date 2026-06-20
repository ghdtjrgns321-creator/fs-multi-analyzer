"""원본(정정 이전) 사업보고서 재무제표 수집 가능성 조사 — 읽기전용.

수집 파이프라인 수정 없음. OpenDartReader를 직접 호출해 다음을 확인한다:
1) list(final=False)가 한 회사의 원본+정정 사업보고서를 모두 나열하는가
2) finstate_xml(rcept_no)로 특정(원본) 보고서 XBRL을 받을 수 있는가
3) 원본 XBRL의 핵심 수치(자산총계·매출·당기순이익)가 정정본과 다른가
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import OpenDartReader

from config.settings import settings

OUT = Path("data/backtest")
dart = OpenDartReader(settings.dart_api_key)

# (이름, corp_code, 분식 회계연도)
TARGETS = [
    ("두산에너빌리티", "00159616", 2017),
    ("셀트리온", "00413046", 2017),
    ("아스트", None, 2018),  # corp_code 미상 → 이름으로 탐색
]


def list_annual_reports(corp_code: str, year: int):
    """해당 회계연도 사업보고서의 모든 신고(원본+정정)를 넓은 창으로 수집."""
    # 회계연도+1 부터 +9 까지: 정정은 수년 뒤에도 올라온다
    start = f"{year + 1}0101"
    end = f"{year + 9}1231"
    df = dart.list(corp=corp_code, start=start, end=end, kind="A", final=False)
    if df is None or df.empty:
        return df
    mask = df["report_nm"].astype(str).str.contains("사업보고서", regex=False)
    return df[mask].copy()


def main():
    summary = {}
    for name, corp_code, year in TARGETS:
        if corp_code is None:
            corp_code = dart.find_corp_code(name)
        print(f"\n=== {name} ({corp_code}) FY{year} ===")
        df = list_annual_reports(corp_code, year)
        if df is None or df.empty:
            print("  사업보고서 신고 없음")
            summary[name] = {"corp_code": corp_code, "year": year, "reports": []}
            continue
        cols = ["rcept_no", "report_nm", "rcept_dt", "flr_nm"]
        cols = [c for c in cols if c in df.columns]
        recs = df[cols].sort_values("rcept_dt").to_dict("records")
        for r in recs:
            print(f"  {r.get('rcept_dt')}  {r.get('rcept_no')}  {r.get('report_nm')}")
        summary[name] = {"corp_code": corp_code, "year": year, "reports": recs}

    (OUT / "_audit_orig_listings.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nsaved -> data/backtest/_audit_orig_listings.json")


if __name__ == "__main__":
    main()
