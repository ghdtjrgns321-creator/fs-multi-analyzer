"""전수 매핑 정합성 감사 — 오매핑(틀린 canonical) 탐지(읽기전용·자기참조 없음).

현 config의 모든 account_id→canonical에 대해, account_id의 IFRS 영문 concept토큰이 가리키는
'개념계열'과 canonical 한글명의 개념계열이 충돌하면 의심오매핑으로 플래그한다.
판정 기준은 account_id 영문 표준명(IFRS) — 현 매핑을 권위로 쓰지 않는다(자기참조 금지).
"""

from __future__ import annotations

from pathlib import Path

import yaml

CFG = Path("config/canonical_accounts.yaml")
PREFIXES = ("ifrs-full_", "ifrs_", "dart_")


def stem(s: str) -> str:
    for p in PREFIXES:
        if s.startswith(p):
            return s[len(p) :].lower()
    return s.lower()


# 영문 account_id 토큰 → 개념계열. 우선순위 순(앞이 강함). 복합어 충돌 방지 위해 구체어 먼저.
EN_CONCEPT = [
    ("costofsales", "원가"),
    ("costofgoods", "원가"),
    ("costofmerchandise", "원가"),
    ("costofsalesfrom", "원가"),
    ("revenue", "수익매출"),
    ("sales", "수익매출"),
    ("grossprofit", "매출총이익"),
    ("tradereceivable", "채권"),
    ("receivable", "채권"),
    ("tradepayable", "채무"),
    ("payable", "채무"),
    ("inventor", "재고"),
    ("rawmaterial", "재고"),
    ("finishedgood", "재고"),
    ("merchandise", "재고"),
    ("borrowing", "차입"),
    ("loanspayable", "차입"),
    ("bond", "사채"),
    ("debenture", "사채"),
    ("cashandcashequivalent", "현금"),
    ("propertyplantandequipment", "유형자산"),
    ("depreciation", "감가상각"),
    ("intangible", "무형자산"),
    ("amortisation", "상각"),
    ("goodwill", "영업권"),
    ("investmentproperty", "투자부동산"),
    ("deferredtax", "이연법인세"),
    ("incometax", "법인세"),
    ("taxexpense", "법인세"),
    ("provision", "충당"),
    ("impairment", "손상"),
    ("interest", "이자"),
    ("dividend", "배당"),
    ("lease", "리스"),
    ("rightofuse", "사용권"),
    ("definedbenefit", "퇴직급여"),
    ("severance", "퇴직급여"),
    ("retirement", "퇴직급여"),
    ("sharebasedpayment", "주식보상"),
    ("derivative", "파생"),
    ("hedge", "위험회피"),
    ("equity", "자본"),
    ("retainedearning", "이익잉여금"),
    ("capitalsurplus", "자본잉여금"),
    ("treasuryshare", "자기주식"),
    ("baddebt", "대손"),
    ("doubtful", "대손"),
    ("salarieswages", "급여"),
    ("employeebenefit", "급여복리"),
    ("earningspershare", "주당이익"),
    ("subsidiar", "종속관계"),
    ("associate", "종속관계"),
    ("jointventure", "종속관계"),
    ("governmentgrant", "정부보조"),
]
# canonical 한글명 토큰 → 개념계열(영문과 같은 라벨 체계).
KO_CONCEPT = [
    ("매출원가", "원가"),
    ("매출총이익", "매출총이익"),
    ("매출", "수익매출"),
    ("수익", "수익매출"),
    ("매입채무", "채무"),
    ("매출채권", "채권"),
    ("채권", "채권"),
    ("미수", "채권"),
    ("채무", "채무"),
    ("미지급", "채무"),
    ("재고", "재고"),
    ("차입", "차입"),
    ("사채", "사채"),
    ("현금", "현금"),
    ("유형자산", "유형자산"),
    ("감가상각", "감가상각"),
    ("무형자산", "무형자산"),
    ("상각", "상각"),
    ("영업권", "영업권"),
    ("투자부동산", "투자부동산"),
    ("이연법인세", "이연법인세"),
    ("법인세", "법인세"),
    ("충당", "충당"),
    ("손상", "손상"),
    ("이자", "이자"),
    ("배당", "배당"),
    ("리스", "리스"),
    ("사용권", "사용권"),
    ("퇴직급여", "퇴직급여"),
    ("주식보상", "주식보상"),
    ("주식기준보상", "주식보상"),
    ("파생", "파생"),
    ("위험회피", "위험회피"),
    ("자본금", "자본"),
    ("자본총계", "자본"),
    ("자본", "자본"),
    ("이익잉여금", "이익잉여금"),
    ("자본잉여금", "자본잉여금"),
    ("자기주식", "자기주식"),
    ("대손", "대손"),
    ("급여", "급여"),
    ("주당이익", "주당이익"),
    ("종속기업", "종속관계"),
    ("관계기업", "종속관계"),
    ("정부보조", "정부보조"),
]


# 흔한 오탐 차단: 처분/취득/지분법/지분은 매출·이자가 아니다(우선 적용).
EN_OVERRIDE = [
    ("accountedforusingequitymethod", "종속관계"),  # 지분법 (≠ 자본)
    ("interestsinassociates", "종속관계"),
    ("interestsininvestments", "종속관계"),
    ("interestsinsubsidiar", "종속관계"),
    ("proceedsfromsalesof", "처분취득"),  # 자산 처분 (≠ 매출)
    ("proceedsfromdisposal", "처분취득"),
    ("purchaseof", "처분취득"),
    ("hybridbond", "자본"),  # 신종자본증권 = 자본
    ("perpetual", "자본"),
]


def en_family(account_id: str) -> str:
    s = stem(account_id)
    for tok, fam in EN_OVERRIDE:
        if tok in s:
            return fam
    for tok, fam in EN_CONCEPT:
        if tok in s:
            return fam
    return ""


# 한글 토큰은 가장 긴 것 우선(매출채권이 매출보다 먼저 매칭되도록).
_KO_SORTED = sorted(KO_CONCEPT, key=lambda kv: -len(kv[0]))


def ko_family(name: str) -> str:
    for tok, fam in _KO_SORTED:
        if tok in name:
            return fam
    return ""


# 진짜 오매핑 = 모순쌍(반대 개념). 단순 "다름"은 오탐이라 제외.
CONTRADICTIONS = [
    frozenset({"수익매출", "원가"}),
    frozenset({"채권", "채무"}),
    frozenset({"차입", "사채"}),
    frozenset({"수익매출", "비용"}),
    frozenset({"자산", "부채"}),
    frozenset({"이익", "손실"}),
]


def is_contradiction(ef: str, kf: str) -> bool:
    return any({ef, kf} == c for c in CONTRADICTIONS)


cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))["canonical_accounts"]
total = 0
agree = 0
no_en = 0
flags = []
for name, body in cfg.items():
    kf = ko_family(name)
    for aid in body.get("account_ids", []) or []:
        total += 1
        ef = en_family(aid)
        if not ef:
            no_en += 1
            continue
        diff = kf and ef != kf
        if diff and is_contradiction(ef, kf):
            flags.append((aid, name, ef, kf, "개념모순"))
        else:
            agree += 1
        # 유동/비유동 뒤바뀜(BS 실오류 유형): canonical 유동인데 id가 noncurrent, 또는 반대
        s = stem(aid)
        has_noncur = "noncurrent" in s
        has_cur = ("current" in s) and not has_noncur
        if "비유동" in name and has_cur:
            flags.append((aid, name, "current", "비유동", "유동성"))
        elif ("유동" in name) and ("비유동" not in name) and has_noncur:
            flags.append((aid, name, "noncurrent", "유동", "유동성"))

print(f"전수 매핑 account_id: {total}")
print(f"  영문개념 추출 가능: {total - no_en} / 일치·비모순: {agree}")
print(f"  영문개념 미추출(판정보류): {no_en}")
print(f"  ⚠ 모순 오매핑 후보(원가↔수익·채권↔채무 등 반대개념): {len(flags)}\n")
print("=== 모순 오매핑 후보(account_id | 현canonical | 영문 vs 한글) ===")
for aid, name, ef, kf, kind in sorted(flags, key=lambda x: x[1]):
    print(f"  {aid[:52]:52s} → [{name[:20]}]  {ef} ≠ {kf}")
if not flags:
    print("  (없음 — 모순 오매핑 0)")
