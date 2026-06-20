"""원본 finstate_all CSV 재생성 — 수정된 컨버터로 account_detail을 한글 라벨로 복원(T1).

기존 raw CSV의 rcept_no(=원본 rcept)와 회사신고 라벨(label_map)을 재사용해 원본 XBRL을 다시
변환한다. **finstate_all_{CFS,OFS}.csv만 덮어쓴다** — 정정본 백업(_backup_corrected)·주석·
analysis.duckdb는 건드리지 않는다(재정규화는 renormalize_all이 별도 수행). 금액은 round-trip
검증된 대로 동일하고, account_detail만 member 코드→한글("이익잉여금 [member]")로 바뀐다.

대상은 known_cases.json positive·runnable 전수(하드코딩 금지). 기본 dry-run, --apply로 실제 기록.
재현: PYTHONPATH=. uv run python data/backtest/_regen_original_csv.py [--apply] [corp_code]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from _xbrl_to_finstate_csv import load_label_map, xbrl_to_frames

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KC = PROJECT_ROOT / "data/backtest/known_cases.json"


def targets() -> list[tuple[str, str]]:
    kc = json.load(KC.open(encoding="utf-8"))
    out = []
    for c in kc["cases"]:
        if c.get("label") == "positive" and c.get("runnable"):
            for y in c.get("run_years", []):
                out.append((c["corp_code"], str(y)))
    return out


def _existing_rcept(corp: str, fy: str) -> str | None:
    """현재 raw CSV의 rcept_no(=컨버터가 기록한 원본 rcept). list() 네트워크 질의 회피."""
    for div in ("CFS", "OFS"):
        p = PROJECT_ROOT / f"data/companies/{corp}/{fy}/raw/finstate_all_{div}.csv"
        if not p.exists() or p.stat().st_size <= 5:
            continue
        with p.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            row = next(reader, None)
            if row and row.get("rcept_no"):
                return str(row["rcept_no"]).strip()
    return None


def regen(corp: str, fy: str, apply: bool) -> tuple[str, str]:
    raw_dir = PROJECT_ROOT / f"data/companies/{corp}/{fy}/raw"
    if not raw_dir.exists():
        return ("skip", "raw 없음")
    rcept = _existing_rcept(corp, fy)
    if not rcept:
        return ("skip", "rcept 없음(빈 CSV)")
    label_map = load_label_map(corp, int(fy))
    frames = xbrl_to_frames(rcept, corp, int(fy), label_map)
    if frames is None or all(df.empty for df in frames.values()):
        return ("skip", f"변환실패/빈 (rcept={rcept})")
    # SCE 한글 leaf 회복 검증(샘플)
    sce_sample = ""
    for fs, df in frames.items():
        sce = df[df["sj_div"] == "SCE"]
        if not sce.empty:
            details = [d for d in sce["account_detail"].tolist() if d and d != "-"]
            kor = sum(1 for d in details if "Axis=" not in d)
            sce_sample = f"{fs} SCE {len(sce)}행 한글detail {kor}/{len(details)}"
            break
    if not apply:
        return (
            "dry",
            f"rcept={rcept} CFS={len(frames.get('CFS', []))} OFS={len(frames.get('OFS', []))} {sce_sample}",
        )
    for fs, df in frames.items():
        if not df.empty:
            df.to_csv(raw_dir / f"finstate_all_{fs}.csv", index=False, encoding="utf-8-sig")
    return (
        "done",
        f"rcept={rcept} CFS={len(frames.get('CFS', []))} OFS={len(frames.get('OFS', []))} {sce_sample}",
    )


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    args = [a for a in args if a != "--apply"]
    corp_filter = args[0] if args else None
    mode = "APPLY(CSV 덮어쓰기)" if apply else "DRY-RUN"
    print(f"=== 원본 CSV 재생성(account_detail 한글 복원) {mode} ===")
    counts: dict[str, int] = {}
    for corp, fy in targets():
        if corp_filter and corp != corp_filter:
            continue
        status, msg = regen(corp, fy, apply)
        counts[status] = counts.get(status, 0) + 1
        print(f"  [{status:4}] {corp}/{fy}: {msg}")
    print(f"\n합계: {counts}")
    if not apply:
        print("실제 기록하려면 --apply")


if __name__ == "__main__":
    main()
