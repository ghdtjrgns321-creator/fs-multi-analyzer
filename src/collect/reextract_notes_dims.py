"""저장된 XBRL zip을 차원(dimensions) 보존해 재추출 — note_facts.tsv 7컬럼화.

재다운로드·API 호출 없음(로컬 zip만 재처리). 현 note_facts.tsv가 6컬럼(차원 없음)이면
재추출해 덮고, 이미 dimensions 컬럼이 있으면 건너뛴다(재개 안전).

실행: PYTHONPATH=. uv run python -m src.collect.reextract_notes_dims         (전수)
      PYTHONPATH=. uv run python -m src.collect.reextract_notes_dims 00100939 (특정 회사)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from config.settings import settings
from src.collect.notes_xbrl import extract_note_facts, save_note_facts

RESULT_PATH = Path("data/backtest/_dg_reextract.jsonl")


def has_dimensions(tsv: Path) -> bool:
    """note_facts.tsv 헤더에 dimensions 컬럼이 있으면 재추출 완료된 것."""

    if not tsv.exists():
        return False
    with tsv.open(encoding="utf-8") as fh:
        header = fh.readline()
    return "dimensions" in header


def find_zips(root: Path, corps: list[str] | None) -> list[Path]:
    corp_dirs = (
        [root / c for c in corps]
        if corps
        else sorted(d for d in root.iterdir() if d.is_dir() and d.name.isdigit())
    )
    zips: list[Path] = []
    for cdir in corp_dirs:
        if not cdir.is_dir():
            continue
        for ydir in sorted(cdir.iterdir()):
            zp = ydir / "raw" / "financial_statement_xbrl.zip"
            if zp.exists() and zp.stat().st_size > 0:
                zips.append(zp)
    return zips


def run(corps: list[str] | None = None, log_every: int = 50) -> dict[str, int]:
    root = settings.data_dir
    zips = find_zips(root, corps)
    counts = {"reextracted": 0, "skip": 0, "empty": 0, "error": 0}
    t0 = time.perf_counter()

    with RESULT_PATH.open("a", encoding="utf-8") as out:
        for idx, zip_path in enumerate(zips):
            notes_dir = zip_path.parent / "notes_xbrl"
            tsv = notes_dir / "note_facts.tsv"
            corp, year = zip_path.parts[-4], zip_path.parts[-3]
            rec: dict = {"corp": corp, "year": year}
            if has_dimensions(tsv):
                counts["skip"] += 1
                continue
            try:
                facts = extract_note_facts(zip_path)
                if not facts:
                    counts["empty"] += 1
                    rec["status"] = "empty"
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    continue
                stats = save_note_facts(facts, notes_dir)
                with_dim = sum(1 for f in facts if f.dimensions)
                counts["reextracted"] += 1
                rec.update(status="ok", facts=stats["fact_count"], with_dim=with_dim)
            except Exception as exc:  # noqa: BLE001 — 한 zip 실패가 전체를 막지 않게
                counts["error"] += 1
                rec.update(status="error", error=str(exc)[:200])
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()

            if (idx + 1) % log_every == 0:
                el = (time.perf_counter() - t0) / 60
                print(
                    f"[{idx + 1}/{len(zips)}] reextract={counts['reextracted']} "
                    f"skip={counts['skip']} empty={counts['empty']} "
                    f"err={counts['error']} | {el:.1f}분",
                    flush=True,
                )

    el = (time.perf_counter() - t0) / 60
    print(
        f"\n[완료] zip {len(zips)} | reextract={counts['reextracted']} skip={counts['skip']} "
        f"empty={counts['empty']} error={counts['error']} | {el:.1f}분 | 로그 {RESULT_PATH}"
    )
    return counts


def main() -> None:
    run(sys.argv[1:] or None)


if __name__ == "__main__":
    main()
