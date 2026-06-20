"""흡수 concept의 복수값이 '왜' 다른지 본문과 직접 대조(§9: 단일케이스 단정 금지).

가설 검정: 같은 기간 2값 = {CFS, OFS}(연결·별도)인가? 아니면 본문에 없는 차원인가?
방법: 주석 흡수값을 그 회사의 normalized_financials(본문, fs_div별)와 매칭. 여러 회사·concept.
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.normalize.notes_classify import classify_concept, load_note_taxonomy

BASE = Path("data/companies")
tax = load_note_taxonomy()

# 본문 canonical 이름 ← 흡수 concept stem 역매핑(어떤 본문계정인지)
from src.normalize.config import load_canonical_accounts

PREFIXES = ("ifrs-full_", "ifrs_", "dart_")


def stem(s: str) -> str:
    for p in PREFIXES:
        if s.startswith(p):
            return s[len(p) :].lower()
    return s.lower()


stem_to_canon = {}
for a in load_canonical_accounts(Path("config/canonical_accounts.yaml")):
    for aid in a.account_ids:
        stem_to_canon.setdefault(stem(aid), a.name)


def note_facts(t: Path):
    rows = list(csv.reader(t.open(encoding="utf-8"), delimiter="\t"))
    return rows[0], rows[1:]


def load_norm(corp: str):
    """본문 normalized_financials: (canonical, year) → {fs_div: amount,...} (당기·전기·전전기)."""
    import duckdb

    out = {}
    cdir = BASE / corp
    if not cdir.exists():
        return out
    for yr in cdir.iterdir():
        db = yr / "analysis.duckdb"
        if not db.exists():
            continue
        try:
            con = duckdb.connect(str(db), read_only=True)
            df = con.execute(
                "SELECT canonical, fs_div, amount, prior_amount, prior2_amount FROM normalized_financials"
            ).fetchdf()
            con.close()
        except Exception:
            continue
        for _, r in df.iterrows():
            out.setdefault((r["canonical"], yr.name), {})[r["fs_div"]] = (
                r["amount"],
                r["prior_amount"],
                r["prior2_amount"],
            )
    return out


# 흡수 facts 풍부한 회사 몇 개 자동 선택
targets = []
for c in sorted(BASE.iterdir()):
    if not c.is_dir():
        continue
    for y in sorted(c.iterdir()):
        t = y / "raw" / "notes_xbrl" / "note_facts.tsv"
        if t.exists():
            targets.append((c.name, y.name, t))
            break
    if len(targets) >= 3:
        break

CHECK = ["Assets", "Liabilities", "Equity", "Revenue"]
for corp, year, t in targets:
    _, rows = note_facts(t)
    norm = load_norm(corp)
    print(f"\n===== {corp} (보고연도 {year}) =====")
    for concept in CHECK:
        facts = [r for r in rows if r and r[0] == concept]
        if not facts:
            continue
        canon = stem_to_canon.get(stem(concept))
        # 기간별 값 모음
        byp = {}
        for r in facts:
            if len(r) >= 6:
                byp.setdefault(r[3], []).append(r[5])
        print(f"  [{concept}→본문 '{canon}'] 기간별 주석값:")
        for per, vals in sorted(byp.items()):
            uniq = sorted(set(vals), key=lambda x: -abs(int(x)) if x.lstrip("-").isdigit() else 0)
            # 본문 매칭 후보(해당 canonical 모든 연도·fs_div 금액)
            stmt_vals = set()
            if canon:
                for (cn, yy), fsmap in norm.items():
                    if cn == canon:
                        for fs, amts in fsmap.items():
                            for a in amts:
                                if a is not None:
                                    stmt_vals.add(int(round(float(a))))
            tagged = []
            for v in uniq:
                iv = int(v) if v.lstrip("-").isdigit() else None
                mark = "✓본문일치" if iv in stmt_vals else "✗본문없음"
                tagged.append(f"{v}({mark})")
            print(f"     {per}: {tagged}")
