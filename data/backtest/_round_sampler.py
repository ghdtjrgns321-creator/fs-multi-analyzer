"""라운드 표본 추출 — 미검증 회사에서 층화 랜덤으로 N사 선택(seed 고정 재현).

층화 축은 업종명이 아니라 **계정 구조 특성**이다 — 정규화 변형(버그)을 일으키는 건 업종
레이블이 아니라 공시 형태(금융 특수계정·blank id·별도전용·연도수·규모)이므로, raw CSV에서
직접 측정해 층을 나눈다. 층:
  S1 금융형(보험·대출채권·예수부채 등 특수계정 보유)   — 일반 제조와 계정 구조가 다름
  S2 별도전용(OFS-only)                                — CFS fallback 경로 검증
  S3 blank account_id 고비중                            — 커스텀 계정 보존(A5) 검증
  S4 다년(6년+)·대형                                    — 시계열·규모 경로
  S5 단년·소형                                          — 최소 데이터 경로

실행: PYTHONPATH=. uv run python data/backtest/_round_sampler.py <round_name> [n=5] [seed=1]
산출: data/backtest/_round_targets.json (배치 러너·게이트가 읽는 라운드 대상)
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMPANIES = PROJECT_ROOT / "data/companies"
KC = PROJECT_ROOT / "data/backtest/known_cases.json"
BACKTEST_DIR = PROJECT_ROOT / "data/backtest"
FIN_TOKENS = ("보험계약", "대출채권", "예수부채", "수신부채", "책임준비금", "재보험", "여신")
BLANK_ID = "-표준계정코드 미사용-"


def audited_corps() -> set[str]:
    """이미 깊은 감사를 거친 회사 제외 — 정답지 positive + 과거 라운드 표본 전부."""
    out: set[str] = set()
    kc = json.load(KC.open(encoding="utf-8"))
    out |= {
        c["corp_code"] for c in kc["cases"] if c.get("label") == "positive" and c.get("runnable")
    }
    for p in BACKTEST_DIR.glob("_round_targets*.json"):
        payload = json.load(p.open(encoding="utf-8"))
        out |= {c["corp_code"] for c in payload.get("cases", [])}
    return out


def company_features(cdir: Path) -> dict | None:
    """최신 raw 연도 CSV에서 층화 특성 측정(DB 불요 — 구버전 DB 상태와 무관)."""
    years = sorted(
        y.name for y in cdir.iterdir() if y.is_dir() and y.name.isdigit() and (y / "raw").exists()
    )
    if not years:
        return None
    latest = cdir / years[-1] / "raw"
    cfs, ofs = latest / "finstate_all_CFS.csv", latest / "finstate_all_OFS.csv"
    # 수집기는 별도전용 회사에도 빈 CFS 파일(헤더만)을 만든다 — 존재가 아니라 데이터 행으로 판정
    rows: list[dict] = []
    if cfs.exists():
        rows = list(csv.DictReader(cfs.open(encoding="utf-8-sig")))
    ofs_only = not rows
    if ofs_only and ofs.exists():
        rows = list(csv.DictReader(ofs.open(encoding="utf-8-sig")))
    if not rows:
        return None
    blank = sum(1 for r in rows if (r.get("account_id") or "").strip() == BLANK_ID)
    fin = any(any(t in (r.get("account_nm") or "") for t in FIN_TOKENS) for r in rows)
    assets = 0
    for r in rows:
        if r.get("sj_div") == "BS" and (r.get("account_nm") or "").strip() == "자산총계":
            try:
                assets = abs(int(float(r.get("thstrm_amount") or 0)))
            except ValueError:
                pass
            break
    return {
        "corp_code": cdir.name,
        "run_years": years,
        "n_years": len(years),
        "ofs_only": ofs_only,
        "blank_ratio": blank / len(rows),
        "fin": fin,
        "assets": assets,
    }


def pick(strata: dict[str, list[dict]], n: int, rng: random.Random) -> list[dict]:
    """층마다 1개씩 비복원 추출. 빈 층은 전체 풀에서 보충."""
    chosen: list[dict] = []
    used: set[str] = set()
    all_pool = [f for pool in strata.values() for f in pool]
    items = list(strata.items())
    # 라운드로빈 — n이 층 수를 넘으면 층을 순환하며 추출(n=10이면 층당 2개)
    for i in range(n):
        name, pool = items[i % len(items)]
        cands = [f for f in pool if f["corp_code"] not in used] or [
            f for f in all_pool if f["corp_code"] not in used
        ]
        c = rng.choice(cands)
        c["stratum"] = name
        used.add(c["corp_code"])
        chosen.append(c)
    return chosen


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "round1"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    rng = random.Random(seed)
    skip = audited_corps()
    feats = []
    for cdir in sorted(COMPANIES.iterdir()):
        if not cdir.is_dir() or cdir.name in skip:
            continue
        f = company_features(cdir)
        if f:
            feats.append(f)
    assets_sorted = sorted(f["assets"] for f in feats if f["assets"])
    q3 = assets_sorted[int(len(assets_sorted) * 0.75)]
    q1 = assets_sorted[int(len(assets_sorted) * 0.25)]
    blank_sorted = sorted(f["blank_ratio"] for f in feats)
    bq3 = blank_sorted[int(len(blank_sorted) * 0.75)]
    strata = {
        "S1_금융형": [f for f in feats if f["fin"]],
        "S2_별도전용": [f for f in feats if f["ofs_only"]],
        "S3_blankid고비중": [f for f in feats if f["blank_ratio"] >= bq3],
        "S4_다년대형": [f for f in feats if f["n_years"] >= 6 and f["assets"] >= q3],
        "S5_단년소형": [f for f in feats if f["n_years"] == 1 and 0 < f["assets"] <= q1],
    }
    chosen = pick(strata, n, rng)
    payload = {
        "name": name,
        "seed": seed,
        "pool": len(feats),
        "strata_sizes": {k: len(v) for k, v in strata.items()},
        "cases": [
            {
                k: c[k]
                for k in (
                    "corp_code",
                    "run_years",
                    "stratum",
                    "n_years",
                    "ofs_only",
                    "blank_ratio",
                    "fin",
                    "assets",
                )
            }
            for c in chosen
        ],
    }
    # 라운드별 파일 분리 — round1은 기존 _round_targets.json(레거시 경로) 유지
    out = (
        BACKTEST_DIR / "_round_targets.json"
        if name == "round1"
        else BACKTEST_DIR / f"_round_targets_{name}.json"
    )
    if out.exists():
        print(f"⛔ {out} 이미 존재 — 같은 라운드 재추출은 기존 파일을 지우고 실행(덮어쓰기 금지)")
        sys.exit(1)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"표본 {len(chosen)}사 → {out} (pool={len(feats)}, seed={seed})")
    for c in chosen:
        print(
            f"  [{c['stratum']:14}] {c['corp_code']} 연도{c['n_years']} OFS전용={c['ofs_only']} "
            f"blank={c['blank_ratio']:.0%} 금융={c['fin']} 자산={c['assets'] / 1e12:,.2f}조"
        )


if __name__ == "__main__":
    main()
