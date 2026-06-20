"""전 축 lump canonical 데이터기반 전수 탐지 — dedup 진짜 소실 유발 canonical 찾기(읽기전용).

한 회사연도·한 canonical에 여러 account_id가 서로 다른 비영 값으로 충돌하고, 그중 어느 값도
나머지의 합(=총계)이 아니면 → distinct 항목 lump(dedup이 하나 소실). 총계 있으면 benign.
축을 추측하지 않고 데이터로 판별(유동/비유동·취득처분·재분류 등 전 축 포함).
재현: PYTHONPATH=. uv run python data/backtest/_p1_lump_detect.py
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from src.normalize.config import load_canonical_accounts
from src.normalize.mapper import OTHER_CANONICAL, AccountMapper

BASE = Path("data/companies")
ROUND = 1_000_000
mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

# 감사 대상: 분식5사+정상2 + 표본(앞쪽 corp 다수) — 충분히 다양
corps = ["00159616", "00409681", "00118345", "00657783", "00413046", "00126380", "00309503"]
allc = sorted(d.name for d in BASE.iterdir() if d.is_dir() and d.name.isdigit())
corps += allc[20:120:3]  # 표본 ~33개(앞20 test 제외 구간)
corps = list(dict.fromkeys(corps))


def has_total(vals: list[int]) -> bool:
    """어느 값이 나머지 합(=총계)이면 True(benign). 2원소면 같을 때만(사실상 없음)."""
    av = [abs(v) for v in vals if v]
    if len(av) < 2:
        return True
    for i, v in enumerate(av):
        if abs(v - sum(av[:i] + av[i + 1 :])) <= 2:  # 100만 반올림 후 2 이내
            return True
    return False


lump = Counter()  # canonical → 충돌(진짜손실) 발생 회사연도 수
example: dict[str, list] = defaultdict(list)
seen_cy = 0
for corp in corps:
    cdir = BASE / corp
    if not cdir.is_dir():
        continue
    for ydir in sorted(p for p in cdir.iterdir() if p.is_dir()):
        # canonical별 충돌 account_id 값 모으기(raw 직접 매핑)
        bycanon: dict[str, dict[str, int]] = defaultdict(dict)
        any_raw = False
        for fs in ("CFS", "OFS"):
            p = ydir / "raw" / f"finstate_all_{fs}.csv"
            if not p.exists() or p.stat().st_size <= 5:
                continue
            any_raw = True
            for r in csv.DictReader(p.open(encoding="utf-8-sig")):
                aid = (r.get("account_id") or "").strip()
                if not aid or aid in ("", "-표준계정코드 미사용-"):
                    continue
                res = mapper.map_row(
                    pd.Series({"account_id": aid, "account_nm": r.get("account_nm", "")})
                )
                if res.canonical == OTHER_CANONICAL:
                    continue
                v = (r.get("thstrm_amount") or "").strip()
                try:
                    iv = round(int(float(v)) / ROUND)
                except (ValueError, TypeError):
                    continue
                key = f"{fs}:{res.canonical}"
                if aid not in bycanon[key] or abs(iv) > abs(bycanon[key][aid]):
                    bycanon[key][aid] = iv
        if not any_raw:
            continue
        seen_cy += 1
        for key, idvals in bycanon.items():
            distinct_vals = [v for v in idvals.values() if v]
            if len(idvals) >= 2 and len(set(distinct_vals)) >= 2 and not has_total(distinct_vals):
                canon = key.split(":", 1)[1]
                lump[canon] += 1
                if len(example[canon]) < 3:
                    example[canon].append(
                        (corp, ydir.name, {k.split("_")[-1][:18]: v for k, v in idvals.items()})
                    )

print(f"검사 회사연도: {seen_cy} (회사 {len(corps)})")
print(f"진짜손실 lump canonical: {len(lump)}\n")
for canon, n in lump.most_common():
    print(f"  [{n:>2}개사연도] {canon}")
    for corp, yr, vals in example[canon]:
        print(f"       {corp}/{yr}: {vals}")
