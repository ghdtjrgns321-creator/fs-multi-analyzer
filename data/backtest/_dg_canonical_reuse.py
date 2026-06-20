"""주석 concept에 본문 canonical을 stem 매칭 재사용 → 흡수율·잔여 detail 측정(읽기전용).

Option 2 설계 근거. note concept(namespace 없는 local name)을 canonical account_id의 stem
(prefix 제거·소문자)과 매칭. 매칭=본문중복(흡수), 미매칭=주석 고유 detail(분류 대상).
메타데이터 노이즈는 별도 식별.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.normalize.config import load_canonical_accounts

BASE = Path("data/companies")
SAMPLE = 400
PREFIXES = ("ifrs-full_", "ifrs_", "dart_")


def stem(s: str) -> str:
    for p in PREFIXES:
        if s.startswith(p):
            s = s[len(p) :]
            break
    return s.lower()


# 본문 canonical의 stem 집합 + stem→canonical 이름
acc = load_canonical_accounts(Path("config/canonical_accounts.yaml"))
canon_stem: dict[str, str] = {}
for a in acc:
    for aid in getattr(a, "account_ids", []) or []:
        canon_stem.setdefault(stem(aid), a.name)

# 메타데이터/표지 노이즈 패턴(분석가치 0)
META_HINT = (
    "auditor",
    "audit",
    "identif",
    "indentif",
    "opinion",
    "reportdate",
    "author",
    "contact",
    "entity",
    "document",
    "exchange",
    "homepage",
    "address",
    "currency",
    "industry",
    "unitinfo",
    "amendment",
    "title",
    "centralindexkey",
    "fiscalmonth",
    "restatement",
    "numberof",
    "statementof",
    "personnel",
    "registrant",
)


def is_meta(concept: str) -> bool:
    c = concept.lower()
    return any(h in c for h in META_HINT)


files = []
for corp in sorted(BASE.iterdir()):
    if corp.is_dir():
        for yr in sorted(corp.iterdir()):
            t = yr / "raw" / "notes_xbrl" / "note_facts.tsv"
            if t.exists():
                files.append(t)
step = max(1, len(files) // SAMPLE)
sample = files[::step][:SAMPLE]
print(f"수집 {len(files)}개 중 표본 {len(sample)}개\n")

absorbed_rows = meta_rows = detail_rows = 0
absorbed_c: set[str] = set()
meta_c: set[str] = set()
detail_c: Counter = Counter()  # 미매칭 detail concept -> 행수
detail_label: dict[str, str] = {}
for t in sample:
    try:
        lines = t.read_text(encoding="utf-8").splitlines()
    except Exception:
        continue
    for ln in lines[1:]:
        p = ln.split("\t")
        if len(p) < 6:
            continue
        concept, label_ko = p[0], p[1]
        if is_meta(concept):
            meta_rows += 1
            meta_c.add(concept)
        elif stem(concept) in canon_stem:
            absorbed_rows += 1
            absorbed_c.add(concept)
        else:
            detail_rows += 1
            detail_c[concept] += 1
            detail_label.setdefault(concept, label_ko)

total = absorbed_rows + meta_rows + detail_rows
print(f"총 fact 행(표본): {total}")
print(
    f"  본문 canonical 흡수(중복): {absorbed_rows:>8} ({absorbed_rows / total * 100:4.1f}%)  concept {len(absorbed_c)}종"
)
print(
    f"  메타/표지 노이즈        : {meta_rows:>8} ({meta_rows / total * 100:4.1f}%)  concept {len(meta_c)}종"
)
print(
    f"  주석 고유 detail(분류대상): {detail_rows:>8} ({detail_rows / total * 100:4.1f}%)  concept {len(detail_c)}종"
)

print("\n=== detail 최빈 concept 35(분류 후보) ===")
for c, n in detail_c.most_common(35):
    print(f"  {n:>6}행  {c:55s} {detail_label.get(c, '')[:24]}")
