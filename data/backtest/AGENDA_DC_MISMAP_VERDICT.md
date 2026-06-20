# 오매핑 52쌍 raw 근거 판정 (AGENDA_DC_MISMAP_VERDICT)

> ②D-C. `ALIAS_MISMAP_AUDIT.md` §2 '오매핑' 52쌍을 raw 원천에서 회사·연도·라벨·금액으로 전수 검증하고
> account_id IFRS 표준명 실질 + 실제 라벨로 [별도필요 / benign / 수동검토] **후보**를 제시한다.
> 단정 아님 — 수정은 사용자 결정(글로벌 §8). config·코드 미수정(읽기전용).
> 원천: `data/companies/{corp}/{year}/raw/finstate_all_{CFS,OFS}.csv`.
> 증거 전량: `data/backtest/_audit_dc_evidence.json` (쌍별 예시·전체 행수). 재현: `_audit_dc_evidence.py` → `_audit_dc_verdict_report.py`.

## 1. 분모·검증

- 대상 52쌍 = 분류기(`_audit_alias_mapped_report.classify`) verdict=='오매핑' 쌍 전수. 본 검증 재현 **52쌍** (분모 일치).
- 쌍별 raw 발견 행수(n_found)가 집계 JSON 행수(n_json)와 **전 쌍 일치**(0 불일치) — 누락·중복 없음.
- 각 쌍 raw 예시 2건 이상 확보. 단, 8쌍은 전체 모집단이 1행(전수가 1건)이라 1건이 곧 전수.

## 2. 판정 요약 (후보)

| 판정 | 쌍수 | 의미 |
|---|--:|---|
| 별도필요 | 4 | 유동 canonical에 비유동/이종이 다수사·대규모로 흡수돼 분류 왜곡. 별도 canonical 또는 재매핑 후보. |
| 수동검토 | 25 | 라벨↔account_id 불일치·개념 모호·고액 단일사 등 — 사람 판단 필요. |
| benign | 23 | 라벨이 흡수처와 일치하고 account_id가 filer 오태깅/legacy(IFRS9 승계)라 영향 미미. |
| 합계 | 52 | |

## 3. 분류기 휴리스틱 오탐 점검 (핵심)

분류기는 **account_id(IFRS 표준ID)를 신뢰 신호로 가정**하고 유동/비유동·측정종류·통합↔순수를 판정했다.
그러나 raw 검증 결과 52쌍의 다수가 **filer의 account_id 오태깅 + 라벨이 진짜 신호**인 경우였다:

- **filer 오태깅**: 라벨 '장기차입금'·'사채'·'리스부채'인데 account_id가 통합채무(LongTermTradeAndOtherNonCurrentPayables)
  → 라벨이 흡수처와 일치하고 account_id가 무관한 표준코드. 라벨 기반 매핑이 오히려 정확(benign).
- **지분법이익 ← 상각후원가자산 제거이익**: account_id가 지분법과 전혀 무관 → 명백한 표준코드 오기, 라벨 정확.
- **측정종류 legacy**: account_id가 매도가능(AvailableForSale)·만기보유(HeldToMaturity)는 IFRS9 이전 코드.
  라벨은 현행 FVOCI/FVPL/상각후원가 — IFRS9 승계관계(매도가능→FVOCI/FVPL, 만기보유→상각후원가)라 라벨이 정확(benign).

즉 '이종 측정종류'와 일부 '통합↔순수' 오매핑 판정은 **account_id 자기신뢰에서 온 오탐**이며, 라벨 기반 매핑이 정확하다.
반대로 진짜 구조적 문제(별도필요)는 **라벨이 유동/비유동 미표기 일반명이면서 account_id가 신뢰 가능한 비유동 통합ID이고
다수 회사·대규모**인 경우 — 유동 채권/채무 canonical에 비유동이 섞여 유동성 분류가 왜곡된다.

## 4. 별도필요 (4쌍)

유동 canonical에 비유동/이종이 다수사·대규모로 흡수돼 분류 왜곡. 별도 canonical 또는 재매핑 후보.

| canonical | 흡수된 표준ID(account_id) | 회사수 | 행수 | 최대금액 | 사유 | raw 예시(corp·연도·fs·라벨·금액) |
|---|---|--:|--:|--:|---|---|
| 매출채권및기타유동채권 | LongTermTradeAndOtherNonCurrentReceivablesGross | 62 | 236 | 14,910억 | 라벨이 유동/비유동 미표기 일반명('매출채권및기타채권')인데 account_id는 명확히 비유동 통합 수취채권. 62개사·최대 1.5조 규모로 유동 통합채권 canonical에 비유동이 섞여 유동성 분류를 왜곡. 비유동매출채권및기타채권 canonical 신설 또는 비유동매출채권 재매핑 검토. | 00131832·2023·OFS·'매출채권및기타채권'·미기재 / 00190321·2022·CFS·'매출채권및기타채권'·14,910억 |
| 매입채무및기타유동채무 | LongTermTradeAndOtherNonCurrentPayables | 58 | 210 | 13,388억 | 라벨 일반명('매입채무 및 기타채무'), account_id는 비유동 통합 채무. 58개사·최대 1.3조. 유동 통합채무 canonical에 비유동 혼입. 비유동 통합채무 canonical 신설/재매핑 검토. | 00130763·2025·CFS·'매입채무 및 기타채무'·미기재 / 00131832·2023·CFS·'매입채무및기타채무'·미기재 |
| 매출채권및기타유동채권 | NoncurrentReceivables | 30 | 78 | 9,896억 | account_id가 순수 비유동 수취채권인데 라벨('매출채권및기타채권')로 유동 통합채권에 흡수. 30개사·최대 9,896억. 유동성 왜곡 — 비유동매출채권 재매핑 검토. | 00160588·2023·CFS·'매출채권및기타채권'·9,896억 / 00838005·2025·OFS·'매출채권및기타채권'·4,876억 |
| 매입채무및기타유동채무 | NoncurrentPayables | 16 | 35 | 280억 | 순수 비유동 채무가 유동 통합채무에 흡수. 16개사. 금액은 중간(최대 280억)이나 구조적 비유동 혼입. 비유동 채무로 재매핑 검토. | 00162063·2025·CFS·'매입채무및기타채무'·280억 / 00108135·2025·OFS·'매입채무및기타채무'·233억 |

## 5. 수동검토 (25쌍)

라벨↔account_id 불일치·개념 모호·고액 단일사 등 — 사람 판단 필요.

| canonical | 흡수된 표준ID(account_id) | 회사수 | 행수 | 최대금액 | 사유 | raw 예시(corp·연도·fs·라벨·금액) |
|---|---|--:|--:|--:|---|---|
| 계약자산 | NonCurrentFirmCommitmentAsset | 6 | 47 | 17,022억 | 라벨 '확정계약자산'. account_id는 비유동 확정계약(firm commitment: 공정가치위험회피 대상)으로 IFRS15 계약자산(contract asset)과 개념이 다르고 비유동. 6개사·최대 1.7조로 큼. 한국 실무에서 '확정계약자산'을 진행기준 계약자산으로 쓰면 benign, 위험회피 확정계약이면 별도필요 — 개념 해석 필요. | 00126308·2022·CFS·'확정계약자산'·미기재 / 00164609·2020·CFS·'확정계약자산'·미기재 |
| 계약부채 | NonCurrentFirmCommitmentLiabilities | 6 | 45 | 3,250억 | 라벨 '확정계약부채'. account_id는 비유동 확정계약부채로 IFRS15 계약부채와 개념 상이 + 비유동. 6개사·최대 3,250억. 계약자산 케이스와 동일 쟁점(개념 해석). | 00126308·2020·CFS·'확정계약부채'·미기재 / 00164830·2020·OFS·'확정계약부채'·미기재 |
| FVOCI금융자산 | NonCurrentFinancialAssetsHeldToMaturity | 1 | 8 | 93억 | 라벨 FVOCI. account_id 만기보유(HTM, legacy). HTM의 IFRS9 후신은 통상 상각후원가(채무상품 FVOCI도 가능) — 라벨과 코드가 다른 종류를 가리킴. 1개사·93억. | 00787057·2020·CFS·'기타포괄손익-공정가치측정금융자산'·93억 / 00787057·2020·OFS·'기타포괄손익-공정가치측정금융자산'·93억 |
| 사채 | CurrentPortionOfConvertibleBonds | 2 | 7 | 192억 | 라벨 '사채'(유동/비유동 미표기). account_id는 전환사채 유동성분(당기상환=유동). 유동성사채 canonical이 별도로 존재 → 유동성사채 재매핑 후보. 라벨이 일반 '사채'라 의도 모호. | 00255105·2021·OFS·'사채'·192억 / 00105606·2025·CFS·'사채'·0.00억 |
| 사채 | CurrentBondsIssuedAndCurrentPortionOfNoncurrentBondsIssued | 4 | 7 | 280억 | 라벨 '사채'. account_id 유동사채+비유동사채 당기상환분(유동). 유동성사채 재매핑 후보. 4개사. | 00117027·2025·CFS·'사채'·35억 / 00192499·2024·CFS·'사채'·미기재 |
| 계약부채 | LongTermTradeAndOtherNonCurrentPayables | 1 | 6 | 1,148억 | 라벨 '계약부채'. account_id는 비유동 통합채무(계약부채와 무관) — filer 오태깅. 비유동계약부채 canonical 존재. 1개사·1,148억. | 00113410·2020·CFS·'계약부채'·1,148억 / 00113410·2021·CFS·'계약부채'·1,108억 |
| FVOCI금융자산 | LongTermTradeAndOtherNonCurrentReceivablesGross | 1 | 6 | 4,437억 | 라벨 FVOCI. account_id 비유동 통합 수취채권(금융자산과 무관) — filer 오태깅. 1개사이나 4,437억으로 큼. | 00113410·2021·CFS·'기타포괄손익-공정가치 측정 금융자산'·4,437억 / 00113410·2021·OFS·'기타포괄손익-공정가치 측정 금융자산'·4,437억 |
| 매출채권 | LongTermTradeAndOtherNonCurrentReceivablesGross | 2 | 4 | 29억 | 라벨 '매출채권'(순수·유동 성격)인데 account_id는 비유동 통합 — 라벨(유동)과 코드(비유동)가 모순. 2개사. | 00128175·2024·CFS·'매출채권'·미기재 / 00140131·2022·OFS·'매출채권'·29억 |
| 자본금변동 | IncreaseDecreaseThroughTransfersAndOtherChangesEquity | 1 | 4 | 4억 | 라벨 '유상증자'(자본금변동)인데 account_id는 대체·기타자본변동(통합) — 라벨과 코드 불일치. SCE 1개사·소액. | 00178851·2025·CFS·'유상증자'·미기재 / 00178851·2025·CFS·'유상증자'·미기재 |
| 미지급비용 | LongTermAccruedExpensesGross | 2 | 3 | 0.27억 | 라벨 '미지급비용'(유동성 미표기), account_id 장기(비유동) 미지급비용. 비유동→유동 혼입. 2개사·0.27억 소액. | 00103547·2022·CFS·'미지급비용'·0.27억 / 01491607·2023·CFS·'미지급비용'·0.19억 |
| 공사손실충당부채 | NonCurrentProvisionForConstructionLosses | 2 | 3 | 16억 | 라벨 '공사손실충당부채', account_id 비유동 공사손실충당. 현 canonical은 유동만 등록 — 비유동 버전(장기충당부채?) 검토. 2개사·16억. | 00144650·2024·CFS·'공사손실충당부채'·16억 / 00442154·2020·CFS·'공사손실충당부채'·미기재 |
| 충당부채 | OtherNonCurrentLiabilities | 1 | 3 | 0.25억 | 라벨 '충당부채', account_id 기타비유동부채. 충당부채 canonical은 유동, 비유동은 장기충당부채 — 비유동 혼입. 1개사·0.25억. | 00491336·2022·CFS·'충당부채'·0.25억 / 00491336·2021·CFS·'충당부채'·0.24억 |
| 사채 | CurrentPortionOfBondWithWarrant | 1 | 2 | 348억 | 라벨 '사채'. account_id 신주인수권부사채 유동성분(유동). 유동성사채 재매핑 후보. 1개사·348억. | 00977650·2024·OFS·'사채'·348억 / 00977650·2025·OFS·'사채'·미기재 |
| 사채 | CurrentPortionOfExchangeableBond | 1 | 2 | 151억 | 라벨 '사채'. account_id 교환사채 유동성분(유동). 유동성사채 재매핑 후보. 1개사·151억. | 00159786·2025·CFS·'사채'·151억 / 00159786·2025·OFS·'사채'·151억 |
| 미지급금 | LongTermOtherPayablesNet | 1 | 2 | 90억 | 라벨 '미지급금'(유동성 미표기), account_id 장기미지급금(비유동). 비유동→유동 혼입. 1개사·90억. | 00992871·2025·CFS·'미지급금'·90억 / 00992871·2025·OFS·'미지급금'·90억 |
| 매입채무및기타유동채무 | ShortTermCollectionWithholdings | 1 | 2 | 4,434억 | 라벨 '매입채무및기타채무'(통합). account_id는 단기 수금예수금(예수금류) — 예수금이 기타채무에 포함될 여지는 있으나 별개 개념. 1개사·4,434억으로 큼. | 00131832·2020·CFS·'매입채무및기타채무'·4,434억 / 00131832·2021·CFS·'매입채무및기타채무'·3,068억 |
| 사채 | CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings | 1 | 2 | 3,197억 | 라벨 '사채'. account_id는 유동차입금+비유동차입금 당기상환분(차입금, 유동). 사채≠차입금 + 유동성. 1개사·3,197억. | 00877059·2025·CFS·'사채'·3,197억 / 00877059·2025·OFS·'사채'·3,197억 |
| 장기차입금 | CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings | 1 | 2 | 9,031억 | 라벨 '장기차입금'인데 account_id는 유동차입+당기상환분(유동) — 라벨(비유동)과 코드(유동) 모순. 유동성장기차입금 후보. 1개사·9,031억. | 01316245·2023·CFS·'장기차입금'·9,031억 / 01316245·2023·OFS·'장기차입금'·4,946억 |
| 매출채권및기타유동채권 | CurrentTaxAssets | 1 | 2 | 9,740억 | 라벨 '매출채권및기타채권'(통합). account_id는 당기법인세자산(세무자산)으로 채권과 별개 개념. 1개사·9,740억으로 큼. | 00131832·2021·CFS·'매출채권및기타채권'·9,740억 / 00131832·2020·CFS·'매출채권및기타채권'·7,668억 |
| 선수금 | NoncurrentAdvances | 1 | 2 | 11억 | 라벨 '선수금'(유동성 미표기), account_id 비유동 선수금. 비유동→유동 혼입. 1개사·11억. | 00992871·2025·CFS·'선수금'·11억 / 00992871·2025·OFS·'선수금'·11억 |
| FVOCI금융자산 | NoncurrentFinancialAssetsAtFairValueThroughProfitOrLossMandatorilyMeasuredAtFairValue | 1 | 2 | 37억 | 라벨 FVOCI인데 account_id는 FVPL(의무 공정가치측정) — 라벨과 코드가 다른 측정종류. 1개사·37억. | 00145738·2020·CFS·'기타포괄손익공정가치측정금융자산'·37억 / 00145738·2020·OFS·'기타포괄손익공정가치측정금융자산'·37억 |
| 충당부채 | OtherNoncurrentFinancialLiabilities | 1 | 2 | 0.77억 | 라벨 '충당부채', account_id 기타비유동금융부채. 비유동 혼입 + 금융부채≠충당부채. 1개사·0.77억 소액. | 00131832·2021·CFS·'충당부채'·0.77억 / 00131832·2020·CFS·'충당부채'·0.35억 |
| FVPL금융자산 | DebtSecuritiesAtFairValueThroughOtherComprehensiveIncome | 1 | 1 | 8억 | 라벨 FVPL인데 account_id는 FVOCI 채무증권 — 라벨과 코드가 다른 측정종류. 1개사·8억. | 00136004·2024·CFS·'당기손익-공정가치측정금융자산'·8억 |
| 상각후원가금융자산 | SeparateAccountDerivativeFinancialAssetsHeldForTrading | 1 | 1 | 2억 | 라벨 '상각후원가측정금융자산'인데 account_id는 별도계정 파생(HFT=FVPL, 보험 별도계정) — 라벨과 코드 모순. 1개사·2억 소액. | 00146232·2023·CFS·'상각후원가측정금융자산'·2억 |
| 계약자산 | NoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleOrAsHeldForDistributionToOwners | 1 | 1 | 5,366억 | 라벨 '미청구공사'(=계약자산). account_id는 매각예정비유동자산으로 계약자산과 전혀 무관 — 명백한 filer 오태깅. 라벨 신뢰 시 계약자산이 맞으나 account_id가 매각예정+5,366억으로 커 검토. 2016년 단건. | 00309503·2016·OFS·'미청구공사'·5,366억 |

## 6. benign (23쌍)

라벨이 흡수처와 일치하고 account_id가 filer 오태깅/legacy(IFRS9 승계)라 영향 미미.

| canonical | 흡수된 표준ID(account_id) | 회사수 | 행수 | 최대금액 | 사유 | raw 예시(corp·연도·fs·라벨·금액) |
|---|---|--:|--:|--:|---|---|
| 매입채무및기타유동채무 | ShortTermTradePayables | 9 | 39 | 9,127억 | 라벨('매입채무및기타채무')이 통합 canonical과 일치. account_id는 순수 매입채무(유동)로 같은 유동 매입채무 가족. 순수→통합 소폭 합산 외 왜곡 없음. | 00428251·2022·CFS·'매입채무및기타채무'·9,127억 / 00216498·2022·CFS·'매입채무및기타채무'·924억 |
| 비유동매출채권 | LongTermTradeAndOtherNonCurrentReceivablesGross | 12 | 34 | 142억 | 라벨('비유동매출채권'/'장기매출채권')과 흡수처(비유동매출채권) 모두 비유동. account_id가 통합(AndOther)이나 라벨은 순수 장기매출채권 — 둘 다 비유동 매출채권 가족. | 00126478·2021·CFS·'비유동매출채권'·104억 / 00146232·2024·CFS·'장기매출채권'·142억 |
| 기타자본변동 | IncreaseDecreaseThroughTransfersAndOtherChangesEquity | 3 | 25 | 1,213억 | 라벨('연결실체의 변동'/'연결실체내 자본거래등')이 기타자본변동 alias와 일치. account_id는 대체·기타자본변동(통합)으로 같은 SCE 기타자본변동 성격. | 00120076·2025·CFS·'연결실체의 변동'·1,213억 / 00161976·2022·CFS·'연결실체내 자본거래등'·69억 |
| FVOCI금융자산 | NonCurrentAvailableForSaleFinancialAssets | 5 | 20 | 38억 | 라벨 전부 FVOCI(기타포괄손익-공정가치). account_id는 매도가능(IFRS9 이전 legacy 코드). 매도가능지분의 IFRS9 후신이 FVOCI라 라벨이 정확 — account_id가 legacy 잔존. | 01405390·2024·CFS·'기타포괄손익-공정가치금융자산'·38억 / 00218575·2023·OFS·'기타포괄손익-공정가치측정금융자산'·30억 |
| 장기차입금 | LongTermTradeAndOtherNonCurrentPayables | 14 | 19 | 483억 | 라벨 전부 '장기차입금', 흡수처(장기차입금) 비유동 일치. account_id는 비유동 통합채무로 filer 오태깅 — 라벨이 신뢰 신호. | 00117577·2023·CFS·'장기차입금'·미기재 / 00129235·2023·CFS·'장기차입금'·483억 |
| FVPL금융자산 | NonCurrentAvailableForSaleFinancialAssets | 4 | 18 | 189억 | 라벨 FVPL. account_id 매도가능(legacy). 매도가능의 IFRS9 후신으로 FVPL 선택 가능 — 라벨 정확. | 00264945·2024·CFS·'당기손익-공정가치측정금융자산'·189억 / 00390365·2020·CFS·'당기손익-공정가치측정금융자산'·59억 |
| 무형자산 | CopyrightsPatentsAndOtherIndustrialPropertyRightsServiceAndOperatingRightsGross | 1 | 12 | 3억 | 라벨 '무형자산'. account_id는 산업재산권 등(무형자산 세부 구성). 무형자산 가족 내 — 1개사·3억 소액. | 00151128·2021·CFS·'무형자산'·3억 / 00151128·2021·OFS·'무형자산'·3억 |
| 지분법이익 | GainsArisingFromDerecognitionOfFinancialAssetsMeasuredAtAmortisedCost | 6 | 10 | 5,964억 | 라벨 전부 '지분법이익'(IS/CIS). account_id는 상각후원가자산 제거이익으로 지분법과 전혀 무관 — 명백한 filer 오태깅. 라벨 기반 매핑(지분법이익)이 정확. amax 5,964억은 라벨이 지분법이익인 회사 값. | 00116426·2020·CFS·'지분법이익'·미기재 / 00258801·2021·CFS·'지분법이익'·5,964억 |
| 사채 | LongTermTradeAndOtherNonCurrentPayables | 3 | 5 | 300억 | 라벨 전부 '사채'(비유동), 흡수처(사채) 일치. account_id 통합채무 오태깅 — 라벨 신뢰. | 00156150·2020·OFS·'사채'·14억 / 00599285·2023·CFS·'사채'·300억 |
| 관계기업투자 | LongTermTradeAndOtherNonCurrentReceivablesGross | 1 | 5 | 177억 | 라벨 '관계기업투자'. account_id 비유동 수취채권 오태깅 — 라벨 신뢰. 1개사. | 00110750·2025·CFS·'관계기업투자'·177억 / 00110750·2023·CFS·'관계기업투자'·72억 |
| 리스부채 | LongTermTradeAndOtherNonCurrentPayables | 1 | 4 | 8억 | 라벨 '리스부채'. account_id 통합채무 오태깅. 1개사·8억 소액. | 00398668·2022·CFS·'리스부채'·8억 / 00398668·2023·CFS·'리스부채'·6억 |
| FVPL금융자산 | LongTermTradeAndOtherNonCurrentReceivablesGross | 1 | 4 | 113억 | 라벨 FVPL. account_id 비유동 수취채권 오태깅 — 라벨 신뢰. 1개사. | 00361381·2021·OFS·'당기손익-공정가치측정금융자산'·113억 / 00361381·2023·OFS·'당기손익-공정가치측정금융자산'·110억 |
| 당기법인세부채 | OtherNoncurrentLiabilities | 1 | 4 | 0.00억 | 라벨 '당기법인세부채'. account_id 기타비유동부채(오태깅)이나 금액 0/미기재 — 영향 없음. 1개사. | 00144395·2024·CFS·'당기법인세부채'·미기재 / 00144395·2024·OFS·'당기법인세부채'·미기재 |
| 유동성장기차입금 | LongtermBorrowings | 3 | 3 | 15,392억 | 라벨 '유동성장기부채/유동성장기차입금'(유동), 흡수처(유동성장기차입금) 일치. account_id LongtermBorrowings(비유동)는 오태깅 — 라벨 신뢰. 3개사·최대 1.5조이나 라벨이 명확히 유동성. | 00113526·2023·CFS·'유동성장기부채'·15,392억 / 00672603·2025·OFS·'유동성장기차입금'·48억 |
| FVPL금융자산 | CurrentAvailableForSaleFinancialAssets | 1 | 2 | 32억 | 라벨 FVPL. account_id 유동 매도가능(legacy) — AFS→FVPL 승계, 라벨 정확. 1개사. | 00264945·2024·CFS·'당기손익-공정가치측정금융자산'·32억 / 00264945·2024·OFS·'당기손익-공정가치측정금융자산'·0.60억 |
| 상각후원가금융자산 | CurrentFinancialAssetsHeldToMaturity | 1 | 2 | 28억 | 라벨 '상각후원가측정금융자산'. account_id 유동 만기보유(HTM, legacy) — HTM의 IFRS9 후신이 상각후원가라 라벨 정확. | 00264945·2024·CFS·'상각후원가측정금융자산'·28억 / 00264945·2024·OFS·'상각후원가측정금융자산'·18억 |
| 종속기업투자 | NonCurrentAvailableForSaleFinancialAssets | 1 | 2 | 304억 | 라벨 '종속기업투자주식'(별도재무제표 OFS). account_id 매도가능(legacy 오태깅) — 라벨 신뢰. 1개사·304억. | 00483735·2023·OFS·'종속기업투자주식'·304억 / 00483735·2022·OFS·'종속기업투자주식'·195억 |
| 상각후원가금융자산 | NonCurrentFinancialAssetsHeldToMaturity | 1 | 2 | 0.01억 | 라벨 '상각후원가 측정 금융자산'. account_id 비유동 HTM(legacy) — HTM→상각후원가 정확. 1개사·0.01억. | 01231786·2025·CFS·'상각후원가 측정 금융자산'·0.01억 / 01231786·2025·OFS·'상각후원가 측정 금융자산'·0.01억 |
| FVOCI금융자산 | CurrentAvailableForSaleFinancialAssets | 1 | 1 | 0.00억 | 라벨 FVOCI. account_id 유동 매도가능(legacy) — AFS→FVOCI 승계, 라벨 정확. 1개사·금액 0/미기재. | 00614593·2025·CFS·'기타포괄손익-공정가치 측정 금융자산'·미기재 |
| 유동성장기차입금 | PresentValueDiscountsLongTermBorrowingsGross | 1 | 1 | 794억 | 라벨 '유동성장기차입금', 흡수처 일치. account_id는 장기차입금 현재가치할인차금(차감항목, 음수) — 같은 계정의 차감. 1개사. | 00146232·2023·CFS·'유동성장기차입금'·794억 |
| 기타유동자산 | CurrentPrepaymentsAndOtherCurrentAssets | 1 | 1 | 4억 | 라벨 '기타유동자산'. account_id 유동 선급+기타유동자산(통합) — 둘 다 유동 기타자산 가족. 1개사·4억. | 00143226·2025·CFS·'기타유동자산'·4억 |
| 매입채무및기타유동채무 | OtherNoncurrentLiabilities | 1 | 1 | 8억 | 라벨 '매입채무 및 기타채무'(통합)과 흡수처 일치. account_id 기타비유동부채(오태깅)이나 1개사·8억 소액 — 영향 미미. | 00373571·2025·OFS·'매입채무 및 기타채무'·8억 |
| 매입채무및기타유동채무 | TradeAndOtherPayablesToTradeSuppliers | 1 | 1 | 493억 | 라벨 '매입채무 및 기타채무'(통합). account_id 순수 공급자매입채무(유동) — 유동 매입채무 가족. 1개사·493억. | 00264945·2024·CFS·'매입채무 및 기타채무'·493억 |

## 7. 산출물·재현

- 증거 JSON: `data/backtest/_audit_dc_evidence.json` (52쌍, 쌍별 예시 최대 6건·전체 행수).
- 수집 하니스: `data/backtest/_audit_dc_evidence.py` (운영 mapper·statement 가드 동일 적용, raw 전수 스캔, read-only).
- 본 문서 생성: `data/backtest/_audit_dc_verdict_report.py`.
- 후속: 별도필요 4쌍·수동검토 25쌍은 사용자 토의로 canonical 신설/재매핑 여부 결정. config·코드 수정은 별도 작업.