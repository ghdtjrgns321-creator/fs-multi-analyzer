"""detail concept을 IFRS 주석 ~25 카테고리로 토큰규칙 분류 → 커버리지 측정(읽기전용).

순서가 중요(다중매칭 시 먼저 매칭이 승). 예: RelatedParty > Receivable, DeferredTax > Tax.
목적: 카테고리별 detail 흡수율·미분류 잔여(기타) 측정 후 config 확정.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.normalize.config import load_canonical_accounts

BASE = Path("data/companies")
SAMPLE = 400
PREFIXES = ("ifrs-full_", "ifrs_", "dart_")

# (카테고리, [토큰...]) — 우선순위 순서. concept(소문자)에 토큰 포함되면 매칭.
CATEGORIES: list[tuple[str, list[str]]] = [
    ("특수관계자거래", ["relatedparty", "relatedpartie", "keymanagement"]),
    ("주식기준보상", ["sharebasedpayment", "shareoption", "stockoption"]),
    ("리스", ["lease", "rightofuse", "rightofuse"]),
    (
        "확정급여_퇴직",
        ["definedbenefit", "postemployment", "retirement", "severance", "employeebenefit"],
    ),
    ("이연법인세", ["deferredtax"]),
    ("법인세", ["incometax", "taxexpense", "currenttax", "taxrelating"]),
    ("파생_위험회피", ["derivative", "hedge", "swap", "forwardcontract", "optioncontract"]),
    ("사채", ["bond", "debenture", "convertible", "warrant"]),
    (
        "차입금조건",
        [
            "borrowing",
            "loanspayable",
            "maturity",
            "interestrate",
            "collateral",
            "pledge",
            "secured",
            "liabilitiesarisingfromfinancing",
        ],
    ),
    (
        "종속관계기업투자",
        ["subsidiar", "associate", "jointventure", "jointarrangement", "equitymethod"],
    ),
    ("정부보조금", ["governmentgrant"]),
    ("외화환산", ["foreignexchange", "foreigncurrency", "exchangerate", "translationof"]),
    ("손상", ["impairment", "recoverableamount", "cashgeneratingunit"]),
    ("무형자산명세", ["intangibleasset", "amortisation", "goodwill"]),
    ("유형자산명세", ["propertyplantandequipment", "depreciation"]),
    ("투자부동산", ["investmentproperty"]),
    (
        "재고자산",
        [
            "inventor",
            "rawmaterial",
            "finishedgood",
            "merchandise",
            "workinprogress",
            "workinprocess",
            "goodsintransit",
            "suppliesinventory",
            "semifinished",
        ],
    ),
    (
        "매출채권_대손",
        [
            "tradereceivable",
            "tradeandotherreceivable",
            "doubtful",
            "allowanceforcredit",
            "creditloss",
            "lossallowance",
            "otherreceivable",
            "baddebt",
            "constructioncontract",
        ],
    ),
    ("매입채무", ["tradepayable", "tradeandotherpayable", "otherpayable"]),
    (
        "수익_고객계약",
        [
            "revenue",
            "contractswithcustomers",
            "contractasset",
            "contractliabilit",
            "duefromcustomers",
            "duetocustomers",
            "contractwork",
            "billings",
        ],
    ),
    (
        "이자배당손익",
        [
            "interestincome",
            "interestexpense",
            "financeincome",
            "financeexpense",
            "financecost",
            "dividendincome",
        ],
    ),
    (
        "금융상품",
        [
            "financialasset",
            "financialliabilit",
            "financialinstrument",
            "fairvalue",
            "availableforsale",
            "amortisedcost",
            "loansreceived",
            "loanreceivable",
            "loansreceivable",
            "loansnet",
        ],
    ),
    (
        "위험관리공시",
        [
            "creditrisk",
            "marketrisk",
            "liquidityrisk",
            "currencyrisk",
            "interestraterisk",
            "sensitivityanalysis",
            "exposuretorisk",
            "managingrisk",
            "riskvariable",
            "maximumexposure",
            "notionalamount",
            "riskmanagement",
        ],
    ),
    ("약정_우발", ["commitment", "contingent", "guarantee"]),
    ("현금금융기관", ["cashandcashequivalent", "deposit", "shortterminvestment"]),
    (
        "자본적립금",
        [
            "retainedearning",
            "treasuryshare",
            "capitalsurplus",
            "reserve",
            "capitalstock",
            "sharecapital",
            "sharepremium",
            "dividendspaid",
            "dividendsproposed",
        ],
    ),
    ("주당이익", ["earningspershare", "pershare", "weightedaverageshare", "weightedaveragenumber"]),
    ("충당부채", ["provision", "litigation", "warrant"]),
]


def stem(s: str) -> str:
    for p in PREFIXES:
        if s.startswith(p):
            s = s[len(p) :]
            break
    return s.lower()


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


def is_meta(c: str) -> bool:
    cl = c.lower()
    return any(h in cl for h in META_HINT)


def classify(concept: str) -> str | None:
    cl = concept.lower()
    for cat, toks in CATEGORIES:
        if any(t in cl for t in toks):
            return cat
    return None


acc = load_canonical_accounts(Path("config/canonical_accounts.yaml"))
canon_stem = set()
for a in acc:
    for aid in getattr(a, "account_ids", []) or []:
        canon_stem.add(stem(aid))

files = []
for corp in sorted(BASE.iterdir()):
    if corp.is_dir():
        for yr in sorted(corp.iterdir()):
            t = yr / "raw" / "notes_xbrl" / "note_facts.tsv"
            if t.exists():
                files.append(t)
step = max(1, len(files) // SAMPLE)
sample = files[::step][:SAMPLE]
print(f"수집 {len(files)} 표본 {len(sample)}\n")

cat_rows: Counter = Counter()
detail_total = 0
other_concepts: Counter = Counter()
other_label: dict[str, str] = {}
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
        if is_meta(concept) or stem(concept) in canon_stem:
            continue
        detail_total += 1
        cat = classify(concept)
        if cat:
            cat_rows[cat] += 1
        else:
            cat_rows["기타주석"] += 1
            other_concepts[concept] += 1
            other_label.setdefault(concept, label_ko)

covered = detail_total - cat_rows["기타주석"]
print(f"detail 행: {detail_total}")
print(f"  카테고리 분류: {covered} ({covered / detail_total * 100:.1f}%)")
print(
    f"  기타주석     : {cat_rows['기타주석']} ({cat_rows['기타주석'] / detail_total * 100:.1f}%)\n"
)
print("=== 카테고리별 detail 행수 ===")
for cat, _ in CATEGORIES:
    print(f"  {cat_rows.get(cat, 0):>7}  {cat}")
print(f"  {cat_rows['기타주석']:>7}  기타주석")
print("\n=== 기타주석 최빈 25(추가 카테고리 후보) ===")
for c, n in other_concepts.most_common(25):
    print(f"  {n:>5}행  {c:50s} {other_label.get(c, '')[:22]}")
