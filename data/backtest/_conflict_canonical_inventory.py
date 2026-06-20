"""id_label_conflict 충돌 인벤토리 측정 (Phase 1).

배경: normalized_financials.mapping_status='id_label_conflict' 행은 account_id가 채택된
canonical(id-canonical)과, 한글 공시명 label을 가진다. label이 가리키는 canonical은
AccountMapper의 _by_alias(normalize_label(label) → CanonicalAccount)로 다시 구해야
비교 가능하다(id-first 정책이라 저장 canonical은 항상 id측).

산출:
  1) 충돌에 등장하는 distinct canonical 집합(id측+label측 합집합) 크기 N.
  2) sj_div 4분면 — id_canonical.statement·label_canonical.statement를 row.sj_div와
     비교(compatible)해 (id만맞음/label만맞음/둘다맞음/둘다불일치) 건수.
  3) 동일표(두 canonical statement 동일) & 거친범주 상이 쌍 목록(triage 대상) → JSON 덤프.

거친 범주는 plan.md "범주(category) 차원 설계" 표의 이름 패턴으로 coarse_category()가 도출.
corp/연도/계정명을 분기 조건에 하드코딩하지 않는다(corpus는 _holistic_chunks.json, 범주는
이름 패턴 함수).

실행: PYTHONPATH=. uv run python data/backtest/_conflict_canonical_inventory.py
      (기본 = 감사 corpus 101사/383cy)
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import duckdb

from config.settings import settings
from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import AccountMapper

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = ROOT / "data" / "backtest" / "_holistic_chunks.json"
OUT_PAIRS = ROOT / "dev" / "active" / "id-label-conflict-category-arbiter" / "_conflict_pairs.json"

# IS↔CIS 호환(plan.md _STATEMENT_COMPATIBLE 철학과 동일). 나머지는 자기표만 호환.
_COMPATIBLE = {("IS", "CIS"), ("CIS", "IS")}


def corpus_targets() -> list[tuple[str, str]]:
    """감사 corpus 101사/383cy (corp, year) 목록 — _is_cf_arithmetic.py와 동일 패턴."""
    chunks = json.loads(CHUNKS.read_text("utf-8"))["chunks"]
    out = []
    for ch in chunks:
        for comp in ch["companies"]:
            for year in comp["years"]:
                out.append((comp["corp"], str(year)))
    return out


def compatible(sj_div: str, statement: str) -> bool:
    """행 sj_div와 canonical statement 표 호환성."""
    if not sj_div or not statement:
        return False
    return sj_div == statement or (sj_div, statement) in _COMPATIBLE


def coarse_category(name: str, statement: str) -> str:
    """canonical 이름+statement → 거친 범주 코드(plan.md 표 패턴). 미분류는 '{stmt}?'.

    이름 패턴만으로 도출(특정 계정 하드코딩 아님). 충돌 중재에 필요한 최소 입도만 가른다.
    체크 순서가 의미 있다 — 더 구체적인 패턴(소계·oci)을 먼저 본다.
    """
    n = name.replace(" ", "")

    if statement in ("IS", "CIS"):
        # pl_oci: 기타포괄·재측정·환산·평가손익
        if any(k in n for k in ("기타포괄", "재측정", "환산", "평가손익", "위험회피", "재분류")):
            return "pl_oci"
        # pl_subtotal: 이익·순이익·소계·총포괄 (단 '차감전'은 소계로 보되 expense 아님)
        if any(k in n for k in ("이익", "순손익", "손익", "소계", "총포괄", "포괄손익")):
            return "pl_subtotal"
        # pl_expense: 원가·비용·상각·법인세·손실(차감전 제외 — 위 subtotal에서 이미 잡힘)
        if any(k in n for k in ("원가", "비용", "상각", "법인세", "손실")):
            return "pl_expense"
        # pl_revenue: 매출·수익
        if any(k in n for k in ("매출", "수익")):
            return "pl_revenue"
        return "pl?"

    if statement == "CF":
        # cf_subtotal: 활동현금흐름·순증감·기초/기말현금
        if any(
            k in n for k in ("활동현금흐름", "순증감", "기초현금", "기말현금", "현금및현금성자산순")
        ):
            return "cf_subtotal"
        # cf_financing: 차입금·사채·배당·자기주식·증자·재무
        if any(
            k in n for k in ("차입", "사채", "배당", "자기주식", "증자", "재무활동", "리스부채")
        ):
            return "cf_financing"
        # cf_investing: 유형/무형자산·금융상품·부동산 취득/처분·투자
        if any(
            k in n
            for k in (
                "유형자산",
                "무형자산",
                "투자",
                "금융상품",
                "부동산",
                "취득",
                "처분",
                "종속기업",
            )
        ):
            return "cf_investing"
        # cf_adjust: 조정·가감·증감(운전자본 조정 라인)
        if any(k in n for k in ("조정", "가감", "증가", "감소", "증감")):
            return "cf_adjust"
        # cf_operating: 영업활동·창출현금·운전자본·당기순이익조정
        if any(k in n for k in ("영업", "창출", "운전자본", "순이익")):
            return "cf_operating"
        return "cf?"

    if statement == "BS":
        if any(k in n for k in ("부채", "충당", "차입", "사채", "미지급", "선수", "예수")):
            return "bs_liability"
        if any(k in n for k in ("자본", "지분", "이익잉여", "자본잉여", "주식", "결손")):
            return "bs_equity"
        return "bs_asset"

    if statement == "SCE":
        return "sce_change"

    return f"{statement or '?'}?"


def collect_conflicts(mapper: AccountMapper) -> list[dict]:
    """corpus 전수 순회 → id_label_conflict 행을 (corp,year,sj_div,account_id,label,
    id_canonical) 로 수집하고 label_canonical을 _by_alias로 재구성."""
    by_id = mapper._by_id  # account_id → CanonicalAccount
    by_alias = mapper._by_alias  # normalize_label(alias) → CanonicalAccount

    rows: list[dict] = []
    for corp, year in corpus_targets():
        db = ROOT / "data" / "companies" / corp / year / "analysis.duckdb"
        if not db.exists():
            continue
        con = duckdb.connect(str(db), read_only=True)
        try:
            recs = con.execute(
                "SELECT sj_div, account_id, label, canonical "
                "FROM normalized_financials WHERE mapping_status = 'id_label_conflict'"
            ).fetchall()
        finally:
            con.close()
        for sj_div, account_id, label, canonical in recs:
            id_acct = by_id.get(str(account_id))
            lbl_acct = by_alias.get(normalize_label(label))
            rows.append(
                {
                    "corp": corp,
                    "year": year,
                    "sj_div": sj_div,
                    "account_id": account_id,
                    "label": label,
                    "id_canonical": id_acct.name if id_acct else canonical,
                    "id_statement": id_acct.statement if id_acct else "",
                    "label_canonical": lbl_acct.name if lbl_acct else None,
                    "label_statement": lbl_acct.statement if lbl_acct else None,
                }
            )
    return rows


def main() -> None:
    mapper = AccountMapper(load_canonical_accounts(settings.config_dir / "canonical_accounts.yaml"))
    rows = collect_conflicts(mapper)

    scanned = len({(r["corp"], r["year"]) for r in rows})
    total = len(rows)
    no_alias = sum(1 for r in rows if r["label_canonical"] is None)
    have_alias = [r for r in rows if r["label_canonical"] is not None]

    # 산출 1: distinct canonical 집합(id측 + label측 합집합)
    canon_set: set[str] = set()
    for r in rows:
        canon_set.add(r["id_canonical"])
        if r["label_canonical"]:
            canon_set.add(r["label_canonical"])
    n_distinct = len(canon_set)

    # 산출 2: sj_div 4분면 (by_alias 있는 행만 — 두 canonical 비교 가능)
    quad = Counter()
    for r in have_alias:
        id_ok = compatible(r["sj_div"], r["id_statement"])
        lbl_ok = compatible(r["sj_div"], r["label_statement"])
        if id_ok and lbl_ok:
            quad["both"] += 1
        elif id_ok and not lbl_ok:
            quad["id_only"] += 1
        elif lbl_ok and not id_ok:
            quad["label_only"] += 1
        else:
            quad["neither"] += 1

    # 산출 3: 동일표 & 거친범주 상이 (triage 대상)
    same_stmt = [r for r in have_alias if r["id_statement"] == r["label_statement"]]
    diff_stmt = [r for r in have_alias if r["id_statement"] != r["label_statement"]]
    same_cat = 0
    diff_cat_pairs: list[dict] = []
    for r in same_stmt:
        c_id = coarse_category(r["id_canonical"], r["id_statement"])
        c_lb = coarse_category(r["label_canonical"], r["label_statement"])
        r2 = {**r, "cat_id": c_id, "cat_label": c_lb}
        if c_id == c_lb:
            same_cat += 1
        else:
            diff_cat_pairs.append(r2)

    # 동일표 범주상이 → distinct 쌍(canonical 조합)으로도 집계
    diff_cat_keys = Counter(
        (p["id_canonical"], p["label_canonical"], p["cat_id"], p["cat_label"])
        for p in diff_cat_pairs
    )

    print(f"[충돌 인벤토리] 스캔 {scanned} 회사연도 (corpus=감사101사)")
    print(f"  id_label_conflict 발화 행: {total}")
    print(f"  label에 alias 없음(by_alias=None): {no_alias}  (충돌 미감지 config gap, 별도 트랙)")
    print(f"  by_alias 있는 비교가능 행: {len(have_alias)}")
    print()
    print(f"[산출1] 충돌 등장 distinct canonical 집합 크기 N = {n_distinct}  (기대 N<600)")
    print()
    print("[산출2] sj_div 4분면 (by_alias 있는 행 기준):")
    print(f"  id만맞음   = {quad['id_only']}")
    print(f"  label만맞음 = {quad['label_only']}")
    print(f"  둘다맞음   = {quad['both']}")
    print(f"  둘다불일치 = {quad['neither']}")
    print(f"  합계       = {sum(quad.values())}")
    print()
    print("[산출3] 표 동일성 분해:")
    print(f"  두 canonical statement 상이 = {len(diff_stmt)}")
    print(f"  두 canonical statement 동일 = {len(same_stmt)}")
    print(f"  └ 동일표 거친범주 동일(동의어) = {same_cat}")
    print(f"  └ 동일표 거친범주 상이(진짜충돌 후보, triage 대상) = {len(diff_cat_pairs)}")
    print(
        f"     distinct (id_canonical, label_canonical, cat_id, cat_label) 쌍 = {len(diff_cat_keys)}"
    )
    print()
    print("  동일표 범주상이 distinct 쌍 (건수 내림차순):")
    for (cid, clb, kid, klb), cnt in diff_cat_keys.most_common():
        print(f"    {cnt:4}x  id={cid}[{kid}]  ↔  label={clb}[{klb}]")

    # triage 입력용 JSON 덤프 (distinct 쌍 + 대표 corp/year)
    OUT_PAIRS.parent.mkdir(parents=True, exist_ok=True)
    rep = {}
    for p in diff_cat_pairs:
        key = (p["id_canonical"], p["label_canonical"])
        rep.setdefault(key, []).append(
            {"corp": p["corp"], "year": p["year"], "sj_div": p["sj_div"], "label": p["label"]}
        )
    dump = [
        {
            "id_canonical": cid,
            "label_canonical": clb,
            "cat_id": kid,
            "cat_label": klb,
            "statement": next(
                p["id_statement"]
                for p in diff_cat_pairs
                if p["id_canonical"] == cid and p["label_canonical"] == clb
            ),
            "count": cnt,
            "examples": rep[(cid, clb)][:3],
        }
        for (cid, clb, kid, klb), cnt in diff_cat_keys.most_common()
    ]
    OUT_PAIRS.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"[덤프] 동일표 범주상이 distinct 쌍 → {OUT_PAIRS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
