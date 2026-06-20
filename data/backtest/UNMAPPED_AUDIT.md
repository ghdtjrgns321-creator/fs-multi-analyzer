# 미분류 잔여 + 거시구조 전수 탐색 (UNMAPPED_AUDIT)

> Phase1이 canonical로 분류 못 하고 '기타 중요 계정'으로 넘기는 잔여를 전수 측정 + 사업보고서
> 분해 차원 인벤토리. 운영 가드·_dedupe_statement_rows 실호출. 목적: 분류 천장·거시구조 파악.
> 단정 금지 — canonical 신설·수정은 다음 단계(§8). 재현: `_audit_unmapped.py`·`_audit_macro_structure.py`.

## 1. 미분류 잔여 전수

- 회사 1667사·파일 9,319·회사연도 4,773.
- statement-dedup 후 행 1,181,691 중 **미분류 604,168 (51.1%)**, 분류 577,523.
- 가드 후 raw 1,575,557 → dedup 붕괴 393,866행 (차원행 raw 488,108 — 주로 SCE 구성요소·member).
- 미분류 분해: 표준ID 보유 484,822행 / 공백ID(확장계정) 119,346행.

> 금액(최대금액)은 원천 `thstrm_amount` 절대값이며 원천 스케일 이상치(corp 00204226 등)가 일부 과대계상. 분류 후보 판단 기준은 **행수·표준ID 존재**이며 금액과 무관.

### sj_div별 미분류율 (어느 표가 안 잡히나)

| sj_div | 전체 | 미분류 | 미분류율 |
|---|--:|--:|--:|
| BS | 406,642 | 136,380 | 33.5% |
| CF | 446,568 | 342,801 | 76.8% |
| CIS | 215,023 | 48,787 | 22.7% |
| IS | 16,834 | 3,948 | 23.5% |
| SCE | 96,624 | 72,252 | 74.8% |

## 2. 신규분류 가능 — 표준ID 있는데 canonical 어디에도 없음 (최우선)

표준ID 보유·미등록 account_id **2080종**. 이것이 '더 분류할 수 있는' 핵심 — canonical 신설/등록 시 EXACT 매핑으로 분류 가능.

| account_id | 행수 | 최대금액 | 주 sj | 예시 라벨 |
|---|--:|--:|---|---|
| dart_CashAndCashEquivalentsAtBeginningOfPeriodCf | 9,285 | 418,425,930억 | CF | 기초현금및현금성자산, 기초의 현금및현금성자산 |
| dart_CashAndCashEquivalentsAtEndOfPeriodCf | 9,085 | 370,488,403억 | CF | 기말현금및현금성자산, 기말의 현금및현금성자산 |
| dart_ElementsOfOtherStockholdersEquity | 7,167 | 6,653,991억 | BS | 기타자본구성요소, 기타자본항목 |
| ifrs-full_EffectOfExchangeRateChangesOnCashAndCashEquivalents | 7,028 | 9,163,867억 | CF | 현금및현금성자산에 대한 환율변동효과, 현금및현금성자산의 환율변동효과 |
| dart_CapitalSurplus | 6,956 | 311,327,346억 | BS | 자본잉여금, 기타불입자본 |
| ifrs-full_IncreaseDecreaseInCashAndCashEquivalents | 6,678 | 47,937,527억 | CF | 현금및현금성자산의순증가(감소), 현금및현금성자산의 증가(감소) |
| ifrs-full_CurrentTaxAssets | 5,915 | 252,735억 | BS | 당기법인세자산, 선급법인세 |
| dart_ProceedsFromShortTermBorrowings | 5,840 | 753,100억 | CF | 단기차입금의 증가, 단기차입금의 차입 |
| ifrs-full_OtherNoncurrentFinancialAssets | 5,796 | 187,238억 | BS | 기타비유동금융자산, 기타금융자산 |
| dart_RepaymentsOfShortTermBorrowings | 5,705 | 726,100억 | CF | 단기차입금의 상환, 단기차입금의 감소 |
| ifrs-full_AdjustmentsForReconcileProfitLoss | 5,445 | 70,551,532억 | CF | 당기순이익조정을 위한 가감, 조정 |
| ifrs-full_OtherCurrentFinancialAssets | 5,423 | 183,774억 | BS | 기타유동금융자산, 기타금융자산 |
| dart_IncreaseInGuaranteeDeposits | 5,152 | 824,000억 | CF | 임차보증금의 증가, 보증금의 증가 |
| dart_DecreaseInGuaranteeDeposits | 5,126 | 300,000억 | CF | 임차보증금의 감소, 보증금의 감소 |
| dart_ProceedsFromSalesOfShortTermFinancialInstruments | 5,075 | 207,054,642억 | CF | 단기금융상품의 처분, 단기금융상품의 감소 |
| dart_PurchaseOfShortTermFinancialInstruments | 4,975 | 140,069,337억 | CF | 단기금융상품의 취득, 단기금융상품의 증가 |
| ifrs-full_DividendsReceivedClassifiedAsOperatingActivities | 4,922 | 294,978억 | CF | 배당금수취(영업), 배당금의 수취 |
| ifrs-full_OtherCurrentLiabilities | 4,826 | 185,257억 | BS | 기타 유동부채, 기타유동부채 |
| dart_OtherComprehensiveIncomeLossAccumulatedAmount | 4,812 | 10,995,979억 | BS | 기타포괄손익누계액, 기타자본구성요소 |
| ifrs-full_OtherCurrentFinancialLiabilities | 4,652 | 411,397억 | BS | 기타유동금융부채, 기타금융부채 |
| ifrs-full_ProceedsFromSalesOfIntangibleAssetsClassifiedAsInvestingActivities | 4,542 | 35,650억 | CF | 무형자산의 처분, 무형자산의 감소 |
| ifrs-full_OtherNoncurrentFinancialLiabilities | 4,207 | 983,341억 | BS | 기타비유동금융부채, 기타금융부채 |
| ifrs-full_IncreaseDecreaseInCashAndCashEquivalentsBeforeEffectOfExchangeRateChanges | 3,606 | 110,365억 | CF | 환율변동효과 반영전 현금및현금성자산의 순증가(감소), 현금및현금성자산의 증가(감소) |
| dart_LongTermDepositsNotClassifiedAsCashEquivalents | 3,416 | 16,831억 | BS | 장기금융상품, 장기금융자산 |
| dart_LongTermTradeAndOtherNonCurrentReceivablesGross | 3,358 | 5,122,200억 | BS | 장기매출채권 및 기타비유동채권, 기타비유동채권 |
| dart_OtherCurrentLiabilities | 3,350 | 18,979,809억 | BS | 기타유동부채, 기타부채 |
| ifrs-full_OtherNoncurrentAssets | 3,239 | 200,124억 | BS | 기타비유동자산, 기타자산 |
| dart_PurchaseOfLongTermFinancialInstruments | 3,117 | 148,360억 | CF | 장기금융상품의 취득, 장기금융상품의 증가 |
| dart_PaymentsOfFinanceLeaseLiabilitiesClassifiedAsFinancingActivities | 3,077 | 14,566억 | CF | 리스부채의 상환, 금융리스부채의 지급 |
| dart_PurchaseOfFairValueFinancialAsset | 2,858 | 28,400,000억 | CF | 당기손익인식금융자산의 취득, 당기손익-공정가치측정금융자산의 취득 |
| dart_ProceedsFromSalesOfShortTermLoansAndReceivables | 2,826 | 20,000,000억 | CF | 단기대여금의 감소, 단기대여금및수취채권의 처분 |
| dart_ProceedsFromSalesOfFairValueFinancialAsset | 2,751 | 22,161,224억 | CF | 당기손익인식금융자산의 처분, 당기손익-공정가치측정금융자산의 처분 |
| dart_LongTermTradeAndOtherNonCurrentPayables | 2,729 | 469,888억 | BS | 장기매입채무 및 기타비유동채무, 장기매입채무및기타채무 |
| dart_IncreaseInGuaranteeDepositsAsFinancialActivities | 2,668 | 7,539억 | CF | 임대보증금의 증가, 예수보증금의 증가 |
| ifrs-full_OtherNoncurrentLiabilities | 2,624 | 111,960억 | BS | 기타 비유동 부채, 기타비유동부채 |
| dart_PurchaseOfShortTermLoansAndReceivables | 2,616 | 20,000,000억 | CF | 단기대여금의 증가, 단기대여금및수취채권의 취득 |
| dart_PurchaseOfLongTermLoansAndReceivables | 2,581 | 4,171억 | CF | 장기대여금의 증가, 장기대여금및수취채권의 취득 |
| dart_ProceedsFromSalesOfLongTermFinancialInstruments | 2,554 | 82,729억 | CF | 장기금융상품의 처분, 장기금융상품의 감소 |
| dart_DecreaseInGuaranteeDepositsAsFinancialActivities | 2,530 | 2,555억 | CF | 임대보증금의 감소, 임대보증금의 상환 |
| dart_PurchaseOfInvestmentsInSubsidiaries | 2,522 | 36,271억 | CF | 종속기업에 대한 투자자산의 취득, 종속기업투자주식의 취득 |
| dart_ProceedsFromSalesOfLongTermLoansAndReceivables | 2,461 | 7,683억 | CF | 장기대여금의 감소, 장기대여금및수취채권의 처분 |
| dart_ProfitLossForStatementOfCashFlows | 2,450 | 115,872,704억 | CF | 당기순이익(손실), 당기순이익 |
| ifrs-full_PaymentsOfFinanceLeaseLiabilitiesClassifiedAsFinancingActivities | 2,285 | 2,633,379억 | CF | 리스부채의 상환, 금융리스부채의 지급 |
| dart_OtherNonCurrentAssets | 2,262 | 83,687억 | BS | 기타비유동자산, 기타자산 |
| ifrs-full_ProceedsFromGovernmentGrantsClassifiedAsInvestingActivities | 2,233 | 17,224억 | CF | 정부보조금의 수취, 정부보조금의 수령 |
| dart_ChangesInReserveOfGainsAndLossesOnFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome | 2,198 | 54,696억 | SCE | 기타포괄손익-공정가치 측정 금융자산 평가손익, 기타포괄손익-공정가치 측정 금융자산 평가손익 적립금 |
| dart_DecreaseInLoans | 2,087 | 20,000,000억 | CF | 대여금의 감소, 단기대여금의 감소 |
| ifrs-full_RepaymentsOfBorrowingsClassifiedAsFinancingActivities | 2,044 | 1,066,361억 | CF | 차입금의 상환, 유동성장기차입금의 상환 |
| dart_IncreaseInLoans | 2,010 | 20,000,000억 | CF | 대여금의 증가, 단기대여금의 증가 |
| dart_CurrentDerivativeLiabilities | 1,973 | 16,799억 | BS | 유동파생상품부채, 파생상품부채 |
| ifrs-full_AdjustmentsForIncomeTaxExpense | 1,972 | 33,790,159억 | CF | 법인세비용, 법인세비용 조정 |
| dart_OtherComprehensiveIncomeThatWillNotBeReclassifiedToProfitOrLossNetOfTax | 1,967 | 17,765억 | CIS | 당기손익으로 재분류되지 않는항목(세후기타포괄손익), 당기손익으로 재분류되지 않는항목 |
| ifrs-full_AdjustmentsForDecreaseIncreaseInInventories | 1,897 | 43,342,821억 | CF | 재고자산의 감소(증가), 재고자산 |
| dart_PurchaseOfInvestmentsInAssociates | 1,874 | 24,093억 | CF | 관계기업에 대한 투자자산의 취득, 관계기업투자주식의 취득 |
| dart_ProceedsFromConvertibleBonds | 1,848 | 180,000억 | CF | 전환사채의 증가, 전환사채의 발행 |
| dart_AdjustmentsForLossesOnForeignExchangeTranslations | 1,808 | 39,903억 | CF | 외화환산손실, 외화환산손실 조정 |
| dart_AdjustmentsForProvisionForSeveranceIndemnities | 1,808 | 5,119억 | CF | 퇴직급여, 퇴직급여 조정 |
| dart_AdjustmentsForInterestExpenses | 1,807 | 17,056,254억 | CF | 이자비용, 이자비용 조정 |
| dart_OtherNonCurrentLiabilities | 1,778 | 106,627억 | BS | 기타비유동부채, 기타부채 |
| ifrs-full_ProceedsFromIssuingShares | 1,773 | 99,913억 | CF | 유상증자, 주식의 발행 |

… 외 2020종 (전체 _audit_unmapped.json).

## 3. 기존개념 타표문 (가드가 강등 — 동일 숫자의 CF/SCE 표현)

이미 다른 표문에 canonical이 있는 개념 **26종**이 CF/SCE 등에서 미분류로 남음 (예: ProfitLoss·Equity의 현금흐름표·자본변동표 표현). statement 가드의 의도된 분리이며, 같은 숫자라 신규분류 대상 아님 — 필요 시 '표문 태깅'으로 연결만.

| account_id | (소속 canonical) | 행수 | 최대금액 | 주 sj |
|---|---|--:|--:|---|
| ifrs-full_ProfitLoss | 당기순이익 | 12,142 | 115,872,704억 | SCE |
| ifrs-full_Equity | 자본총계 | 9,244 | 789,251,126억 | SCE |
| ifrs-full_OtherComprehensiveIncomeNetOfTaxGainsLossesOnRemeasurementsOfDefinedBenefitPlans | 확정급여재측정손익 | 2,168 | 8,283억 | SCE |
| ifrs-full_OtherComprehensiveIncome | 기타포괄손익 | 1,425 | 71,916억 | SCE |
| ifrs-full_ComprehensiveIncome | 총포괄손익 | 773 | 430,173억 | SCE |
| ifrs-full_PurchaseOfTreasuryShares | 자기주식취득 | 753 | 81,893억 | SCE |
| ifrs-full_OtherComprehensiveIncomeNetOfTaxGainsLossesFromInvestmentsInEquityInstruments | FVOCI평가손익 | 718 | 46,783억 | SCE |
| ifrs-full_GainsLossesOnExchangeDifferencesOnTranslationNetOfTax | 해외사업환산손익 | 536 | 151,161억 | SCE |
| ifrs-full_CashAndCashEquivalents | 현금및현금성자산 | 211 | 372,351억 | CF |
| ifrs-full_GainsLossesOnCashFlowHedgesNetOfTax | 현금흐름위험회피손익 | 169 | 8,371억 | SCE |
| ifrs-full_DividendsPaidClassifiedAsFinancingActivities | 배당금지급 | 87 | 5,990억 | SCE |
| ifrs-full_IssueOfEquity | 자본금변동 | 81 | 2,098억 | CF |
| dart_ChangesInConsolidatedCompanies | 기타자본변동 | 65 | 1,252억 | CF |
| ifrs-full_IncomeTaxExpenseContinuingOperations | 법인세비용 | 29 | 472억 | CF |
| ifrs-full_ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod | 지분법이익 | 8 | 65억 | SCE |
| ifrs-full_OtherComprehensiveIncomeThatWillNotBeReclassifiedToProfitOrLossNetOfTax | 재분류불가능기타포괄손익 | 7 | 3,307억 | SCE |
| ifrs-full_OtherComprehensiveIncomeThatWillBeReclassifiedToProfitOrLossNetOfTax | 재분류가능기타포괄손익 | 4 | 1,021억 | SCE |
| dart_TreasuryShareTransactions | 자기주식변동 | 4 | 265억 | CF |
| dart_OtherLosses | 기타비용 | 2 | 0.00억 | CF |
| ifrs-full_DividendsPaid | 배당변동 | 2 | 0.00억 | CF |
| ifrs-full_CashFlowsUsedInObtainingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities | 사업결합순현금유출 | 2 | 0.00억 | SCE |
| ifrs-full_ProfitLossBeforeTax | 법인세비용차감전순이익 | 2 | 104억 | CF |
| ifrs-full_ProceedsFromSalesOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities | 유형자산처분 | 1 | 0.04억 | SCE |
| ifrs-full_ProfitLossAttributableToOwnersOfParent | 지배기업귀속순이익 | 1 | 70억 | SCE |
| ifrs-full_ComprehensiveIncomeAttributableToNoncontrollingInterests | 비지배지분총포괄손익 | 1 | 0.00억 | SCE |

## 4. 공백 표준ID 확장계정 (회사 자체계정 — 표준ID 없음)

account_id 공백 + 미분류 라벨 상위 30 (표준ID 없어 alias로만 가능). 분모 46,708행+.

| 라벨 | 행수 | 최대금액 |
|---|--:|--:|
| 지분법자본변동 | 1,287 | 13,236억 |
| 확정급여제도의재측정요소 | 1,168 | 6,631억 |
| 순확정급여부채의재측정요소 | 988 | 3,248억 |
| 유동성장기차입금의상환 | 913 | 19,377억 |
| 리스부채의상환 | 896 | 2,813억 |
| 해외사업환산손익 | 896 | 13,978억 |
| 유동성장기부채의상환 | 847 | 32,913억 |
| 유상증자 | 767 | 99,913억 |
| 배당금수익 | 764 | 8,348억 |
| 재무활동으로인한현금유출액 | 722 | 94,325억 |
| 재무활동으로인한현금유입액 | 705 | 192,445억 |
| 당기순이익 | 695 | 556,541억 |
| 순확정급여자산 | 605 | 5,173억 |
| 단기대여금의증가 | 481 | 4,163억 |
| 보증금의증가 | 474 | 981억 |
| 전환사채의발행 | 455 | 4,000억 |
| 당기손익-공정가치측정금융자산의취득 | 440 | 64,492억 |
| 지분법손익 | 437 | 19,244억 |
| 투자활동으로인한현금유출액 | 428 | 161,769억 |
| 기타포괄손익-공정가치측정금융자산의처분 | 421 | 3,511억 |
| 영업으로부터창출된현금흐름 | 416 | 209,515억 |
| 투자활동으로인한현금유입액 | 414 | 69,477억 |
| 보증금의감소 | 404 | 1,992억 |
| 장기대여금의증가 | 390 | 10,874억 |
| 기타포괄손익-공정가치측정금융자산평가손익 | 389 | 55,810억 |
| 퇴직금의지급 | 381 | 637억 |
| 전환사채의전환 | 379 | 1,501억 |
| 기타포괄손익-공정가치측정금융자산의취득 | 377 | 5,091억 |
| 보험수리적손익 | 370 | 596억 |
| 단기금융상품의감소 | 361 | 41,542억 |

## 5. 거시 구조 인벤토리 (사업보고서 분해 차원)

전수 1667사·9,319파일·raw 1,575,557행.

### 5.1 재무제표 × 연결/별도 행렬

| | BS | CF | CIS | IS | SCE |
|---|--:|--:|--:|--:|--:|
| CFS | 208,916 | 228,379 | 120,306 | 9,072 | 306,009 |
| OFS | 198,812 | 218,474 | 95,678 | 7,812 | 182,099 |

### 5.2 account_detail 차원종류 (분해축 규모)

| sj_div | plain | member | 구성요소 | 기타detail |
|---|--:|--:|--:|--:|
| BS | 407,728 | 0 | 0 | 0 |
| CF | 446,853 | 0 | 0 | 0 |
| CIS | 215,984 | 0 | 0 | 0 |
| IS | 16,884 | 0 | 0 | 0 |
| SCE | 0 | 240,561 | 247,175 | 372 |

→ **SCE만 2D 매트릭스**(자본구성요소 76종 × 자본변동 행). BS/IS/CIS/CF는 plain(1D). member는 연결/별도 등 표문 태그.

### 5.3 SCE 자본구성요소 축 (상위)

자본(247,082), 지배기업의 소유주에게 귀속되는 지분(134,128), 이익잉여금(43,533), 자본금(37,476), 기타자본구성요소(33,914), 자본잉여금(33,630), 비지배지분(22,376), 기타포괄손익누계액(21,477), 기타포괄손익누적액(4,437), 주식발행초과금(3,649), 자본조정(3,254), 신종자본증권(2,227), 추가납입자본(1,853), 자기주식(1,515), 기타불입자본(938)

### 5.4 기간·단위·보고서종류

- 기간 충전율: 당기 93.4% · 전기 93.0% · 전전기 92.3% · 분기누적 0.0%. → **비교기간 3개** 가용(전전기까지).
- 통화: {'KRW': 1569765, 'USD': 5792}
- reprt_code: {'11011': 1575557} (11011=사업보고서).

### 5.5 주석 수집 현황

- 주석 디렉터리 보유 회사연도: 62 (CFS 62·OFS 62).
- 디렉터리당 파일수 분포: {'16': 124}
