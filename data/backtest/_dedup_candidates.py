"""same-statement 충돌 쌍 보수적 3분류 시드 (synonym / narrower / mistag).

배경: `_conflict_canonical_inventory.py`가 측정한 same-statement(두 canonical statement
동일) 충돌 distinct 쌍을 입력으로, 각 쌍 (id_canonical, label_canonical)을 자동 시드 분류한다.

lexical·범주·영문id 유사도 3종이 모두 자동분류 실패로 측정됐으므로(_264_triage.md), 이
스크립트는 **확정이 아니라 보수적 시드**다. 명백한 narrower(세분화=통합 금지)와 명백한
mistag(진짜오매핑=온보딩 게이트행)만 자동 분류하고, 애매한 나머지는 전부 synonym 큐(사람
검수)로 보낸다.

분류 규칙(보수):
  - narrower(통합 금지): 한 name이 다른 것의 부분문자열이고, 차이가 {유동,비유동,단기,장기,
    순,총,비,유동성,금융,연결,별도} 같은 분류 수식어뿐 → 세분화. id가 더 정확하므로 통합 시
    유동/비유동 정보 손실. 조금이라도 세분화 의심이면 narrower(통합 차단 안전).
  - mistag(진짜오매핑 후보→게이트행): 두 거친범주(coarse_category)가 다르면서, 그 차이가
    _264_triage.md의 진짜충돌 구조 패턴(수익↔이익소계, 조정↔소계, OCI↔법인세효과,
    cross-category 실물 상이)에 해당할 때만. 확신 없으면 synonym 큐로(보수).
  - synonym(통합 후보, 사람검수 큐): 위 둘 다 아닌 나머지.

생존자 선정(synonym 쌍에만, 결정론): ①account_ids 많은 쪽 ②동수면 ifrs-full_ 보유 쪽
③그래도 동수면 수식어 적은(짧고 일반적인) name.

corp/연도/계정명을 분기 조건에 하드코딩하지 않는다. corpus는 _holistic_chunks.json(인벤토리
스크립트 재사용), 분류는 이름 패턴·범주 함수.

실행: PYTHONPATH=. uv run python data/backtest/_dedup_candidates.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

# 같은 디렉터리의 인벤토리 스크립트를 모듈로 재사용(corpus 순회·범주 도출 동일 방식).
from _conflict_canonical_inventory import (  # noqa: E402
    coarse_category,
    collect_conflicts,
)

from config.settings import settings
from src.normalize.config import load_canonical_accounts
from src.normalize.mapper import AccountMapper

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "backtest" / "_dedup_candidates.json"

# narrower 판정용 분류 수식어 토큰: 한 name이 다른 것에 이 토큰만 더 붙은 형태면 세분화.
# (회계 분류축 — 유동성·만기·순총·연결범위. 이 토큰만 차이나면 같은 본계정의 세분.)
QUALIFIER_TOKENS = (
    "유동성",
    "비유동",
    "유동",
    "단기",
    "장기",
    "순",
    "총",
    "비",
    "금융",
    "연결",
    "별도",
)

# mistag 진짜충돌 구조 범주쌍(_264_triage.md 진짜충돌 9쌍 패턴). 거친범주 frozenset.
# 두 canonical의 coarse_category가 이 조합이고, 미분류('?')가 아닐 때만 mistag.
MISTAG_CATEGORY_PAIRS = frozenset(
    {
        frozenset({"pl_revenue", "pl_subtotal"}),  # 수익 ↔ 이익소계 (영업이익↔매출)
        frozenset({"pl_oci", "pl_expense"}),  # OCI 본액 ↔ 법인세효과/손익
        frozenset({"cf_adjust", "cf_operating"}),  # 가감조정 ↔ 영업창출/운전자본 소계
        frozenset({"cf_adjust", "cf_subtotal"}),  # 조정 ↔ 현금흐름 소계
        frozenset({"pl_revenue", "pl_subtotal"}),
    }
)


def _strip_qualifiers(name: str) -> str:
    """name에서 분류 수식어 토큰을 앞에서부터 제거한 핵심부 반환(narrower 판정용)."""
    core = name.replace(" ", "")
    changed = True
    while changed:
        changed = False
        for tok in QUALIFIER_TOKENS:
            if core.startswith(tok) and len(core) > len(tok):
                core = core[len(tok) :]
                changed = True
                break
    return core


def is_narrower(a: str, b: str) -> bool:
    """a, b가 세분화 관계인가(부분문자열 + 수식어 차이만). 통합 금지 판정.

    보수적: (1) 한쪽이 다른쪽의 부분문자열이고 차이가 수식어 토큰으로만 구성, 또는
    (2) 수식어 제거 핵심부가 동일하고 원본 길이가 다르면(=한쪽이 더 세분) narrower.
    """
    na, nb = a.replace(" ", ""), b.replace(" ", "")
    if na == nb:
        return False  # 완전 동일은 synonym(중복) 처리
    short, long = (na, nb) if len(na) <= len(nb) else (nb, na)
    # (1) 부분문자열 + 차이가 수식어 토큰으로만
    if short in long:
        diff = long.replace(short, "", 1)
        rest = diff
        for tok in QUALIFIER_TOKENS:
            rest = rest.replace(tok, "")
        if rest == "":
            return True
    # (2) 수식어 제거 후 핵심부 동일 & 원본 길이 상이(한쪽이 더 세분)
    ca, cb = _strip_qualifiers(a), _strip_qualifiers(b)
    if ca == cb and na != nb:
        return True
    return False


def is_mistag(cat_a: str, cat_b: str) -> bool:
    """두 거친범주가 진짜충돌 구조 패턴인가. 미분류('?') 포함이면 보수적으로 False(synonym)."""
    if "?" in cat_a or "?" in cat_b:
        return False  # 범주 도출 노이즈 — 확신 없음 → synonym 큐
    if cat_a == cat_b:
        return False  # 같은 범주는 동의어
    return frozenset({cat_a, cat_b}) in MISTAG_CATEGORY_PAIRS


def classify(a: str, b: str, stmt: str) -> tuple[str, str]:
    """쌍 (a=id_canonical, b=label_canonical) → (klass, reason). 보수 우선순위:
    narrower(통합금지) → mistag(게이트행) → synonym(나머지, 사람검수).
    """
    if is_narrower(a, b):
        return "narrower", f"세분화 관계(수식어 차이만): '{a}' vs '{b}' — 통합 금지(정보손실)"
    cat_a = coarse_category(a, stmt)
    cat_b = coarse_category(b, stmt)
    if is_mistag(cat_a, cat_b):
        return (
            "mistag",
            f"거친범주 진짜충돌 구조: {cat_a} ↔ {cat_b} (id='{a}', label='{b}') — 온보딩 게이트행",
        )
    return (
        "synonym",
        f"narrower·mistag 아님(범주 {cat_a}/{cat_b}) — 통합 후보, 사람검수 큐",
    )


def _qualifier_count(name: str) -> int:
    """name에 포함된 수식어 토큰 수(생존자 선정 tie-break — 적을수록 일반적)."""
    n = name.replace(" ", "")
    return sum(1 for tok in QUALIFIER_TOKENS if tok in n)


def pick_survivor(a: str, b: str, by_name: dict) -> str:
    """synonym 쌍 생존 canonical 결정론 선정.
    ①account_ids 많은 쪽 ②동수면 ifrs-full_ 보유 쪽 ③동수면 수식어 적은(짧고 일반) name.
    """
    acct_a = by_name.get(a)
    acct_b = by_name.get(b)
    ids_a = len(acct_a.account_ids) if acct_a else 0
    ids_b = len(acct_b.account_ids) if acct_b else 0
    if ids_a != ids_b:
        return a if ids_a > ids_b else b
    has_ifrs_a = any(
        str(i).startswith("ifrs-full_") for i in (acct_a.account_ids if acct_a else [])
    )
    has_ifrs_b = any(
        str(i).startswith("ifrs-full_") for i in (acct_b.account_ids if acct_b else [])
    )
    if has_ifrs_a != has_ifrs_b:
        return a if has_ifrs_a else b
    qa, qb = _qualifier_count(a), _qualifier_count(b)
    if qa != qb:
        return a if qa < qb else b
    return a if len(a) <= len(b) else b  # 최종: 짧은 name


def build_pairs(mapper: AccountMapper) -> list[tuple[str, str, str]]:
    """same-statement 충돌 distinct 쌍 (id_canonical, label_canonical, statement) 전체.

    인벤토리 collect_conflicts 재사용 → label_canonical 비None & 두 statement 동일 행만.
    """
    rows = collect_conflicts(mapper)
    have_alias = [r for r in rows if r["label_canonical"] is not None]
    same_stmt = [r for r in have_alias if r["id_statement"] == r["label_statement"]]
    pairs: dict[tuple[str, str], str] = {}
    for r in same_stmt:
        key = (r["id_canonical"], r["label_canonical"])
        pairs.setdefault(key, r["id_statement"])
    return [(a, b, stmt) for (a, b), stmt in pairs.items()]


def main() -> None:
    accounts = load_canonical_accounts(settings.config_dir / "canonical_accounts.yaml")
    mapper = AccountMapper(accounts)
    by_name = {acct.name: acct for acct in accounts}

    pairs = build_pairs(mapper)
    results: list[dict] = []
    counts: Counter = Counter()
    for a, b, stmt in pairs:
        klass, reason = classify(a, b, stmt)
        survivor = pick_survivor(a, b, by_name) if klass == "synonym" else None
        counts[klass] += 1
        results.append(
            {
                "a": a,
                "b": b,
                "statement": stmt,
                "klass": klass,
                "survivor": survivor,
                "reason": reason,
            }
        )

    # 자기검증: 핵심 케이스 3개를 분류기에 직접 통과(corpus 존재 여부와 무관, 로직 검증).
    self_check_inputs = [
        ("유동리스부채", "리스부채", "BS"),  # 기대: narrower
        ("FVPL금융자산", "당기손익-공정가치측정금융자산", "BS"),  # 기대: synonym
        ("영업이익", "매출", "IS"),  # 기대: mistag
    ]
    self_check = []
    for a, b, stmt in self_check_inputs:
        klass, reason = classify(a, b, stmt)
        survivor = pick_survivor(a, b, by_name) if klass == "synonym" else None
        self_check.append(
            {
                "a": a,
                "b": b,
                "statement": stmt,
                "klass": klass,
                "survivor": survivor,
                "reason": reason,
            }
        )

    OUT.write_text(
        json.dumps({"pairs": results, "_self_check": self_check}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[dedup 후보 3분류] same-statement distinct 쌍 = {len(pairs)}")
    print(f"  synonym (통합 후보, 사람검수) = {counts['synonym']}")
    print(f"  narrower(세분화 보존, 통합금지) = {counts['narrower']}")
    print(f"  mistag  (진짜오매핑, 게이트행)  = {counts['mistag']}")
    print()
    print("[자기검증] 핵심 케이스 3개 (분류기 직접 통과):")
    for sc in self_check:
        print(f"  {sc['a']} ↔ {sc['b']}  →  {sc['klass']}")
    print()
    print(f"[산출] {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
