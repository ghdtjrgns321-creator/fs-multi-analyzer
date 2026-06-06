"""백테스트 정답지 빌더.

known_cases.json(내가 검증한 실명 분식사건) → corp_code 보강 + DART 가용성 확인 → labels.csv.
계산/판단은 사람(Claude)이 끝냈고, 이 스크립트는 보강·검증·표 출력만 한다.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import OpenDartReader

from config.settings import settings

BASE = Path("data/backtest")
CASES_JSON = BASE / "known_cases.json"
LABELS_CSV = BASE / "labels.csv"

COLUMNS = [
    "company",
    "corp_code",
    "stock_code",
    "market",
    "label",
    "runnable",
    "dart_ok",
    "fraud_year_start",
    "fraud_year_end",
    "run_years",
    "fraud_type",
    "fs_detectable",
    "accounts",
    "confirmed",
    "confidence",
    "sources",
    "notes",
]


def resolve_corp_code(dart: OpenDartReader, stock_code: str | None) -> str | None:
    """상장 종목코드로 corp_code를 정확 조회(동명이의 회피)."""
    if not stock_code:
        return None
    df = dart.corp_codes
    hit = df[df["stock_code"].astype(str).str.strip() == str(stock_code)]
    return str(hit.iloc[0]["corp_code"]) if not hit.empty else None


def check_dart(dart: OpenDartReader, corp_code: str, run_years: list[int]) -> bool:
    """run_years 중 하나라도 재무제표가 받아지면 실행 가능으로 본다."""
    for year in run_years:
        for fs_div in ("CFS", "OFS"):
            try:
                df = dart.finstate_all(corp_code, year, reprt_code="11011", fs_div=fs_div)
            except Exception:
                continue
            if df is not None and len(df) > 0:
                return True
    return False


def build(input_path: Path = CASES_JSON, output_path: Path = LABELS_CSV) -> None:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    dart = OpenDartReader(settings.dart_api_key)

    rows: list[dict[str, object]] = []
    for case in payload["cases"]:
        corp_code = case.get("corp_code") or resolve_corp_code(dart, case.get("stock_code"))
        run_years = case.get("run_years") or []
        dart_ok = (
            bool(case.get("runnable"))
            and corp_code is not None
            and check_dart(dart, corp_code, run_years)
        )
        rows.append(
            {
                "company": case["company"],
                "corp_code": corp_code or "",
                "stock_code": case.get("stock_code") or "",
                "market": case.get("market") or "",
                "label": case["label"],
                "runnable": case.get("runnable", False),
                "dart_ok": dart_ok,
                "fraud_year_start": case.get("fraud_year_start") or "",
                "fraud_year_end": case.get("fraud_year_end") or "",
                "run_years": ";".join(str(y) for y in run_years),
                "fraud_type": case.get("fraud_type") or "",
                "fs_detectable": case.get("fs_detectable", False),
                "accounts": ";".join(case.get("accounts") or []),
                "confirmed": case.get("confirmed") or "",
                "confidence": case.get("confidence") or "",
                "sources": " | ".join(case.get("sources") or []),
                "notes": case.get("notes") or "",
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    runnable = [r for r in rows if r["dart_ok"]]
    print(f"총 {len(rows)}건 → {output_path}")
    print(f"실행가능(dart_ok) {len(runnable)}건:")
    for r in runnable:
        print(f"  [{r['label']}] {r['company']} ({r['corp_code']}) run_years={r['run_years']}")


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic backtest labels.")
    parser.add_argument("--input", type=Path, default=CASES_JSON)
    parser.add_argument("--output", type=Path, default=LABELS_CSV)
    return parser.parse_args()


if __name__ == "__main__":
    args = _args()
    build(args.input, args.output)
