"""P1 E2E 검증 S1b — 선정 4사 정성자료 재수집(사업보고서·event·report·정정).

raw에 거의 없던 사업보고서 본문/event/report/correction을 DART API로 받아 정성검증 입력 확보.
조회 범위는 선정연도 기준 상대(리터럴 윈도우 아님). 부재는 status로 흡수(예외 아님).

실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_collect.py
"""

from __future__ import annotations

import json
from pathlib import Path

from config.settings import settings
from src.collect.correction import collect_corrections
from src.collect.events import collect_events, collect_reports
from src.collect.opendart import DartCollector
from src.collect.report_doc import collect_report_doc

SAMPLE = Path("data/backtest/_p1e2e_sample.json")
LOG = Path("data/backtest/_p1e2e_collect_log.json")


def main() -> None:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    root = settings.data_dir
    api = DartCollector()
    log: list[dict] = []
    for s in sample:
        corp, year = s["corp"], int(s["year"])
        rd = collect_report_doc(api, corp, year, root)
        ev = collect_events(api, corp, f"{year - 2}-01-01", f"{year}-12-31", data_dir=root)
        rp = collect_reports(api, corp, (year - 1, year), data_dir=root)
        co = collect_corrections(api, corp, f"{year - 3}-01-01", f"{year}-12-31", data_dir=root)
        rec = {
            "corp": corp,
            "year": year,
            "report_doc": rd.get("status"),
            "report_doc_bytes": rd.get("bytes", 0),
            "event_types": len(ev),
            "report_types": len(rp),
            "corrections": len(co),
        }
        log.append(rec)
        print(rec, flush=True)
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
