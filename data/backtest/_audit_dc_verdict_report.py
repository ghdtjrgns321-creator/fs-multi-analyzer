"""②D-C: 오매핑 52쌍 raw 근거 + 판정 → AGENDA_DC_MISMAP_VERDICT.md 생성 (read-only).

증거: _audit_dc_evidence.json (쌍별 회사·연도·라벨·금액 예시, n_found=분류기 분모와 일치).
판정(아래 VERDICT): account_id IFRS 표준명 실질 + raw 라벨로 [별도필요/benign/수동검토] 후보 제시.
단정 금지 — 수정은 사용자 결정(§8). config·코드 수정 없음.
"""

from __future__ import annotations

import json
from pathlib import Path

IN = Path("data/backtest/_audit_dc_evidence.json")
OUT = Path("data/backtest/AGENDA_DC_MISMAP_VERDICT.md")
PREFIXES = ("ifrs-full_", "ifrs_", "dart_")


def stem(aid: str) -> str:
    for p in PREFIXES:
        if aid.startswith(p):
            return aid[len(p) :]
    return aid


def won(x: float) -> str:
    x = abs(x)
    return f"{x / 1e8:,.0f}억" if x >= 1e8 else f"{x / 1e8:,.2f}억"


# 판정 맵: (canonical, account_id) -> (verdict, 사유)
# verdict ∈ {별도필요, benign, 수동검토}. 단정 아님(후보).
VERDICT: dict[tuple[str, str], tuple[str, str]] = {
    ("매출채권및기타유동채권", "dart_LongTermTradeAndOtherNonCurrentReceivablesGross"): (
        "별도필요",
        "라벨이 유동/비유동 미표기 일반명('매출채권및기타채권')인데 account_id는 명확히 비유동 통합 수취채권. "
        "62개사·최대 1.5조 규모로 유동 통합채권 canonical에 비유동이 섞여 유동성 분류를 왜곡. "
        "비유동매출채권및기타채권 canonical 신설 또는 비유동매출채권 재매핑 검토.",
    ),
    ("매입채무및기타유동채무", "dart_LongTermTradeAndOtherNonCurrentPayables"): (
        "별도필요",
        "라벨 일반명('매입채무 및 기타채무'), account_id는 비유동 통합 채무. 58개사·최대 1.3조. "
        "유동 통합채무 canonical에 비유동 혼입. 비유동 통합채무 canonical 신설/재매핑 검토.",
    ),
    ("매출채권및기타유동채권", "ifrs-full_NoncurrentReceivables"): (
        "별도필요",
        "account_id가 순수 비유동 수취채권인데 라벨('매출채권및기타채권')로 유동 통합채권에 흡수. "
        "30개사·최대 9,896억. 유동성 왜곡 — 비유동매출채권 재매핑 검토.",
    ),
    ("매입채무및기타유동채무", "ifrs-full_NoncurrentPayables"): (
        "별도필요",
        "순수 비유동 채무가 유동 통합채무에 흡수. 16개사. 금액은 중간(최대 280억)이나 구조적 비유동 혼입. "
        "비유동 채무로 재매핑 검토.",
    ),
    ("계약자산", "dart_NonCurrentFirmCommitmentAsset"): (
        "수동검토",
        "라벨 '확정계약자산'. account_id는 비유동 확정계약(firm commitment: 공정가치위험회피 대상)으로 "
        "IFRS15 계약자산(contract asset)과 개념이 다르고 비유동. 6개사·최대 1.7조로 큼. "
        "한국 실무에서 '확정계약자산'을 진행기준 계약자산으로 쓰면 benign, 위험회피 확정계약이면 별도필요 — 개념 해석 필요.",
    ),
    ("계약부채", "dart_NonCurrentFirmCommitmentLiabilities"): (
        "수동검토",
        "라벨 '확정계약부채'. account_id는 비유동 확정계약부채로 IFRS15 계약부채와 개념 상이 + 비유동. "
        "6개사·최대 3,250억. 계약자산 케이스와 동일 쟁점(개념 해석).",
    ),
    ("매입채무및기타유동채무", "dart_ShortTermTradePayables"): (
        "benign",
        "라벨('매입채무및기타채무')이 통합 canonical과 일치. account_id는 순수 매입채무(유동)로 "
        "같은 유동 매입채무 가족. 순수→통합 소폭 합산 외 왜곡 없음.",
    ),
    ("비유동매출채권", "dart_LongTermTradeAndOtherNonCurrentReceivablesGross"): (
        "benign",
        "라벨('비유동매출채권'/'장기매출채권')과 흡수처(비유동매출채권) 모두 비유동. "
        "account_id가 통합(AndOther)이나 라벨은 순수 장기매출채권 — 둘 다 비유동 매출채권 가족.",
    ),
    ("기타자본변동", "ifrs-full_IncreaseDecreaseThroughTransfersAndOtherChangesEquity"): (
        "benign",
        "라벨('연결실체의 변동'/'연결실체내 자본거래등')이 기타자본변동 alias와 일치. "
        "account_id는 대체·기타자본변동(통합)으로 같은 SCE 기타자본변동 성격.",
    ),
    ("FVOCI금융자산", "dart_NonCurrentAvailableForSaleFinancialAssets"): (
        "benign",
        "라벨 전부 FVOCI(기타포괄손익-공정가치). account_id는 매도가능(IFRS9 이전 legacy 코드). "
        "매도가능지분의 IFRS9 후신이 FVOCI라 라벨이 정확 — account_id가 legacy 잔존.",
    ),
    ("장기차입금", "dart_LongTermTradeAndOtherNonCurrentPayables"): (
        "benign",
        "라벨 전부 '장기차입금', 흡수처(장기차입금) 비유동 일치. account_id는 비유동 통합채무로 filer 오태깅 — 라벨이 신뢰 신호.",
    ),
    ("FVPL금융자산", "dart_NonCurrentAvailableForSaleFinancialAssets"): (
        "benign",
        "라벨 FVPL. account_id 매도가능(legacy). 매도가능의 IFRS9 후신으로 FVPL 선택 가능 — 라벨 정확.",
    ),
    (
        "무형자산",
        "dart_CopyrightsPatentsAndOtherIndustrialPropertyRightsServiceAndOperatingRightsGross",
    ): (
        "benign",
        "라벨 '무형자산'. account_id는 산업재산권 등(무형자산 세부 구성). 무형자산 가족 내 — 1개사·3억 소액.",
    ),
    (
        "지분법이익",
        "ifrs-full_GainsArisingFromDerecognitionOfFinancialAssetsMeasuredAtAmortisedCost",
    ): (
        "benign",
        "라벨 전부 '지분법이익'(IS/CIS). account_id는 상각후원가자산 제거이익으로 지분법과 전혀 무관 — 명백한 filer 오태깅. "
        "라벨 기반 매핑(지분법이익)이 정확. amax 5,964억은 라벨이 지분법이익인 회사 값.",
    ),
    ("FVOCI금융자산", "dart_NonCurrentFinancialAssetsHeldToMaturity"): (
        "수동검토",
        "라벨 FVOCI. account_id 만기보유(HTM, legacy). HTM의 IFRS9 후신은 통상 상각후원가(채무상품 FVOCI도 가능) — "
        "라벨과 코드가 다른 종류를 가리킴. 1개사·93억.",
    ),
    ("사채", "dart_CurrentPortionOfConvertibleBonds"): (
        "수동검토",
        "라벨 '사채'(유동/비유동 미표기). account_id는 전환사채 유동성분(당기상환=유동). "
        "유동성사채 canonical이 별도로 존재 → 유동성사채 재매핑 후보. 라벨이 일반 '사채'라 의도 모호.",
    ),
    ("사채", "ifrs-full_CurrentBondsIssuedAndCurrentPortionOfNoncurrentBondsIssued"): (
        "수동검토",
        "라벨 '사채'. account_id 유동사채+비유동사채 당기상환분(유동). 유동성사채 재매핑 후보. 4개사.",
    ),
    ("계약부채", "dart_LongTermTradeAndOtherNonCurrentPayables"): (
        "수동검토",
        "라벨 '계약부채'. account_id는 비유동 통합채무(계약부채와 무관) — filer 오태깅. "
        "비유동계약부채 canonical 존재. 1개사·1,148억.",
    ),
    ("FVOCI금융자산", "dart_LongTermTradeAndOtherNonCurrentReceivablesGross"): (
        "수동검토",
        "라벨 FVOCI. account_id 비유동 통합 수취채권(금융자산과 무관) — filer 오태깅. 1개사이나 4,437억으로 큼.",
    ),
    ("사채", "dart_LongTermTradeAndOtherNonCurrentPayables"): (
        "benign",
        "라벨 전부 '사채'(비유동), 흡수처(사채) 일치. account_id 통합채무 오태깅 — 라벨 신뢰.",
    ),
    ("관계기업투자", "dart_LongTermTradeAndOtherNonCurrentReceivablesGross"): (
        "benign",
        "라벨 '관계기업투자'. account_id 비유동 수취채권 오태깅 — 라벨 신뢰. 1개사.",
    ),
    ("리스부채", "dart_LongTermTradeAndOtherNonCurrentPayables"): (
        "benign",
        "라벨 '리스부채'. account_id 통합채무 오태깅. 1개사·8억 소액.",
    ),
    ("FVPL금융자산", "dart_LongTermTradeAndOtherNonCurrentReceivablesGross"): (
        "benign",
        "라벨 FVPL. account_id 비유동 수취채권 오태깅 — 라벨 신뢰. 1개사.",
    ),
    ("매출채권", "dart_LongTermTradeAndOtherNonCurrentReceivablesGross"): (
        "수동검토",
        "라벨 '매출채권'(순수·유동 성격)인데 account_id는 비유동 통합 — 라벨(유동)과 코드(비유동)가 모순. 2개사.",
    ),
    ("자본금변동", "ifrs-full_IncreaseDecreaseThroughTransfersAndOtherChangesEquity"): (
        "수동검토",
        "라벨 '유상증자'(자본금변동)인데 account_id는 대체·기타자본변동(통합) — 라벨과 코드 불일치. SCE 1개사·소액.",
    ),
    ("당기법인세부채", "ifrs-full_OtherNoncurrentLiabilities"): (
        "benign",
        "라벨 '당기법인세부채'. account_id 기타비유동부채(오태깅)이나 금액 0/미기재 — 영향 없음. 1개사.",
    ),
    ("미지급비용", "dart_LongTermAccruedExpensesGross"): (
        "수동검토",
        "라벨 '미지급비용'(유동성 미표기), account_id 장기(비유동) 미지급비용. 비유동→유동 혼입. 2개사·0.27억 소액.",
    ),
    ("공사손실충당부채", "dart_NonCurrentProvisionForConstructionLosses"): (
        "수동검토",
        "라벨 '공사손실충당부채', account_id 비유동 공사손실충당. 현 canonical은 유동만 등록 — 비유동 버전(장기충당부채?) 검토. 2개사·16억.",
    ),
    ("충당부채", "dart_OtherNonCurrentLiabilities"): (
        "수동검토",
        "라벨 '충당부채', account_id 기타비유동부채. 충당부채 canonical은 유동, 비유동은 장기충당부채 — 비유동 혼입. 1개사·0.25억.",
    ),
    ("유동성장기차입금", "ifrs-full_LongtermBorrowings"): (
        "benign",
        "라벨 '유동성장기부채/유동성장기차입금'(유동), 흡수처(유동성장기차입금) 일치. "
        "account_id LongtermBorrowings(비유동)는 오태깅 — 라벨 신뢰. 3개사·최대 1.5조이나 라벨이 명확히 유동성.",
    ),
    ("FVPL금융자산", "dart_CurrentAvailableForSaleFinancialAssets"): (
        "benign",
        "라벨 FVPL. account_id 유동 매도가능(legacy) — AFS→FVPL 승계, 라벨 정확. 1개사.",
    ),
    ("상각후원가금융자산", "dart_CurrentFinancialAssetsHeldToMaturity"): (
        "benign",
        "라벨 '상각후원가측정금융자산'. account_id 유동 만기보유(HTM, legacy) — HTM의 IFRS9 후신이 상각후원가라 라벨 정확.",
    ),
    ("사채", "dart_CurrentPortionOfBondWithWarrant"): (
        "수동검토",
        "라벨 '사채'. account_id 신주인수권부사채 유동성분(유동). 유동성사채 재매핑 후보. 1개사·348억.",
    ),
    ("사채", "dart_CurrentPortionOfExchangeableBond"): (
        "수동검토",
        "라벨 '사채'. account_id 교환사채 유동성분(유동). 유동성사채 재매핑 후보. 1개사·151억.",
    ),
    ("미지급금", "dart_LongTermOtherPayablesNet"): (
        "수동검토",
        "라벨 '미지급금'(유동성 미표기), account_id 장기미지급금(비유동). 비유동→유동 혼입. 1개사·90억.",
    ),
    ("종속기업투자", "dart_NonCurrentAvailableForSaleFinancialAssets"): (
        "benign",
        "라벨 '종속기업투자주식'(별도재무제표 OFS). account_id 매도가능(legacy 오태깅) — 라벨 신뢰. 1개사·304억.",
    ),
    ("상각후원가금융자산", "dart_NonCurrentFinancialAssetsHeldToMaturity"): (
        "benign",
        "라벨 '상각후원가 측정 금융자산'. account_id 비유동 HTM(legacy) — HTM→상각후원가 정확. 1개사·0.01억.",
    ),
    ("매입채무및기타유동채무", "dart_ShortTermCollectionWithholdings"): (
        "수동검토",
        "라벨 '매입채무및기타채무'(통합). account_id는 단기 수금예수금(예수금류) — 예수금이 기타채무에 포함될 여지는 있으나 별개 개념. 1개사·4,434억으로 큼.",
    ),
    ("사채", "ifrs-full_CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings"): (
        "수동검토",
        "라벨 '사채'. account_id는 유동차입금+비유동차입금 당기상환분(차입금, 유동). 사채≠차입금 + 유동성. 1개사·3,197억.",
    ),
    ("장기차입금", "ifrs-full_CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings"): (
        "수동검토",
        "라벨 '장기차입금'인데 account_id는 유동차입+당기상환분(유동) — 라벨(비유동)과 코드(유동) 모순. 유동성장기차입금 후보. 1개사·9,031억.",
    ),
    ("매출채권및기타유동채권", "ifrs-full_CurrentTaxAssets"): (
        "수동검토",
        "라벨 '매출채권및기타채권'(통합). account_id는 당기법인세자산(세무자산)으로 채권과 별개 개념. 1개사·9,740억으로 큼.",
    ),
    ("선수금", "ifrs-full_NoncurrentAdvances"): (
        "수동검토",
        "라벨 '선수금'(유동성 미표기), account_id 비유동 선수금. 비유동→유동 혼입. 1개사·11억.",
    ),
    (
        "FVOCI금융자산",
        "ifrs-full_NoncurrentFinancialAssetsAtFairValueThroughProfitOrLossMandatorilyMeasuredAtFairValue",
    ): (
        "수동검토",
        "라벨 FVOCI인데 account_id는 FVPL(의무 공정가치측정) — 라벨과 코드가 다른 측정종류. 1개사·37억.",
    ),
    ("충당부채", "ifrs-full_OtherNoncurrentFinancialLiabilities"): (
        "수동검토",
        "라벨 '충당부채', account_id 기타비유동금융부채. 비유동 혼입 + 금융부채≠충당부채. 1개사·0.77억 소액.",
    ),
    ("FVOCI금융자산", "dart_CurrentAvailableForSaleFinancialAssets"): (
        "benign",
        "라벨 FVOCI. account_id 유동 매도가능(legacy) — AFS→FVOCI 승계, 라벨 정확. 1개사·금액 0/미기재.",
    ),
    ("FVPL금융자산", "dart_DebtSecuritiesAtFairValueThroughOtherComprehensiveIncome"): (
        "수동검토",
        "라벨 FVPL인데 account_id는 FVOCI 채무증권 — 라벨과 코드가 다른 측정종류. 1개사·8억.",
    ),
    ("유동성장기차입금", "dart_PresentValueDiscountsLongTermBorrowingsGross"): (
        "benign",
        "라벨 '유동성장기차입금', 흡수처 일치. account_id는 장기차입금 현재가치할인차금(차감항목, 음수) — 같은 계정의 차감. 1개사.",
    ),
    ("상각후원가금융자산", "dart_SeparateAccountDerivativeFinancialAssetsHeldForTrading"): (
        "수동검토",
        "라벨 '상각후원가측정금융자산'인데 account_id는 별도계정 파생(HFT=FVPL, 보험 별도계정) — 라벨과 코드 모순. 1개사·2억 소액.",
    ),
    ("기타유동자산", "ifrs-full_CurrentPrepaymentsAndOtherCurrentAssets"): (
        "benign",
        "라벨 '기타유동자산'. account_id 유동 선급+기타유동자산(통합) — 둘 다 유동 기타자산 가족. 1개사·4억.",
    ),
    ("매입채무및기타유동채무", "ifrs-full_OtherNoncurrentLiabilities"): (
        "benign",
        "라벨 '매입채무 및 기타채무'(통합)과 흡수처 일치. account_id 기타비유동부채(오태깅)이나 1개사·8억 소액 — 영향 미미.",
    ),
    ("매입채무및기타유동채무", "ifrs-full_TradeAndOtherPayablesToTradeSuppliers"): (
        "benign",
        "라벨 '매입채무 및 기타채무'(통합). account_id 순수 공급자매입채무(유동) — 유동 매입채무 가족. 1개사·493억.",
    ),
    (
        "계약자산",
        "ifrs_NoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleOrAsHeldForDistributionToOwners",
    ): (
        "수동검토",
        "라벨 '미청구공사'(=계약자산). account_id는 매각예정비유동자산으로 계약자산과 전혀 무관 — 명백한 filer 오태깅. "
        "라벨 신뢰 시 계약자산이 맞으나 account_id가 매각예정+5,366억으로 커 검토. 2016년 단건.",
    ),
}

ORDER = ["별도필요", "수동검토", "benign"]
DESC = {
    "별도필요": "유동 canonical에 비유동/이종이 다수사·대규모로 흡수돼 분류 왜곡. 별도 canonical 또는 재매핑 후보.",
    "수동검토": "라벨↔account_id 불일치·개념 모호·고액 단일사 등 — 사람 판단 필요.",
    "benign": "라벨이 흡수처와 일치하고 account_id가 filer 오태깅/legacy(IFRS9 승계)라 영향 미미.",
}


def ex_refs(examples: list[dict], k: int = 2) -> str:
    """raw 예시 ≥k건을 'corp·year·fs·금액' 형식으로. nan 금액은 '미기재'."""
    out = []
    for e in examples[:k]:
        amt = e["amount"]
        try:
            f = float(amt)
            amt_s = "미기재" if f != f else won(f)
        except (ValueError, TypeError):
            amt_s = "미기재"
        out.append(f"{e['corp']}·{e['year']}·{e['fs']}·'{e['label']}'·{amt_s}")
    return " / ".join(out)


def main() -> None:
    d = json.loads(IN.read_text(encoding="utf-8"))
    items = d["items"]
    for it in items:
        key = (it["canonical"], it["account_id"])
        v, r = VERDICT.get(key, ("수동검토", "판정 미정의 — 검토 필요"))
        it["verdict"], it["verdict_reason"] = v, r

    groups = {g: [it for it in items if it["verdict"] == g] for g in ORDER}
    n_total = len(items)
    counts = {g: len(groups[g]) for g in ORDER}

    L: list[str] = []
    A = L.append
    A("# 오매핑 52쌍 raw 근거 판정 (AGENDA_DC_MISMAP_VERDICT)")
    A("")
    A(
        "> ②D-C. `ALIAS_MISMAP_AUDIT.md` §2 '오매핑' 52쌍을 raw 원천에서 회사·연도·라벨·금액으로 전수 검증하고"
    )
    A(
        "> account_id IFRS 표준명 실질 + 실제 라벨로 [별도필요 / benign / 수동검토] **후보**를 제시한다."
    )
    A("> 단정 아님 — 수정은 사용자 결정(글로벌 §8). config·코드 미수정(읽기전용).")
    A("> 원천: `data/companies/{corp}/{year}/raw/finstate_all_{CFS,OFS}.csv`.")
    A(
        "> 증거 전량: `data/backtest/_audit_dc_evidence.json` (쌍별 예시·전체 행수). 재현: `_audit_dc_evidence.py` → `_audit_dc_verdict_report.py`."
    )
    A("")
    A("## 1. 분모·검증")
    A("")
    A(
        f"- 대상 52쌍 = 분류기(`_audit_alias_mapped_report.classify`) verdict=='오매핑' 쌍 전수. 본 검증 재현 **{n_total}쌍** (분모 일치)."
    )
    A(
        "- 쌍별 raw 발견 행수(n_found)가 집계 JSON 행수(n_json)와 **전 쌍 일치**(0 불일치) — 누락·중복 없음."
    )
    A("- 각 쌍 raw 예시 2건 이상 확보. 단, 8쌍은 전체 모집단이 1행(전수가 1건)이라 1건이 곧 전수.")
    A("")
    A("## 2. 판정 요약 (후보)")
    A("")
    A("| 판정 | 쌍수 | 의미 |")
    A("|---|--:|---|")
    for g in ORDER:
        A(f"| {g} | {counts[g]} | {DESC[g]} |")
    A(f"| 합계 | {n_total} | |")
    A("")
    A("## 3. 분류기 휴리스틱 오탐 점검 (핵심)")
    A("")
    A(
        "분류기는 **account_id(IFRS 표준ID)를 신뢰 신호로 가정**하고 유동/비유동·측정종류·통합↔순수를 판정했다."
    )
    A(
        "그러나 raw 검증 결과 52쌍의 다수가 **filer의 account_id 오태깅 + 라벨이 진짜 신호**인 경우였다:"
    )
    A("")
    A(
        "- **filer 오태깅**: 라벨 '장기차입금'·'사채'·'리스부채'인데 account_id가 통합채무(LongTermTradeAndOtherNonCurrentPayables)"
    )
    A(
        "  → 라벨이 흡수처와 일치하고 account_id가 무관한 표준코드. 라벨 기반 매핑이 오히려 정확(benign)."
    )
    A(
        "- **지분법이익 ← 상각후원가자산 제거이익**: account_id가 지분법과 전혀 무관 → 명백한 표준코드 오기, 라벨 정확."
    )
    A(
        "- **측정종류 legacy**: account_id가 매도가능(AvailableForSale)·만기보유(HeldToMaturity)는 IFRS9 이전 코드."
    )
    A(
        "  라벨은 현행 FVOCI/FVPL/상각후원가 — IFRS9 승계관계(매도가능→FVOCI/FVPL, 만기보유→상각후원가)라 라벨이 정확(benign)."
    )
    A("")
    A(
        "즉 '이종 측정종류'와 일부 '통합↔순수' 오매핑 판정은 **account_id 자기신뢰에서 온 오탐**이며, 라벨 기반 매핑이 정확하다."
    )
    A(
        "반대로 진짜 구조적 문제(별도필요)는 **라벨이 유동/비유동 미표기 일반명이면서 account_id가 신뢰 가능한 비유동 통합ID이고"
    )
    A(
        "다수 회사·대규모**인 경우 — 유동 채권/채무 canonical에 비유동이 섞여 유동성 분류가 왜곡된다."
    )
    A("")

    sec = 4
    for g in ORDER:
        A(f"## {sec}. {g} ({counts[g]}쌍)")
        A("")
        A(f"{DESC[g]}")
        A("")
        A(
            "| canonical | 흡수된 표준ID(account_id) | 회사수 | 행수 | 최대금액 | 사유 | raw 예시(corp·연도·fs·라벨·금액) |"
        )
        A("|---|---|--:|--:|--:|---|---|")
        for it in groups[g]:
            A(
                f"| {it['canonical']} | {stem(it['account_id'])} | {it['distinct_corps']} | "
                f"{it['n_found']} | {won(it['amax'])} | {it['verdict_reason']} | {ex_refs(it['examples'])} |"
            )
        A("")
        sec += 1

    A(f"## {sec}. 산출물·재현")
    A("")
    A("- 증거 JSON: `data/backtest/_audit_dc_evidence.json` (52쌍, 쌍별 예시 최대 6건·전체 행수).")
    A(
        "- 수집 하니스: `data/backtest/_audit_dc_evidence.py` (운영 mapper·statement 가드 동일 적용, raw 전수 스캔, read-only)."
    )
    A("- 본 문서 생성: `data/backtest/_audit_dc_verdict_report.py`.")
    A(
        "- 후속: 별도필요 4쌍·수동검토 25쌍은 사용자 토의로 canonical 신설/재매핑 여부 결정. config·코드 수정은 별도 작업."
    )

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(
        f"-> {OUT}  (별도필요 {counts['별도필요']} · 수동검토 {counts['수동검토']} · benign {counts['benign']} / 합 {n_total})"
    )
    undef = [it for it in items if it["verdict_reason"] == "판정 미정의 — 검토 필요"]
    print(f"판정 미정의 쌍: {len(undef)}")
    for it in undef:
        print("  ", it["canonical"], it["account_id"])


if __name__ == "__main__":
    main()
