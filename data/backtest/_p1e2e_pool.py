"""힌트 train 후보 풀 — 전 회사연도 raw에서 무표준코드(placeholder account_id) 계정 수 측정.

무표준코드 계정이 많은 회사일수록 alias 제안 대상(=오답 수집원)이 많다. 정규화 DB stale 무관하게
raw CSV에서 직접 센다. sj_div=SCE 제외(전용 2D 담당), 금액 0/결측 제외.

실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_pool.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path("data/companies")
OUT = Path("data/backtest/_p1e2e_pool.jsonl")
PROFILE = Path("data/backtest/_p1e2e_profile.jsonl")
PLACEHOLDER = {"-표준계정코드 미사용-", "", "nan", "none"}


def count_placeholder(path: Path) -> int:
    n = 0
    try:
        with path.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if (r.get("sj_div") or "").strip() == "SCE":
                    continue
                aid = (r.get("account_id") or "").strip()
                if aid not in PLACEHOLDER:
                    continue
                if not (r.get("account_nm") or "").strip():
                    continue
                try:
                    if abs(float(r.get("thstrm_amount") or 0)) <= 0:
                        continue
                except ValueError:
                    continue
                n += 1
    except Exception:
        return 0
    return n


def main() -> None:
    # profile에서 (corp, year, asset, fin, note) 메타 재사용
    meta = {}
    for line in PROFILE.read_text(encoding="utf-8").splitlines():
        o = json.loads(line)
        meta[(o["corp"], o["year"])] = o

    out: list[dict] = []
    for cdir in sorted(ROOT.iterdir()):
        if not cdir.is_dir() or not cdir.name.isdigit():
            continue
        corp = cdir.name
        for ydir in sorted(cdir.iterdir()):
            if not ydir.is_dir():
                continue
            raw = ydir / "raw"
            total = 0
            for fs in ("CFS", "OFS"):
                p = raw / f"finstate_all_{fs}.csv"
                if p.exists():
                    total += count_placeholder(p)
            if total == 0:
                continue
            m = meta.get((corp, ydir.name), {})
            out.append(
                {
                    "corp": corp,
                    "year": ydir.name,
                    "placeholder": total,
                    "asset": m.get("asset"),
                    "fin": m.get("fin"),
                    "note": m.get("note"),
                }
            )

    out.sort(key=lambda o: o["placeholder"], reverse=True)
    OUT.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out), encoding="utf-8")

    n = len(out)
    print(f"무표준코드>0 회사연도: {n}")
    for thr in (5, 10, 20, 40):
        print(f"  placeholder ≥ {thr}: {sum(1 for o in out if o['placeholder'] >= thr)}개")
    print("--- 상위 15 ---")
    for o in out[:15]:
        tag = "금융" if o.get("fin") else "비금융"
        note = "주석O" if o.get("note") else "주석X"
        print(f"  {o['corp']}/{o['year']} ph={o['placeholder']} {tag} {note} 자산={o.get('asset')}")


if __name__ == "__main__":
    main()
