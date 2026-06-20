"""_merge_audit_full.json 을 읽어 동질/이질을 account_id IFRS 표준명 실질로 분류하고
data/backtest/MERGE_AUDIT.md 를 생성한다.

자기참조 금지(§10): 분류는 현재 canonical/alias 매핑을 보지 않고, account_id 표준ID 문자열
자체의 회계 실질(접두사·세전세후·잔액vs흐름·유동vs비유동·종속vs관계·순수vs기타포함)로만 판정한다.
∅ = '-표준계정코드 미사용-'(account_id 공백). 표준명이 없어 실질 판정 불가 → 별도 취급.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

IN_JSON = Path("data/backtest/_merge_audit_full.json")
OUT_MD = Path("data/backtest/MERGE_AUDIT.md")
PREFIXES = ("ifrs-full_", "ifrs_", "dart_")
# account_id 공백 = OpenDART가 표준ID 대신 넣는 placeholder. 표준명이 없어 실질 판정 불가 → 동질 prefix 버킷.
BLANK_TOKENS = {"∅", "-표준계정코드 미사용-", ""}

# CF/흐름 조정·증감 표준명 패턴 (잔액이 아니라 '흐름·증감').
# 주의: 'CashFlows'(=ForStatementOfCashFlows 표문변형)는 흐름조정이 아니므로 제외 — 아래 PRESENT_RE로 먼저 제거.
FLOW_RE = re.compile(
    r"AdjustmentsFor|ProceedsFrom|PurchaseOf|PaymentsOf|PaymentsFor|RepaymentsOf"
    r"|IncreaseDecreaseIn|InterestPaid|InterestReceived|IncomeTaxesPaid|DividendsPaid"
    r"|AcquisitionOf|SaleOrIssueOf|RedemptionOf"
)
# 표문 표시 접미사(같은 계정의 BS·CF·SCE 반복) — 흐름조정 아님(의뢰서 동질제외).
PRESENT_RE = re.compile(r"(ForStatementOfCashFlows|ForStatementOfChangesInEquity)$")
CUR_RE = re.compile(r"(?<!Non)(?<!non)Current|Shortterm|ShortTerm")
NONCUR_RE = re.compile(r"Noncurrent|NonCurrent|noncurrent|Longterm|LongTerm")
TRADE_NOUNS = ("Receivable", "Payable")


def stem(aid: str) -> str:
    for p in PREFIXES:
        if aid.startswith(p):
            return aid[len(p) :]
    return aid


def detax(s: str) -> str:
    return re.sub(r"(NetOfTax|BeforeTax|AfterTax)$", "", s)


def core_stem(aid: str) -> str:
    """동질 판정용 핵심 stem: prefix·표문접미사·세전세후 제거 후 남는 회계개념."""
    return detax(PRESENT_RE.sub("", stem(aid)))


# 측정종류(회계 분류) 토큰: 같은 칸에 종류가 다르면 이종 혼합(유동/비유동과 무관한 본질 차이).
# 우선순위 순서대로 첫 매칭 반환. 자기참조 금지: canonical이 아니라 account_id 표준명으로만 판정.
_CLASS_PATTERNS = [
    (
        "지분법",
        r"AccountedForUsingEquityMethod|InvestmentsInAssociates|InvestmentsInSubsidiaries|JointVentures",
    ),
    ("FVOCI", r"FairValueThroughOtherComprehensiveIncome"),
    ("FVPL", r"FairValueThroughProfitOrLoss|FinancialAssetHeldForTrading|HeldForTrading"),
    ("상각후원가", r"AmortisedCost"),
    ("만기보유", r"HeldToMaturity"),
    ("매도가능", r"AvailableForSale"),
    ("파생", r"Derivative"),
    ("예금", r"Deposits"),
    ("리스", r"Lease"),
    ("사채", r"Bond"),
    ("차입", r"Borrowing"),
    ("충당", r"Provision"),
    ("투자부동산", r"InvestmentProperty"),
    ("계약자산", r"ContractAsset|DueFromCustomers|FirmCommitmentAsset"),
    ("계약부채", r"ContractLiabilit|DueToCustomers|FirmCommitmentLiabilit|IncomeReceivedInAdvance"),
    ("매출채권", r"TradeReceivable|TradeAndOther\w*Receivable"),
    ("매입채무", r"TradePayable|TradeAndOther\w*Payable"),
    ("재고", r"Inventor"),
]
_CLASS_RES = [(name, re.compile(pat)) for name, pat in _CLASS_PATTERNS]


def measurement_class(aid: str) -> str | None:
    """account_id 표준명에서 회계 측정종류를 추출. 분류 불가는 None."""
    s = stem(aid)
    for name, rx in _CLASS_RES:
        if rx.search(s):
            return name
    return None


def classify(ids: list[str]) -> tuple[str, str, str]:
    """반환: (verdict, category, 근거). verdict ∈ {동질, 이질, 의심}.

    자기참조 금지: 현 매핑이 아니라 account_id 표준명 실질로만 판정.
    """
    real = [i for i in ids if i not in BLANK_TOKENS]
    has_blank = any(i in BLANK_TOKENS for i in ids)
    stems = [core_stem(i) for i in real]
    uniq = sorted(set(stems))

    if len(uniq) <= 1:
        # 핵심 stem이 1개뿐 → prefix/표문접미사 차이뿐(같은 계정의 BS·CF·SCE 반복).
        if has_blank:
            return (
                "동질",
                "공백+동일개념",
                "∅(미표준) + 동일 표준개념 1종 — 표문 반복/별도표 미표준ID",
            )
        return "동질", "prefix/표문차", "동일 핵심개념, 접두사·표문접미사(ForStatementOf…)만 상이"

    # 세전/세후만 다른가
    if len({detax(s) for s in uniq}) == 1:
        return "동질", "세전세후", "동일개념의 BeforeTax/NetOfTax 변형"

    flow = [s for s in uniq if FLOW_RE.search(s)]
    nonflow = [s for s in uniq if not FLOW_RE.search(s)]
    if flow and nonflow:
        return (
            "이질",
            "잔액vs흐름조정",
            f"흐름·증감({','.join(flow)}) vs 잔액({','.join(nonflow)}) — sj_div 키 부재 충돌",
        )

    subs = [s for s in uniq if s == "InvestmentsInSubsidiaries"]
    assoc = [s for s in uniq if "Associat" in s or "EquityMethod" in s or "JointVentures" in s]
    if subs and assoc:
        return "이질", "종속vs관계", f"지배(종속:{subs}) vs 유의적영향(관계:{assoc})"

    # 이종 측정종류 혼합: 한 칸에 회계 종류가 다른 계정(매도가능↔FVPL, 예금↔FVPL 등)이 섞임.
    # 유동/비유동보다 우선 — 유동/비유동으로 묶이면 본질 차이(종류)가 묻힌다.
    classes = {measurement_class(i) for i in real}
    classes.discard(None)
    if len(classes) >= 2:
        return "이질", "이종클래스혼합", f"측정종류 혼합: {sorted(classes)}"

    cur = [s for s in uniq if CUR_RE.search(s) and not NONCUR_RE.search(s)]
    noncur = [s for s in uniq if NONCUR_RE.search(s)]
    if cur and noncur:
        return "이질", "유동vs비유동", f"유동({cur}) vs 비유동({noncur})"

    # 순수 vs 기타포함 통합: 공유 핵심명사(Receivable/Payable)를 가진 두 ID 중
    # 하나만 'AndOther'(기타채권/채무 포함) → 순수계정이 통합라벨에 흡수(케이스 A).
    for noun in TRADE_NOUNS:
        withn = [s for s in uniq if noun.lower() in s.lower()]
        if len(withn) >= 2:
            ands = [s for s in withn if "AndOther" in s]
            pures = [s for s in withn if "AndOther" not in s]
            if ands and pures:
                return "이질", "순수vs기타포함", f"통합({ands}) vs 순수({pures})"

    return "의심", "기타이질", f"서로 다른 표준개념 {uniq} — 수동 확인 필요"


def short(ids: list[str]) -> list[str]:
    return [stem(i) for i in ids]


def won(x: float) -> str:
    return f"{x / 1e8:,.0f}억" if abs(x) >= 1e8 else f"{x / 1e8:,.2f}억"


def severity(cat: str) -> str:
    """심각도: 같은 BS 칸 내 실질 소실=상, 표문 간(잔액 우선보존)=중, 그외=하."""
    if cat in ("순수vs기타포함", "유동vs비유동", "종속vs관계"):
        return "상"  # BS 내 별도 실질계정이 통합/유동·비유동에 흡수 → 소실
    if cat == "잔액vs흐름조정":
        return "중"  # 잔액(BS/IS) vs 흐름(CF/SCE) — canonical_statement 우선보존되나 타표문 소실
    return "하"


def main() -> None:
    d = json.loads(IN_JSON.read_text(encoding="utf-8"))
    cov = d["coverage"]
    canons = d["canonicals"]

    # 분류 결과 평탄화
    rows = []  # (canon, verdict, category, ids, n, drop_sum, drop_max, kept, ex, 근거)
    for cv, info in canons.items():
        for c in info["combos"]:
            verdict, cat, why = classify(c["ids"])
            rows.append(
                {
                    "canon": cv,
                    "verdict": verdict,
                    "cat": cat,
                    "why": why,
                    "ids": c["ids"],
                    "n": c["n"],
                    "drop_sum": c["drop_sum"],
                    "drop_max": c["drop_max"],
                    "kept": c["kept"],
                    "ex": c["examples"][0],
                    "groups": info["collision_groups"],
                    "examined": info["groups_examined"],
                }
            )

    hetero = [r for r in rows if r["verdict"] == "이질"]
    suspect = [r for r in rows if r["verdict"] == "의심"]
    homo = [r for r in rows if r["verdict"] == "동질"]
    hetero.sort(key=lambda r: -r["drop_sum"])
    suspect.sort(key=lambda r: -r["drop_sum"])

    def ex_line(r: dict) -> str:
        ex = r["ex"]
        parts = []
        for k, v in ex["ids"].items():
            mark = "←keep" if k == ex["kept"] else "drop"
            parts.append(f"{stem(k)}({v['sj']},{won(v['amt'])},{mark})")
        return f"{ex['corp']}·{ex['year']}·{ex['fs']}: " + " vs ".join(parts)

    L = []
    A = L.append
    A("# canonical 이질계정 병합 전수 감사 결과 (MERGE_AUDIT)")
    A("")
    A("> 운영코드(`AccountMapper.map_row`·`_dedupe_statement_rows`·`_dedupe_canonical_rows`·")
    A(
        "> `_canonical_score`)를 실제 호출해 계측. 이질 판정은 account_id IFRS 표준명 실질로만(자기참조 금지)."
    )
    A("> 재현: `data/backtest/_merge_audit_full.py`(수집)→`_merge_audit_classify.py`(분류).")
    A("")
    A("## 1. 전수 커버리지 (수치 증명)")
    A("")
    A(
        f"- 수집 회사: **{cov['companies_total']}사 전부 순회**, 데이터 보유 {cov['companies_with_data']}사."
    )
    A(f"- 검사 회사-연도: {cov['company_years']}, 읽은 raw 파일(CFS+OFS): **{cov['files_read']}**.")
    fail = cov["files_failed"]
    if fail:
        A(
            f"- [~] 파싱 실패 파일 {fail}건 — 스키마 검증(`validate_raw_frame`) 탈락분. 전수 분모에서 제외(조용한 축소 아님, 수치 명시)."
        )
    else:
        A("- 파싱 실패 파일 0건.")
    A(f"- 충돌(2+ distinct account_id) 발생 canonical: **{len({r['canon'] for r in rows})}종**.")
    A(f"- 이질 조합 {len(hetero)} · 의심(수동확인) {len(suspect)} · 동질(노이즈) {len(homo)}.")
    A(
        f"- 참고: `data/companies/` 하위 디렉터리 1668개 중 1개는 placeholder(`NO_SUCH_CORP`) → "
        f"실제 corp_code 디렉터리 {cov['companies_total']}개를 전수 순회."
    )
    A("")
    A(
        "판정 기준: account_id 표준명 실질. 동질=prefix/표문차·세전세후·공백+동일개념. "
        "이질=잔액vs흐름조정·종속vs관계·유동vs비유동·순수vs기타포함·기타."
    )
    A("")
    A(
        "> 금액 주의: `drop합`·`drop최대`는 원천 `thstrm_amount` **절대값** 집계다(순손실 아님). "
        "원천 DART 필링의 스케일 이상치(예: corp 00204226의 2022 자산총계 122,130조 등)가 일부 합계를 "
        "과대계상한다. **이질 판정은 distinct account_id 충돌 여부이며 금액과 무관**하므로 결론에 영향 없다."
    )
    A("")

    A("## 2. 이질병합표 (확정 이질)")
    A("")
    A(
        "| canonical | 유형 | 심각도 | 동시출현 표준ID | keep | drop | 충돌그룹수 | drop합 | drop최대 | 실데이터 예시 |"
    )
    A("|---|---|:--:|---|---|---|--:|--:|--:|---|")
    for r in hetero:
        keptid = max(r["kept"], key=r["kept"].get) if r["kept"] else ""
        dropped = [stem(i) for i in r["ids"] if i != keptid]
        A(
            f"| {r['canon']} | {r['cat']} | {severity(r['cat'])} | {' + '.join(short(r['ids']))} | {stem(keptid)} "
            f"| {','.join(dropped)} | {r['n']} | {won(r['drop_sum'])} | {won(r['drop_max'])} | {ex_line(r)} |"
        )
    A("")

    A("## 3. 의심(수동확인 필요)")
    A("")
    if suspect:
        A("| canonical | 동시출현 표준ID | 충돌그룹수 | drop합 | 근거 | 예시 |")
        A("|---|---|--:|--:|---|---|")
        for r in suspect:
            A(
                f"| {r['canon']} | {' + '.join(short(r['ids']))} | {r['n']} | {won(r['drop_sum'])} | {r['why']} | {ex_line(r)} |"
            )
    else:
        A("없음.")
    A("")

    A("## 4. 신규 발견 (기지 A/B/C·종속관계 외)")
    A("")
    known = {"매출채권", "매입채무", "재고자산", "충당부채", "관계기업투자", "종속기업투자"}
    new_h = [r for r in hetero if r["canon"] not in known]
    if new_h:
        seen = set()
        for r in new_h:
            if r["canon"] in seen:
                continue
            seen.add(r["canon"])
            A(
                f"- **{r['canon']}** ({r['cat']}): {' + '.join(short(r['ids']))} — {r['why']}. 예) {ex_line(r)}"
            )
    else:
        A("기지 유형 외 신규 이질 canonical 없음.")
    A("")

    A("## 5. 동질(노이즈) 요약 — 빈 PASS 아님")
    A("")
    A(
        f"동질로 분류해 제외한 조합 {len(homo)}건. 분모: 충돌 canonical {len({r['canon'] for r in homo})}종."
    )
    A("사유 분포:")
    from collections import Counter

    cc = Counter(r["cat"] for r in homo)
    for cat, n in cc.most_common():
        A(f"- {cat}: {n}건")
    A("")
    A("## 6. 충돌 없던 canonical (분모 기록)")
    A("")
    nocol = d.get("canonicals_no_collision", {})
    A(f"충돌 0건 canonical {len(nocol)}종(각 검사그룹수>0). 단일 account_id만 출현 → 소실 없음.")
    A(
        "예: "
        + ", ".join(f"{k}({v})" for k, v in list(sorted(nocol.items(), key=lambda x: -x[1]))[:15])
    )
    A("")

    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"hetero={len(hetero)} suspect={len(suspect)} homo={len(homo)} -> {OUT_MD}")
    print("\n[이질 상위]")
    for r in hetero[:25]:
        print(
            f"  {r['canon']:<16}{r['cat']:<14}{r['n']:>4}grp {won(r['drop_sum']):>10}  {' + '.join(short(r['ids']))}"
        )
    print("\n[의심]")
    for r in suspect[:25]:
        print(f"  {r['canon']:<16}{r['n']:>4}grp  {' + '.join(short(r['ids']))}")


if __name__ == "__main__":
    main()
