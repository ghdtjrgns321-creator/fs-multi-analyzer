"""40-F 자가 적대 감사: Fix A flip(표본) + label_priority 역케이스 + 피팅 + 역검증.

경합 회피 위해 단일 uv 호출. Fix A flip은 corpus를 stride 표본(전수 너무 느림).
실행: PYTHONPATH=. uv run python data/backtest/_p1_fix_audit.py
"""

from __future__ import annotations

import collections
import csv
import glob

import pandas as pd

from config.settings import settings
from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import ID_LABEL_CONFLICT, OTHER_CANONICAL, AccountMapper
from src.normalize.pipeline import normalize_company_year

accs = load_canonical_accounts(settings.config_dir / "canonical_accounts.yaml")
mapper = AccountMapper(accs)
by_id = {aid: a for a in accs for aid in a.account_ids}
by_alias = {normalize_label(al): a for a in accs for al in a.aliases}

# ── A. Fix A flip 표본 (stride로 corpus 전반 분산) ────────────────────────────
dirs = set()
for f in glob.glob("data/companies/*/*/raw/finstate_all_*.csv"):
    p = f.replace(chr(92), "/").split("/")
    dirs.add((p[2], p[3]))
dirs = sorted(dirs)
sample = dirs[::9]  # 약 1/9 표본, corpus 전반 분산
flips = []
n = 0
for corp, yr in sample:
    n += 1
    try:
        df = normalize_company_year(corp, int(yr))
    except Exception:
        continue
    if not len(df):
        continue
    other = df[df["canonical"] == OTHER_CANONICAL]
    for _, orow in other.iterrows():
        mr = mapper.map_row(
            pd.Series({"account_id": orow["account_id"], "account_nm": orow["label"]})
        )
        if mr.mapping_status != ID_LABEL_CONFLICT:
            continue
        rep = df[(df["canonical"] == mr.canonical) & (df["fs_div"] == orow["fs_div"])]
        if not len(rep):
            continue
        try:
            ra = abs(float(rep["amount"].iloc[0]))
            da = abs(float(orow["amount"]))
        except Exception:
            continue
        if da > ra * 1.05 and da > 1e9:
            flips.append((corp, yr, mr.canonical, ra, da, str(orow["label"])[:22]))
print(f"## A. Fix A flip 표본 — {n} 회사연도, 의심 flip {len(flips)}건")
print("  canonical별:", dict(collections.Counter(f[2] for f in flips).most_common(15)))
for f in flips[:15]:
    print(
        f"  {f[0]}/{f[1]} [{f[2]}] 대표 {f[3] / 1e9:.2f} < 강등 {f[4] / 1e9:.2f}십억 (라벨={f[5]})"
    )

# ── B. label_priority 4 id 충돌 라벨 전수 (역케이스 탐지) ──────────────────────
PRIORITY = [
    "ifrs-full_IssuedCapital",
    "ifrs-full_ProceedsFromIssuingShares",
    "dart_PurchaseOfFinancialAssetsHeldToMaturity",
    "ifrs-full_PurchaseOfInvestmentProperty",
]
conf = {t: collections.Counter() for t in PRIORITY}
for f in glob.glob("data/companies/*/*/raw/*.csv"):
    try:
        for row in csv.reader(open(f, encoding="utf-8")):
            if len(row) < 8:
                continue
            aid = row[6].strip()
            if aid not in PRIORITY:
                continue
            nl = normalize_label(row[7].strip())
            ida = by_id.get(aid)
            la = by_alias.get(nl)
            if ida is not None and la is not None and la.name != ida.name:
                conf[aid][f"{row[7].strip()} → {la.name}"] += 1
    except Exception:
        continue
print("\n## B. label_priority 충돌 라벨 전수 (라벨→채택canonical) — 역케이스 점검")
for t in PRIORITY:
    print(f"  [{t} = {by_id[t].name}]")
    for lab, c in conf[t].most_common(20):
        print(f"      {c:>4}  {lab}")

# ── C. 피팅: 00545716 quirk 단일사 재확인 ────────────────────────────────────
print("\n## C. 00545716 영업수익→영업이익 오태깅 회사 수(quirk 단일사 맞나)")
oc = collections.defaultdict(set)
for f in glob.glob("data/companies/*/*/raw/*.csv"):
    try:
        for row in csv.reader(open(f, encoding="utf-8")):
            if len(row) < 8:
                continue
            if row[6].strip() == "dart_OperatingIncomeLoss" and row[7].strip() in {
                "영업수익",
                "매출",
                "매출액",
                "수익",
            }:
                p = f.replace(chr(92), "/").split("/")
                oc[p[2]].add(p[3])
    except Exception:
        continue
print(f"  영업수익계열을 영업이익id로 태깅: {len(oc)}개사 — {dict(list(oc.items())[:6])}")

# ── D. 역검증: 신규 alias가 다른 의미 행 흡수? ──────────────────────────────
print("\n## D. 신규 alias 역검증")
for lab in ["금융업자산", "금융업부채", "발행사채의 증가"]:
    ids = collections.Counter()
    for f in glob.glob("data/companies/*/*/raw/*.csv"):
        try:
            for row in csv.reader(open(f, encoding="utf-8")):
                if len(row) < 8:
                    continue
                if row[7].strip() == lab:
                    ids[row[6].strip()] += 1
        except Exception:
            continue
    print(f"  '{lab}' 라벨의 account_id 분포: {dict(ids.most_common(6))}")
