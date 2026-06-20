"""본문 전수 재정규화 — 현 파이프라인(428 canonical·통화·이질병합 차단·SCE 2D)을 디스크에 반영.

각 회사연도: normalize_company_year → write_normalized_financials + sce_components_company_year →
write_sce_components. 재무 raw(finstate_all_*.csv)만 있으면 됨(API 0).
재개: normalized_financials에 currency 컬럼 + sce 테이블 둘 다 있으면 skip.

실행: PYTHONPATH=. uv run python -m src.normalize.renormalize_all            (전수)
      PYTHONPATH=. uv run python -m src.normalize.renormalize_all --limit 20 (앞 20개사 테스트)
      PYTHONPATH=. uv run python -m src.normalize.renormalize_all 00126380   (특정 회사)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb

from config.settings import settings
from src.db.normalized import db_path, write_normalized_financials, write_sce_components
from src.normalize.pipeline import normalize_company_year, sce_components_company_year

RESULT_PATH = Path("data/backtest/_p1_renormalize.jsonl")


def raw_years(root: Path, corp: str) -> list[str]:
    cdir = root / corp
    out = []
    for ydir in sorted(cdir.iterdir()) if cdir.is_dir() else []:
        raw = ydir / "raw"
        if (raw / "finstate_all_CFS.csv").exists() or (raw / "finstate_all_OFS.csv").exists():
            out.append(ydir.name)
    return out


def is_fresh(path: Path) -> bool:
    """현 파이프라인 산출(currency 컬럼 + sce 테이블)이면 재정규화 불필요."""

    if not path.exists():
        return False
    try:
        with duckdb.connect(str(path), read_only=True) as con:
            tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
            if "normalized_financials" not in tabs or "sce_equity_components" not in tabs:
                return False
            cols = [c[0] for c in con.execute("DESCRIBE normalized_financials").fetchall()]
            return "currency" in cols
    except Exception:
        return False


def run(
    corps: list[str] | None = None,
    limit: int | None = None,
    log_every: int = 50,
    force: bool = False,
) -> dict:
    root = settings.data_dir
    all_corps = corps or sorted(d.name for d in root.iterdir() if d.is_dir() and d.name.isdigit())
    if limit is not None:
        all_corps = all_corps[:limit]
    counts = {"renorm": 0, "skip": 0, "empty": 0, "error": 0}
    rows_total = 0
    processed = 0
    t0 = time.perf_counter()

    with RESULT_PATH.open("a", encoding="utf-8") as out:
        for corp in all_corps:
            for year in raw_years(root, corp):
                processed += 1
                rec: dict = {"corp": corp, "year": year}
                if not force and is_fresh(db_path(corp, year, root)):
                    counts["skip"] += 1
                    continue
                try:
                    frame = normalize_company_year(corp, year, data_dir=root)
                    if frame.empty:
                        counts["empty"] += 1
                        rec["status"] = "empty"
                        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        continue
                    write_normalized_financials(frame, corp, year, root)
                    sce = sce_components_company_year(corp, year, data_dir=root)
                    write_sce_components(sce, corp, year, root)
                    counts["renorm"] += 1
                    rows_total += len(frame)
                    rec.update(status="ok", rows=len(frame), sce_rows=len(sce))
                except Exception as exc:  # noqa: BLE001 — 한 건 실패가 전체를 막지 않게
                    counts["error"] += 1
                    rec.update(status="error", error=str(exc)[:200])
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if processed % log_every == 0:
                    el = (time.perf_counter() - t0) / 60
                    print(
                        f"[{processed}] renorm={counts['renorm']} skip={counts['skip']} "
                        f"empty={counts['empty']} err={counts['error']} | {el:.1f}분",
                        flush=True,
                    )
            out.flush()

    el = (time.perf_counter() - t0) / 60
    print(
        f"\n[완료] 처리 {processed} | renorm={counts['renorm']} skip={counts['skip']} "
        f"empty={counts['empty']} error={counts['error']} | 행 {rows_total:,} | {el:.1f}분"
    )
    return counts


def main() -> None:
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    limit = None
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        args = args[:i] + args[i + 2 :]
    run(args or None, limit=limit, force=force)


if __name__ == "__main__":
    main()
