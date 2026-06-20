"""P1 E2E 검증 S4 정성 — S7 청크선별 4사 실행(서술형 감사관심사항 → material 전달 검증).

사업보고서 본문 → extract_parts → select_review_chunks(gpt-5.4) → 검증용 별도 quirks에 persist.
원본 company_quirks.yaml은 건드리지 않는다(한글 인코딩 가드). 산출 청크를 통독해 소송·특수관계·
우발 등이 잡혔는지 대조.

실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_s7.py
"""

from __future__ import annotations

import json
from pathlib import Path

from config.settings import settings
from src.notes.report_parts import extract_parts
from src.report.review_chunks import persist_review_chunks, select_review_chunks

SAMPLE = Path("data/backtest/_p1e2e_sample.json")
TEST_QUIRKS = Path("data/backtest/_p1e2e_quirks_test.yaml")  # 원본 보호용 별도 경로
LOG = Path("data/backtest/_p1e2e_s7_log.json")


def main() -> None:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    root = settings.data_dir
    log: list[dict] = []
    for s in sample:
        corp, year = s["corp"], str(s["year"])
        xml_path = root / corp / year / "raw" / "report_doc" / "business_report.xml"
        if not xml_path.exists():
            rec = {"corp": corp, "year": year, "status": "no_report_doc"}
            log.append(rec)
            print(rec, flush=True)
            continue
        parts = extract_parts(xml_path.read_text(encoding="utf-8"))
        res = select_review_chunks(parts, corp, year)
        sel = res.get("selection")
        rec = {
            "corp": corp,
            "year": year,
            "status": res["status"],
            "parts": len(parts),
            "chunks": len(sel.chunks) if sel else 0,
            "usage": res.get("usage"),
        }
        if res["status"] == "ok" and sel:
            persist_review_chunks(corp, year, sel, path=TEST_QUIRKS)
        log.append(rec)
        print(rec, flush=True)
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
