"""E2E 충실도 감사 — 6사 수집 드라이버.

각 회사: collect_company_years(include_notes/corrections/events=True) → 진행 로그.
수집만 수행. 정규화는 별도(renormalize_all --force).

실행: PYTHONPATH=. uv run python -m data.backtest._e2e_collect
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

from src.collect.spike import collect_company_years

LOG = Path("data/backtest/_e2e_collect.jsonl")

# 차원별 1사. corrections/events는 corp 단위(연도 무관). FS연도는 정규화/주석/원문 대상.
TARGETS = [
    ("대형다각화", "00126380", (2024, 2023)),  # 삼성전자
    ("금융지주", "00688996", (2024, 2023)),  # KB금융
    ("자본거래多", "00258801", (2024, 2023)),  # 카카오
    ("정정본", "00117212", (2024, 2023)),  # 두산
    ("구포맷", "00356361", (2017, 2016)),  # LG화학
    ("소형단순", "00160375", (2024, 2023)),  # 진양폴리우레탄
]


def _log(rec: dict) -> None:
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    LOG.write_text("", encoding="utf-8")
    for dim, corp, years in TARGETS:
        t0 = time.time()
        rec: dict = {"dim": dim, "corp": corp, "years": list(years)}
        try:
            summary = collect_company_years(
                corp_code=corp,
                years=years,
                include_xbrl=True,
                include_notes=True,
                include_corrections=True,
                include_events=True,
            )
            rec["status"] = summary.get("status")
            rec["corrections"] = summary.get("corrections")
            rec["events"] = summary.get("events")
        except Exception:
            rec["status"] = "error"
            rec["error"] = traceback.format_exc()[-1500:]
        rec["secs"] = round(time.time() - t0, 1)
        _log(rec)
        print(
            f"[{dim}] {corp} {rec.get('status')} {rec['secs']}s "
            f"corr={rec.get('corrections')} ev={rec.get('events')}",
            flush=True,
        )
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
