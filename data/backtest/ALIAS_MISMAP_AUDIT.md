# 오매핑 전수 감사 — 표준ID 보유 + 이름매핑 (ALIAS_MISMAP_AUDIT)

> 충돌 여부·분류사전과 무관한 전수. `mapping_status==ALIAS` 인데 `account_id`(IFRS 표준ID)가
> 비어있지 않은 행 = 표준ID가 어느 canonical에도 등록 안 돼 **이름(alias)으로 흡수**된 직접 증거.
> 운영 statement 가드(`_apply_statement_guard`) 적용 후 측정. 분류는 config 등록ID와 표준명 실질 비교(자기참조 회피).
> 재현: `data/backtest/_audit_alias_mapped.py` → `_audit_alias_mapped_report.py`.

## 1. 전수 커버리지

- 회사 1667사 전수, 전체 행 1,575,557, 매핑된 행 682,205.
- **표준ID 보유 + 이름매핑(오매핑/등록누락 후보) 행: 30,847** → distinct (account_id, canonical) **540쌍**.
- 공백 account_id 이름매핑(표준ID 없어 불가피, 별도 분모): 22,398행.
- account_id EXACT 매핑(명시 등록, 신뢰)은 본 감사 대상 아님.

분류 결과(쌍 기준): 오매핑 52 · 수동확인 427 · 등록누락(무해) 61.
분류 결과(행 기준): 오매핑 940 · 수동확인 22,838 · 등록누락 7,069.

## 2. 오매핑 (이종개념이 이름으로 흡수) — 수정 후보

| canonical | 흡수된 표준ID(account_id) | 사유 | 등록ID(stem) | 행수 | 최대금액 | 예시 라벨 |
|---|---|---|---|--:|--:|---|
| 매출채권및기타유동채권 | LongTermTradeAndOtherNonCurrentReceivablesGross | 비유동 표준ID가 유동 canonical에 흡수 | TradeAndOtherCurrentReceivables, TradeAndOtherCurrentReceivables | 236 | 14,910억 | 매출채권 및 기타채권, 매출채권및기타채권 |
| 매입채무및기타유동채무 | LongTermTradeAndOtherNonCurrentPayables | 비유동 표준ID가 유동 canonical에 흡수 | TradeAndOtherCurrentPayables, TradeAndOtherCurrentPayables | 210 | 13,388억 | 매입채무 및 기타채무, 매입채무및기타채무 |
| 매출채권및기타유동채권 | NoncurrentReceivables | 비유동 표준ID가 유동 canonical에 흡수 | TradeAndOtherCurrentReceivables, TradeAndOtherCurrentReceivables | 78 | 9,896억 | 매출채권및기타채권 |
| 계약자산 | NonCurrentFirmCommitmentAsset | 비유동 표준ID가 유동 canonical에 흡수 | ContractAssets, CurrentContractAssets, ShortTermDueFromCustomersForContractWork | 47 | 17,022억 | 확정계약자산 |
| 계약부채 | NonCurrentFirmCommitmentLiabilities | 비유동 표준ID가 유동 canonical에 흡수 | CurrentContractLiabilities, ShortTermDueToCustomersForContractWork, ShortTermIncomeReceivedInAdvance | 45 | 3,250억 | 확정계약부채 |
| 매입채무및기타유동채무 | ShortTermTradePayables | 통합(AndOther)↔순수 불일치 | TradeAndOtherCurrentPayables, TradeAndOtherCurrentPayables | 39 | 9,127억 | 매입채무 및 기타채무, 매입채무및기타채무 |
| 매입채무및기타유동채무 | NoncurrentPayables | 비유동 표준ID가 유동 canonical에 흡수 | TradeAndOtherCurrentPayables, TradeAndOtherCurrentPayables | 35 | 280억 | 매입채무및기타채무 |
| 비유동매출채권 | LongTermTradeAndOtherNonCurrentReceivablesGross | 통합(AndOther)↔순수 불일치 | LongTermTradeReceivablesGross, NoncurrentTradeReceivables | 34 | 142억 | 비유동매출채권, 장기매출채권 |
| 기타자본변동 | IncreaseDecreaseThroughTransfersAndOtherChangesEquity | 통합(AndOther)↔순수 불일치 | ChangesInConsolidatedCompanies, IncreaseDecreaseThroughChangesInAccountingPolicies, IntercompanyAcquisition | 25 | 1,213억 | 연결실체내 자본거래등, 연결실체의 변동 |
| FVOCI금융자산 | NonCurrentAvailableForSaleFinancialAssets | 이종 측정종류(매도가능) ↔ 등록(['FVOCI']) | FinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome | 20 | 38억 | 기타포괄손익-공정가치금융자산, 기타포괄손익-공정가치측정금융자산 |
| 장기차입금 | LongTermTradeAndOtherNonCurrentPayables | 통합(AndOther)↔순수 불일치 | LongTermBorrowingsGross, NoncurrentPortionOfNoncurrentLoansReceived | 19 | 483억 | 장기차입금 |
| FVPL금융자산 | NonCurrentAvailableForSaleFinancialAssets | 이종 측정종류(매도가능) ↔ 등록(['FVPL']) | FinancialAssetsMeasuredAtFairValueThroughProfitOrLoss | 18 | 189억 | 당기손익-공정가치 측정 금융자산, 당기손익-공정가치측정금융자산 |
| 무형자산 | CopyrightsPatentsAndOtherIndustrialPropertyRightsServiceAndOperatingRightsGross | 통합(AndOther)↔순수 불일치 | IntangibleAssetsAndGoodwill, IntangibleAssetsOtherThanGoodwill | 12 | 3억 | 무형자산 |
| 지분법이익 | GainsArisingFromDerecognitionOfFinancialAssetsMeasuredAtAmortisedCost | 이종 측정종류(상각후원가) ↔ 등록(['지분법']) | ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod | 10 | 5,964억 | 지분법이익 |
| FVOCI금융자산 | NonCurrentFinancialAssetsHeldToMaturity | 이종 측정종류(만기보유) ↔ 등록(['FVOCI']) | FinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome | 8 | 93억 | 기타포괄손익-공정가치측정금융자산 |
| 사채 | CurrentPortionOfConvertibleBonds | 유동 표준ID가 비유동 canonical에 흡수 | BondsIssued, NoncurrentPortionOfNoncurrentBondsIssued | 7 | 192억 | 사채 |
| 사채 | CurrentBondsIssuedAndCurrentPortionOfNoncurrentBondsIssued | 유동 표준ID가 비유동 canonical에 흡수 | BondsIssued, NoncurrentPortionOfNoncurrentBondsIssued | 7 | 280억 | 사채 |
| 계약부채 | LongTermTradeAndOtherNonCurrentPayables | 비유동 표준ID가 유동 canonical에 흡수 | CurrentContractLiabilities, ShortTermDueToCustomersForContractWork, ShortTermIncomeReceivedInAdvance | 6 | 1,148억 | 계약부채 |
| FVOCI금융자산 | LongTermTradeAndOtherNonCurrentReceivablesGross | 통합(AndOther)↔순수 불일치 | FinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome | 6 | 4,437억 | 기타포괄손익-공정가치 측정 금융자산, 기타포괄손익-공정가치측정금융자산 |
| 사채 | LongTermTradeAndOtherNonCurrentPayables | 통합(AndOther)↔순수 불일치 | BondsIssued, NoncurrentPortionOfNoncurrentBondsIssued | 5 | 300억 | 사채 |
| 관계기업투자 | LongTermTradeAndOtherNonCurrentReceivablesGross | 통합(AndOther)↔순수 불일치 | InvestmentAccountedForUsingEquityMethod, InvestmentsInAssociates, InvestmentsInSubsidiariesJointVenturesAndAssociates | 5 | 177억 | 관계기업투자 |
| 리스부채 | LongTermTradeAndOtherNonCurrentPayables | 통합(AndOther)↔순수 불일치 | LeaseLiabilities | 4 | 8억 | 리스부채 |
| FVPL금융자산 | LongTermTradeAndOtherNonCurrentReceivablesGross | 통합(AndOther)↔순수 불일치 | FinancialAssetsMeasuredAtFairValueThroughProfitOrLoss | 4 | 113억 | 당기손익-공정가치측정금융자산 |
| 매출채권 | LongTermTradeAndOtherNonCurrentReceivablesGross | 비유동 표준ID가 유동 canonical에 흡수 | CurrentTradeReceivables, ShortTermTradeReceivable | 4 | 29억 | 매출채권 |
| 자본금변동 | IncreaseDecreaseThroughTransfersAndOtherChangesEquity | 통합(AndOther)↔순수 불일치 | IssueOfEquity | 4 | 4억 | 유상증자 |
| 당기법인세부채 | OtherNoncurrentLiabilities | 비유동 표준ID가 유동 canonical에 흡수 | CurrentTaxLiabilities | 4 | 0.00억 | 당기법인세부채 |
| 미지급비용 | LongTermAccruedExpensesGross | 비유동 표준ID가 유동 canonical에 흡수 | AccrualsClassifiedAsCurrent | 3 | 0.27억 | 미지급비용 |
| 공사손실충당부채 | NonCurrentProvisionForConstructionLosses | 비유동 표준ID가 유동 canonical에 흡수 | CurrentProvisionForConstructionLosses | 3 | 16억 | 공사손실충당부채 |
| 충당부채 | OtherNonCurrentLiabilities | 비유동 표준ID가 유동 canonical에 흡수 | CurrentProvisions, CurrentProvisions, OtherShorttermProvisions, ShorttermMiscellaneousOtherProvisions, ShorttermMiscellaneousOtherProvisions, ShorttermProvisionForDecommissioningRestorationAndRehabilitationCosts | 3 | 0.25억 | 충당부채 |
| 유동성장기차입금 | LongtermBorrowings | 비유동 표준ID가 유동 canonical에 흡수 | CurrentPortionOfLongtermBorrowings, CurrentPortionOfNoncurrentBorrowings | 3 | 15,392억 | 유동성장기부채, 유동성장기차입금 |
| FVPL금융자산 | CurrentAvailableForSaleFinancialAssets | 이종 측정종류(매도가능) ↔ 등록(['FVPL']) | FinancialAssetsMeasuredAtFairValueThroughProfitOrLoss | 2 | 32억 | 당기손익-공정가치측정금융자산 |
| 상각후원가금융자산 | CurrentFinancialAssetsHeldToMaturity | 이종 측정종류(만기보유) ↔ 등록(['상각후원가']) | FinancialAssetsMeasuredAtAmortisedCost | 2 | 28억 | 상각후원가측정금융자산 |
| 사채 | CurrentPortionOfBondWithWarrant | 유동 표준ID가 비유동 canonical에 흡수 | BondsIssued, NoncurrentPortionOfNoncurrentBondsIssued | 2 | 348억 | 사채 |
| 사채 | CurrentPortionOfExchangeableBond | 유동 표준ID가 비유동 canonical에 흡수 | BondsIssued, NoncurrentPortionOfNoncurrentBondsIssued | 2 | 151억 | 사채 |
| 미지급금 | LongTermOtherPayablesNet | 비유동 표준ID가 유동 canonical에 흡수 | OtherCurrentPayables | 2 | 90억 | 미지급금 |
| 종속기업투자 | NonCurrentAvailableForSaleFinancialAssets | 이종 측정종류(매도가능) ↔ 등록(['지분법']) | InvestmentsInSubsidiaries | 2 | 304억 | 종속기업투자주식 |
| 상각후원가금융자산 | NonCurrentFinancialAssetsHeldToMaturity | 이종 측정종류(만기보유) ↔ 등록(['상각후원가']) | FinancialAssetsMeasuredAtAmortisedCost | 2 | 0.01억 | 상각후원가 측정 금융자산 |
| 매입채무및기타유동채무 | ShortTermCollectionWithholdings | 통합(AndOther)↔순수 불일치 | TradeAndOtherCurrentPayables, TradeAndOtherCurrentPayables | 2 | 4,434억 | 매입채무및기타채무 |
| 사채 | CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings | 유동 표준ID가 비유동 canonical에 흡수 | BondsIssued, NoncurrentPortionOfNoncurrentBondsIssued | 2 | 3,197억 | 사채 |
| 장기차입금 | CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings | 유동 표준ID가 비유동 canonical에 흡수 | LongTermBorrowingsGross, NoncurrentPortionOfNoncurrentLoansReceived | 2 | 9,031억 | 장기차입금 |
| 매출채권및기타유동채권 | CurrentTaxAssets | 통합(AndOther)↔순수 불일치 | TradeAndOtherCurrentReceivables, TradeAndOtherCurrentReceivables | 2 | 9,740억 | 매출채권및기타채권 |
| 선수금 | NoncurrentAdvances | 비유동 표준ID가 유동 canonical에 흡수 | CurrentAdvances, ShortTermAdvancesCustomers | 2 | 11억 | 선수금 |
| FVOCI금융자산 | NoncurrentFinancialAssetsAtFairValueThroughProfitOrLossMandatorilyMeasuredAtFairValue | 이종 측정종류(FVPL) ↔ 등록(['FVOCI']) | FinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome | 2 | 37억 | 기타포괄손익공정가치측정금융자산 |
| 충당부채 | OtherNoncurrentFinancialLiabilities | 비유동 표준ID가 유동 canonical에 흡수 | CurrentProvisions, CurrentProvisions, OtherShorttermProvisions, ShorttermMiscellaneousOtherProvisions, ShorttermMiscellaneousOtherProvisions, ShorttermProvisionForDecommissioningRestorationAndRehabilitationCosts | 2 | 0.77억 | 충당부채 |
| FVOCI금융자산 | CurrentAvailableForSaleFinancialAssets | 이종 측정종류(매도가능) ↔ 등록(['FVOCI']) | FinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome | 1 | 0.00억 | 기타포괄손익-공정가치 측정 금융자산 |
| FVPL금융자산 | DebtSecuritiesAtFairValueThroughOtherComprehensiveIncome | 이종 측정종류(FVOCI) ↔ 등록(['FVPL']) | FinancialAssetsMeasuredAtFairValueThroughProfitOrLoss | 1 | 8억 | 당기손익-공정가치측정금융자산 |
| 유동성장기차입금 | PresentValueDiscountsLongTermBorrowingsGross | 비유동 표준ID가 유동 canonical에 흡수 | CurrentPortionOfLongtermBorrowings, CurrentPortionOfNoncurrentBorrowings | 1 | 794억 | 유동성장기차입금 |
| 상각후원가금융자산 | SeparateAccountDerivativeFinancialAssetsHeldForTrading | 이종 측정종류(FVPL) ↔ 등록(['상각후원가']) | FinancialAssetsMeasuredAtAmortisedCost | 1 | 2억 | 상각후원가측정금융자산 |
| 기타유동자산 | CurrentPrepaymentsAndOtherCurrentAssets | 통합(AndOther)↔순수 불일치 | OtherCurrentAssets | 1 | 4억 | 기타유동자산 |
| 매입채무및기타유동채무 | OtherNoncurrentLiabilities | 비유동 표준ID가 유동 canonical에 흡수 | TradeAndOtherCurrentPayables, TradeAndOtherCurrentPayables | 1 | 8억 | 매입채무 및 기타채무 |
| 매입채무및기타유동채무 | TradeAndOtherPayablesToTradeSuppliers | 통합(AndOther)↔순수 불일치 | TradeAndOtherCurrentPayables, TradeAndOtherCurrentPayables | 1 | 493억 | 매입채무 및 기타채무 |
| 계약자산 | NoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleOrAsHeldForDistributionToOwners | 비유동 표준ID가 유동 canonical에 흡수 | ContractAssets, CurrentContractAssets, ShortTermDueFromCustomersForContractWork | 1 | 5,366억 | 미청구공사 |

## 3. 수동확인 (등록ID 없음/판정보류)

| canonical | 흡수된 표준ID | 사유 | 행수 | 최대금액 | 예시 라벨 |
|---|---|---|--:|--:|---|
| 매입채무 | ShortTermTradePayables | 등록ID와 다른 표준개념 — 수동확인 | 1678 | 65,235,382억 | 매입채무 |
| 배당변동 | AnnualDividendsPaid | 등록ID와 다른 표준개념 — 수동확인 | 1525 | 16,630억 | 연차배당 |
| 자기주식변동 | SaleOrIssueOfTreasuryShares | 등록ID와 다른 표준개념 — 수동확인 | 940 | 50,281억 | 자기주식의 처분, 자기주식처분 |
| 자본금변동 | ProceedsFromPaidinCapitalIncrease | 등록ID와 다른 표준개념 — 수동확인 | 788 | 15,410억 | 유상증자 |
| FVPL금융자산 | NoncurrentFinancialAssetsAtFairValueThroughProfitOrLossDesignatedUponInitialRecognition | 등록ID와 다른 표준개념 — 수동확인 | 641 | 9,208,899억 | 당기손익-공정가치 측정  금융자산, 당기손익-공정가치 측정 금융자산 |
| 미지급금 | ShortTermOtherPayables | 등록ID와 다른 표준개념 — 수동확인 | 614 | 97,314억 | 미지급금 |
| 자기주식변동 | DispositionOfTreasuryShares | 등록ID와 다른 표준개념 — 수동확인 | 599 | 458억 | 자기주식의 처분 |
| 이익잉여금변동 | StockDividends | alias-only canonical(등록ID 없음) — 표준명 수동확인 | 572 | 88억 | 주식배당 |
| 무형자산 | OtherIntangibleAssetsGross | 등록ID와 다른 표준개념 — 수동확인 | 538 | 127,090억 | 무형자산 |
| 순확정급여부채 | NoncurrentRecognisedLiabilitiesDefinedBenefitPlan | 등록ID와 다른 표준개념 — 수동확인 | 434 | 18,244억 | 순확정급여부채 |
| 미지급비용 | ShortTermAccruedExpenses | 등록ID와 다른 표준개념 — 수동확인 | 420 | 25,313억 | 미지급비용 |
| FVPL금융자산 | CurrentFinancialAssetsAtFairValueThroughProfitOrLossMandatorilyMeasuredAtFairValue | 등록ID와 다른 표준개념 — 수동확인 | 409 | 6,511억 | 당기손익-공정가치 측정 금융자산, 당기손익-공정가치측정 금융자산 |
| 자본잉여금변동 | CompoundFinancialInstrumentConversion | alias-only canonical(등록ID 없음) — 표준명 수동확인 | 363 | 699억 | 전환권 행사 |
| 장기차입금 | LongtermBorrowings | 등록ID와 다른 표준개념 — 수동확인 | 323 | 163,746억 | 장기차입금 |
| FVPL금융자산 | FinancialAssetsAtFairValueThroughProfitOrLoss | 등록ID와 다른 표준개념 — 수동확인 | 319 | 770,383억 | 당기손익-공정가치측정금융자산 |
| 순확정급여부채 | RecognisedLiabilitiesDefinedBenefitPlan | 등록ID와 다른 표준개념 — 수동확인 | 309 | 22,865억 | 순확정급여부채 |
| FVPL금융자산 | NoncurrentFinancialAssetsAtFairValueThroughProfitOrLossMandatorilyMeasuredAtFairValue | 등록ID와 다른 표준개념 — 수동확인 | 308 | 2,852,042억 | 당기손익-공정가치 측정 금융자산, 당기손익-공정가치측정 금융자산 |
| FVPL금융자산 | CurrentFinancialAssetsAtFairValueThroughProfitOrLossDesignatedUponInitialRecognition | 등록ID와 다른 표준개념 — 수동확인 | 284 | 12,245억 | 당기손익-공정가치 측정 금융자산, 당기손익-공정가치측정 금융자산 |
| FVOCI금융자산 | FinancialAssetsAtFairValueThroughOtherComprehensiveIncome | 등록ID와 다른 표준개념 — 수동확인 | 259 | 1,676,647억 | 기타포괄손익-공정가치측정금융자산 |
| 자본금변동 | SubscriptionOnNewStocks | 등록ID와 다른 표준개념 — 수동확인 | 250 | 976억 | 유상증자 |
| 판매비와관리비 | SellingGeneralAndAdministrativeExpense | 등록ID와 다른 표준개념 — 수동확인 | 242 | 49,231억 | 판매비와관리비 |
| FVPL금융자산 | NoncurrentFinancialAssetsAtFairValueThroughProfitOrLoss | 등록ID와 다른 표준개념 — 수동확인 | 239 | 318,875억 | 당기손익-공정가치 측정 금융자산, 당기손익-공정가치측정금융자산 |
| 지분법이익 | ProfitsOfAssociatesAndJointVenturesAccountedForUsingEquityMethod | 등록ID와 다른 표준개념 — 수동확인 | 237 | 3,757억 | 지분법이익 |
| 이자지급 | InterestPaidClassifiedAsFinancingActivities | 등록ID와 다른 표준개념 — 수동확인 | 236 | 13,883억 | 이자의 지급 |
| 확정급여부채 | PresentValueOfDefinedBenefitObligation | 등록ID와 다른 표준개념 — 수동확인 | 234 | 963억 | 확정급여부채, 확정급여채무 |
| FVPL금융자산 | NonCurrentFairValueFinancialAsset | 등록ID와 다른 표준개념 — 수동확인 | 225 | 22,273억 | 당기손익-공정가치 측정 금융자산, 당기손익-공정가치측정금융자산 |
| 이자비용 | InterestExpenseFinanceExpense | 등록ID와 다른 표준개념 — 수동확인 | 216 | 4,897억 | 이자비용 |
| 이연법인세자산 | NetDeferredTaxAssets | 등록ID와 다른 표준개념 — 수동확인 | 212 | 35,209억 | 이연법인세자산 |
| FVOCI평가손익 | OtherComprehensiveIncomeNetOfTaxChangeInFairValueOfFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome | 등록ID와 다른 표준개념 — 수동확인 | 201 | 55,810억 | 기타포괄손익-공정가치금융자산평가손익, 기타포괄손익-공정가치측정금융자산평가손익 |
| 상각후원가금융자산 | NoncurrentFinancialAssetsAtAmortisedCost | 등록ID와 다른 표준개념 — 수동확인 | 195 | 267,628억 | 상각후원가 측정 금융자산, 상각후원가측정금융자산 |
| 해외사업환산손익 | OtherComprehensiveIncomeNetOfTaxExchangeDifferencesOnTranslation | 등록ID와 다른 표준개념 — 수동확인 | 190 | 11,113억 | 해외사업환산손익 |
| 충당부채 | Provisions | 등록ID와 다른 표준개념 — 수동확인 | 186 | 14,444억 | 충당부채 |
| 이자비용 | InterestExpense | 등록ID와 다른 표준개념 — 수동확인 | 185 | 170,034억 | 이자비용 |
| 이연법인세부채 | NetDeferredTaxLiabilities | 등록ID와 다른 표준개념 — 수동확인 | 171 | 22,853억 | 이연법인세부채 |
| 단기차입금 | CurrentLoansReceivedAndCurrentPortionOfNoncurrentLoansReceived | 등록ID와 다른 표준개념 — 수동확인 | 169 | 51,671억 | 단기차입금 |
| 상각후원가금융자산 | CurrentFinancialAssetsAtAmortisedCost | 등록ID와 다른 표준개념 — 수동확인 | 167 | 185,576억 | 상각후원가 측정 금융자산, 상각후원가측정금융자산 |
| 계약부채 | CurrentFirmCommitmentLiabilities | 등록ID와 다른 표준개념 — 수동확인 | 164 | 2,756억 | 계약부채, 유동확정계약부채 |
| 이자수취 | InterestReceivedClassifiedAsInvestingActivities | 등록ID와 다른 표준개념 — 수동확인 | 163 | 3,361억 | 이자의 수취 |
| 배당변동 | StockDividends | 등록ID와 다른 표준개념 — 수동확인 | 162 | 681억 | 연차배당 |
| FVPL금융자산 | CurrentFinancialAssetsAtFairValueThroughProfitOrLoss | 등록ID와 다른 표준개념 — 수동확인 | 159 | 260,571억 | 당기손익-공정가치 측정 금융자산, 당기손익-공정가치측정금융자산 |
| 사채 | BondsIssuedNominalValue | 등록ID와 다른 표준개념 — 수동확인 | 147 | 71,063억 | 사채 |
| 순확정급여부채 | PresentValueOfDefinedBenefitObligation | 등록ID와 다른 표준개념 — 수동확인 | 147 | 4,688억 | 순확정급여부채 |
| 확정급여부채 | NoncurrentRecognisedLiabilitiesDefinedBenefitPlan | 등록ID와 다른 표준개념 — 수동확인 | 143 | 1,097억 | 확정급여부채, 확정급여채무 |
| 계약자산 | CurrentFirmCommitmentAsset | 등록ID와 다른 표준개념 — 수동확인 | 130 | 11,923억 | 계약자산, 유동확정계약자산 |
| 자본금변동 | BonusIssue | 등록ID와 다른 표준개념 — 수동확인 | 126 | 1,160억 | 유상증자 |
| 기타자본변동 | SubscriptionOnNewStocks | 등록ID와 다른 표준개념 — 수동확인 | 122 | 61억 | 신주인수권 행사 |
| 확정급여재측정손익 | OtherComprehensiveIncomeBeforeTaxGainsLossesOnRemeasurementsOfDefinedBenefitPlans | 등록ID와 다른 표준개념 — 수동확인 | 122 | 4,184억 | 확정급여제도의 재측정요소 |
| 자본금변동 | StockRedemption | 등록ID와 다른 표준개념 — 수동확인 | 119 | 32,998억 | 유상증자 |
| 자기주식변동 | PurchaseDisposalsOfOddShares | 등록ID와 다른 표준개념 — 수동확인 | 116 | 1,705억 | 자기주식 처분 |
| 유동성사채 | CurrentBondsIssuedAndCurrentPortionOfNoncurrentBondsIssued | 등록ID와 다른 표준개념 — 수동확인 | 113 | 13,134억 | 유동성 사채, 유동성사채 |
| FVOCI평가손익 | GainsLossesOnFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncomeNetOfTax | 등록ID와 다른 표준개념 — 수동확인 | 113 | 55,791억 | 기타포괄손익-공정가치 측정 금융자산 평가손익, 기타포괄손익-공정가치측정 금융자산평가손익 |
| 매출 | RevenueFromSaleOfGoods | 등록ID와 다른 표준개념 — 수동확인 | 112 | 16,993억 | 재화의 판매로 인한 수익(매출액) |
| FVOCI금융자산 | NoncurrentInvestmentsInEquityInstrumentsDesignatedAtFairValueThroughOtherComprehensiveIncome | 등록ID와 다른 표준개념 — 수동확인 | 109 | 162,950억 | 기타포괄손익-공정가치 금융자산, 기타포괄손익-공정가치금융 자산 |
| 비유동FVPL금융자산 | NoncurrentFinancialAssetsAtFairValueThroughProfitOrLossDesignatedUponInitialRecognition | 등록ID와 다른 표준개념 — 수동확인 | 105 | 2,492억 | 비유동 당기손익-공정가치 측정 금융자산, 비유동당기손익-공정가치측정금융자산 |
| FVOCI평가손익 | OtherComprehensiveIncomeNetOfTaxGainsLossesOnRevaluation | 등록ID와 다른 표준개념 — 수동확인 | 104 | 1,524억 | 기타포괄손익 -공정가치 금융자산평가손익, 기타포괄손익-공정가치 측정 금융자산 평가손익 |
| 기타비용 | NonOperatingExpense | 등록ID와 다른 표준개념 — 수동확인 | 102 | 1,329억 | 기타비용 |
| 이익잉여금변동 | IncreaseDecreaseThroughTransfersAndOtherChangesEquity | alias-only canonical(등록ID 없음) — 표준명 수동확인 | 98 | 600억 | 결손금보전 |
| 기타수익 | NonOperatingIncome | 등록ID와 다른 표준개념 — 수동확인 | 95 | 861억 | 기타수익 |
| 상각후원가금융자산 | FinancialAssetsAtAmortisedCost | 등록ID와 다른 표준개념 — 수동확인 | 95 | 827,747억 | 상각후원가측정금융자산 |
| 재고자산 | InventoriesTotal | 등록ID와 다른 표준개념 — 수동확인 | 91 | 13,098억 | 재고자산 |

… 외 367쌍 (전체는 _audit_alias_mapped.json).

## 4. 등록누락·동일개념 (무해 — 등록 추가만 권장)

동일 stem(접두사만 차이)인 표준ID 61쌍, 7,069행. 같은 계정이라 소실 아님.
상위:

| canonical | 미등록 표준ID | 행수 |
|---|---|--:|
| 기타유동자산 | OtherCurrentAssets | 3172 |
| 기타자본변동 | IncreaseDecreaseThroughChangesInAccountingPolicies | 734 |
| 재분류불가능기타포괄손익 | OtherComprehensiveIncomeThatWillNotBeReclassifiedToProfitOrLossNetOfTax | 540 |
| 재분류가능기타포괄손익 | OtherComprehensiveIncomeThatWillBeReclassifiedToProfitOrLossNetOfTax | 231 |
| 사채 | BondsIssued | 146 |
| 당기순이익 | ProfitLoss | 98 |
| 자본총계 | Equity | 71 |
| 자본과부채총계 | EquityAndLiabilities | 71 |
| 부채총계 | Liabilities | 71 |
| 자산총계 | Assets | 69 |
| 매출원가 | CostOfSales | 69 |
| 유동자산 | CurrentAssets | 69 |
| 유동부채 | CurrentLiabilities | 69 |
| 금융수익 | FinanceIncome | 69 |
| 매출총이익 | GrossProfit | 69 |
| 재고자산 | Inventories | 69 |
| 비유동자산 | NoncurrentAssets | 69 |
| 비유동부채 | NoncurrentLiabilities | 69 |
| 유형자산 | PropertyPlantAndEquipment | 69 |
| 매출 | Revenue | 69 |
