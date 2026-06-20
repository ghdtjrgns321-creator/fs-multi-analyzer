"""_audit_alias_mapped.json(표준ID 보유 + ALIAS 매핑 = 등록누락/오매핑 후보 전수)을
config 등록ID·account_id 표준명 실질로 분류해 data/backtest/ALIAS_MISMAP_AUDIT.md 생성.

분류(자기참조 회피): canonical의 현재 등록 account_ids(config)와 이름흡수된 account_id의
IFRS 표준명을 비교한다.
- 등록누락·동일개념: aid stem이 canonical 등록ID stem과 동일(접두사 dart_/ifrs-full_만 차이) → 무해, 등록만 추가.
- 오매핑(이종개념): 유동↔비유동, 통합(AndOther)↔순수, 이종 측정종류 등 실질이 다른데 이름으로 흡수.
- 등록ID 없음(alias-only canonical): 비교 불가 → 표준명 신호(유동/비유동·종류)로만 판정, 나머지 수동확인.
수정 여부는 사용자 결정(§8). 단정 금지, 전수 증거로 제시.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.normalize.config import load_canonical_accounts

IN = Path("data/backtest/_audit_alias_mapped.json")
OUT = Path("data/backtest/ALIAS_MISMAP_AUDIT.md")
CONFIG = Path("config/canonical_accounts.yaml")
PREFIXES = ("ifrs-full_", "ifrs_", "dart_")
CUR_RE = re.compile(r"(?<!Non)(?<!non)Current|Shortterm|ShortTerm")
NONCUR_RE = re.compile(r"Noncurrent|NonCurrent|noncurrent|Longterm|LongTerm")
FLOW_RE = re.compile(
    r"AdjustmentsFor|ProceedsFrom|PurchaseOf|PaymentsOf|PaymentsFor|RepaymentsOf"
    r"|IncreaseDecreaseIn|InterestPaid|InterestReceived|IncomeTaxesPaid|DividendsPaid"
    r"|AcquisitionOf|SaleOrIssueOf|RedemptionOf|Disposition|Subscription|StockDividends"
)
# 측정종류 토큰(이종 종류 혼합 탐지). account_id 표준명으로만.
_CLASS = [
    (
        "지분법",
        r"AccountedForUsingEquityMethod|InvestmentsInAssociates|InvestmentsInSubsidiaries|JointVentures",
    ),
    ("FVOCI", r"FairValueThroughOtherComprehensiveIncome"),
    ("FVPL", r"FairValueThroughProfitOrLoss|HeldForTrading"),
    ("상각후원가", r"AmortisedCost"),
    ("만기보유", r"HeldToMaturity"),
    ("매도가능", r"AvailableForSale"),
    ("파생", r"Derivative"),
]
_CLASS_RES = [(n, re.compile(p)) for n, p in _CLASS]


def stem(aid: str) -> str:
    for p in PREFIXES:
        if aid.startswith(p):
            return aid[len(p) :]
    return aid


def mclass(aid: str) -> str | None:
    s = stem(aid)
    for n, rx in _CLASS_RES:
        if rx.search(s):
            return n
    return None


def _cur_noncur(s: str) -> tuple[bool, bool]:
    """(is_current, is_noncurrent). 'CurrentPortionOf…Noncurrent…'는 당기상환예정분 → 유동으로 본다."""
    if "CurrentPortionOf" in s:
        return True, False
    return bool(CUR_RE.search(s)) and not bool(NONCUR_RE.search(s)), bool(NONCUR_RE.search(s))


def _is_combined(s: str) -> bool:
    """'TradeAndOther…' 통합. 단 '…ToTradeSuppliers/Customers'는 순수 매입/매출채권의 IFRS 정식명이라 제외."""
    return "AndOther" in s and "ToTradeSupplier" not in s and "ToTradeCustomer" not in s


def classify(aid: str, registered: set[str]) -> tuple[str, str]:
    """반환 (verdict, reason). verdict ∈ {등록누락, 오매핑, 수동확인}.
    오매핑 = 휴리스틱 후보(단정 아님). 표준명 실질로 등록ID와 비교.
    """
    a = stem(aid)
    reg_stems = {stem(x) for x in registered}
    if not registered:
        # alias-only canonical: 등록ID 없음 → 표준명 신호로만
        return "수동확인", "alias-only canonical(등록ID 없음) — 표준명 수동확인"
    if a in reg_stems:
        return "등록누락", "등록ID와 동일 stem(접두사만 차이) — 무해, 등록 추가 권장"
    # 유동/비유동 (CurrentPortionOf 보정)
    a_cur, a_noncur = _cur_noncur(a)
    reg_cn = [_cur_noncur(s) for s in reg_stems]
    reg_cur = any(c for c, _ in reg_cn)
    reg_noncur = any(nc for _, nc in reg_cn)
    if a_noncur and reg_cur and not reg_noncur:
        return "오매핑", "비유동 표준ID가 유동 canonical에 흡수"
    if a_cur and reg_noncur and not reg_cur:
        return "오매핑", "유동 표준ID가 비유동 canonical에 흡수"
    # 측정종류 불일치
    reg_classes = {mclass(x) for x in registered if mclass(x)}
    ac = mclass(aid)
    if ac and reg_classes and ac not in reg_classes:
        return "오매핑", f"이종 측정종류({ac}) ↔ 등록({sorted(reg_classes)})"
    # 통합(AndOther) vs 순수 (ToTradeSuppliers 보정)
    if _is_combined(a) != any(_is_combined(s) for s in reg_stems):
        return "오매핑", "통합(AndOther)↔순수 불일치"
    return "수동확인", "등록ID와 다른 표준개념 — 수동확인"


def won(x: float) -> str:
    return f"{x / 1e8:,.0f}억" if abs(x) >= 1e8 else f"{x / 1e8:,.2f}억"


def main() -> None:
    d = json.loads(IN.read_text(encoding="utf-8"))
    cov = d["coverage"]
    accounts = load_canonical_accounts(CONFIG)
    reg_by_name: dict[str, set[str]] = {}
    for ac in accounts:
        reg_by_name.setdefault(ac.name, set()).update(ac.account_ids)

    rows = []
    for it in d["items"]:
        canon = it["canonical"]
        registered = reg_by_name.get(canon, set())
        verdict, reason = classify(it["account_id"], registered)
        rows.append(
            {
                **it,
                "verdict": verdict,
                "reason": reason,
                "registered": sorted(stem(x) for x in registered),
            }
        )

    mismap = [r for r in rows if r["verdict"] == "오매핑"]
    manual = [r for r in rows if r["verdict"] == "수동확인"]
    benign = [r for r in rows if r["verdict"] == "등록누락"]
    for g in (mismap, manual, benign):
        g.sort(key=lambda r: -r["n"])

    def rowcnt(g):
        return sum(r["n"] for r in g)

    L = []
    A = L.append
    A("# 오매핑 전수 감사 — 표준ID 보유 + 이름매핑 (ALIAS_MISMAP_AUDIT)")
    A("")
    A(
        "> 충돌 여부·분류사전과 무관한 전수. `mapping_status==ALIAS` 인데 `account_id`(IFRS 표준ID)가"
    )
    A(
        "> 비어있지 않은 행 = 표준ID가 어느 canonical에도 등록 안 돼 **이름(alias)으로 흡수**된 직접 증거."
    )
    A(
        "> 운영 statement 가드(`_apply_statement_guard`) 적용 후 측정. 분류는 config 등록ID와 표준명 실질 비교(자기참조 회피)."
    )
    A("> 재현: `data/backtest/_audit_alias_mapped.py` → `_audit_alias_mapped_report.py`.")
    A("")
    A("## 1. 전수 커버리지")
    A("")
    A(
        f"- 회사 {cov['companies']}사 전수, 전체 행 {cov['rows_total']:,}, 매핑된 행 {cov['mapped_rows']:,}."
    )
    A(
        f"- **표준ID 보유 + 이름매핑(오매핑/등록누락 후보) 행: {cov['alias_with_id_rows']:,}** "
        f"→ distinct (account_id, canonical) **{cov['distinct_id_canonical']}쌍**."
    )
    A(f"- 공백 account_id 이름매핑(표준ID 없어 불가피, 별도 분모): {cov['blank_alias_rows']:,}행.")
    A("- account_id EXACT 매핑(명시 등록, 신뢰)은 본 감사 대상 아님.")
    A("")
    A(
        f"분류 결과(쌍 기준): 오매핑 {len(mismap)} · 수동확인 {len(manual)} · 등록누락(무해) {len(benign)}."
    )
    A(
        f"분류 결과(행 기준): 오매핑 {rowcnt(mismap):,} · 수동확인 {rowcnt(manual):,} · 등록누락 {rowcnt(benign):,}."
    )
    A("")

    A("## 2. 오매핑 (이종개념이 이름으로 흡수) — 수정 후보")
    A("")
    A(
        "| canonical | 흡수된 표준ID(account_id) | 사유 | 등록ID(stem) | 행수 | 최대금액 | 예시 라벨 |"
    )
    A("|---|---|---|---|--:|--:|---|")
    for r in mismap:
        A(
            f"| {r['canonical']} | {stem(r['account_id'])} | {r['reason']} | "
            f"{', '.join(r['registered']) or '—'} | {r['n']} | {won(r['amax'])} | {', '.join(r['labels'][:2])} |"
        )
    A("")

    A("## 3. 수동확인 (등록ID 없음/판정보류)")
    A("")
    A("| canonical | 흡수된 표준ID | 사유 | 행수 | 최대금액 | 예시 라벨 |")
    A("|---|---|---|--:|--:|---|")
    for r in manual[:60]:
        A(
            f"| {r['canonical']} | {stem(r['account_id'])} | {r['reason']} | {r['n']} | {won(r['amax'])} | {', '.join(r['labels'][:2])} |"
        )
    if len(manual) > 60:
        A("")
        A(f"… 외 {len(manual) - 60}쌍 (전체는 _audit_alias_mapped.json).")
    A("")

    A("## 4. 등록누락·동일개념 (무해 — 등록 추가만 권장)")
    A("")
    A(
        f"동일 stem(접두사만 차이)인 표준ID {len(benign)}쌍, {rowcnt(benign):,}행. 같은 계정이라 소실 아님."
    )
    A("상위:")
    A("")
    A("| canonical | 미등록 표준ID | 행수 |")
    A("|---|---|--:|")
    for r in benign[:20]:
        A(f"| {r['canonical']} | {stem(r['account_id'])} | {r['n']} |")
    A("")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(
        f"오매핑={len(mismap)}쌍/{rowcnt(mismap):,}행 · 수동확인={len(manual)}쌍 · 등록누락={len(benign)}쌍 -> {OUT}"
    )
    print("\n[오매핑 상위 25]")
    for r in mismap[:25]:
        print(f"  {r['n']:>5}행 {r['canonical']:<16}{stem(r['account_id']):<52}{r['reason']}")


if __name__ == "__main__":
    main()
