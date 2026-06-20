"""전수 수집 타이밍/용량 실측: 새 표본 10 회사연도를 수집하며 단계별 시간·용량을 측정,
전수(4,773)로 외삽한다.

단계: 보고서탐색(list) · zip 다운로드 · Arelle 추출+저장. 각 시간과 zip/tsv 바이트 기록.
재현: PYTHONPATH=. uv run python data/backtest/_dg_timing.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from config.settings import settings
from src.collect.notes_xbrl import extract_note_facts, find_annual_report, save_note_facts
from src.collect.opendart import DartCollector

# 등간격 추출(미수집·규모 다양·보유연도 2+·안정연도 ≤2024). corp_code 기준.
SAMPLES = [
    ("00101628", 2024),
    ("00123143", 2024),
    ("00143314", 2024),
    ("00163673", 2024),
    ("00249034", 2024),
    ("00363592", 2024),
    ("00537221", 2024),
    ("00808022", 2024),
    ("01141942", 2023),
    ("01786958", 2024),
]
TOTAL_UNIVERSE = 4773  # MERGE_AUDIT.md:10 분석 대상 회사연도


def main() -> None:
    if not settings.dart_api_key:
        print("DART_API_KEY 미설정")
        return
    collector = DartCollector()
    root = settings.data_dir
    rows = []
    for corp, year in SAMPLES:
        r: dict = {"corp": corp, "year": year}
        t0 = time.perf_counter()
        report = find_annual_report(collector, corp, year)
        r["t_find"] = round(time.perf_counter() - t0, 2)
        if report is None:
            r["ok"] = False
            r["reason"] = "no_report"
            rows.append(r)
            print(f"{corp}/{year}: 사업보고서 없음 (find {r['t_find']}s)")
            continue
        zip_path = root / corp / str(year) / "raw" / "financial_statement_xbrl.zip"
        t1 = time.perf_counter()
        ok = collector.save_xbrl_zip(report, zip_path)
        r["t_download"] = round(time.perf_counter() - t1, 2)
        if not (ok and zip_path.exists() and zip_path.stat().st_size > 0):
            r["ok"] = False
            r["reason"] = "no_zip"
            rows.append(r)
            print(f"{corp}/{year}: zip 미수신")
            continue
        r["zip_bytes"] = zip_path.stat().st_size
        t2 = time.perf_counter()
        facts = extract_note_facts(zip_path)
        out_dir = zip_path.parent / "notes_xbrl"
        stats = save_note_facts(facts, out_dir)
        r["t_extract"] = round(time.perf_counter() - t2, 2)
        r["facts"] = stats["fact_count"]
        r["tsv_bytes"] = (out_dir / "note_facts.tsv").stat().st_size
        r["ok"] = True
        r["t_total"] = round(r["t_find"] + r["t_download"] + r["t_extract"], 2)
        rows.append(r)
        print(
            f"{corp}/{year}: zip {r['zip_bytes'] // 1024}KB facts={r['facts']} | "
            f"find {r['t_find']}s + dl {r['t_download']}s + extract {r['t_extract']}s "
            f"= {r['t_total']}s"
        )

    ok_rows = [r for r in rows if r.get("ok")]
    out = Path("data/backtest/_dg_timing.json")
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    no_report = sum(1 for r in rows if r.get("reason") == "no_report")
    no_zip = sum(1 for r in rows if r.get("reason") == "no_zip")
    print(
        f"\n[표본 {len(rows)}] 성공 {len(ok_rows)}/{len(rows)} "
        f"| 사업보고서없음 {no_report} · XBRL없음 {no_zip}"
    )
    if not ok_rows:
        print("성공 0 — 추정 불가")
        return
    n = len(ok_rows)
    avg_total = sum(r["t_total"] for r in ok_rows) / n
    avg_dl = sum(r["t_download"] for r in ok_rows) / n
    avg_ex = sum(r["t_extract"] for r in ok_rows) / n
    avg_find = sum(r["t_find"] for r in ok_rows) / n
    avg_zip = sum(r["zip_bytes"] for r in ok_rows) / n
    avg_tsv = sum(r["tsv_bytes"] for r in ok_rows) / n
    print(
        f"평균/회사연도: find {avg_find:.2f}s · dl {avg_dl:.2f}s · extract {avg_ex:.2f}s "
        f"· 합 {avg_total:.2f}s | zip {avg_zip / 1024:.0f}KB · tsv {avg_tsv / 1024:.0f}KB"
    )
    # 전수 외삽 (단일 스레드 직렬)
    tot_s = avg_total * TOTAL_UNIVERSE
    tot_zip = avg_zip * TOTAL_UNIVERSE
    tot_tsv = avg_tsv * TOTAL_UNIVERSE
    print(
        f"\n[전수 {TOTAL_UNIVERSE} 외삽·단일스레드 직렬]"
        f"\n  시간 ≈ {tot_s / 3600:.1f}시간 ({tot_s / 60:.0f}분)"
        f"\n  용량 ≈ zip {tot_zip / 1e9:.2f}GB + tsv {tot_tsv / 1e9:.2f}GB "
        f"= {(tot_zip + tot_tsv) / 1e9:.2f}GB"
    )
    # 추출만 병렬(다운로드는 직렬 가정), 추출 4코어 가정
    par_s = (avg_find + avg_dl) * TOTAL_UNIVERSE + (avg_ex * TOTAL_UNIVERSE) / 4
    print(f"  시간(추출 4병렬) ≈ {par_s / 3600:.1f}시간")
    print(f"결과: {out}")


if __name__ == "__main__":
    main()
