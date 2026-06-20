# D-A 미분류 분류후보 군집 (전수)

> 읽기전용 감사 산출물. config/코드 미수정. 분류가치는 **제안**이며 단정·확정이 아니다.

재현: `PYTHONPATH=. uv run python data/backtest/_da_report.py` (입력=전수 산출물 `_audit_unmapped.json`). 회사수·금액중앙값 보강은 `PYTHONPATH=. uv run python data/backtest/_da_cluster.py`(raw 전수 재스캔).

## 1. 분모 확정 (전수 §10)

대상 = `_audit_unmapped.json`의 `classify_candidates` = 표준ID(ifrs-full_*/dart_*/ifrs_*) 보유하나 canonical 미매핑(OTHER)인 비차원 account_id. 운영 매핑 파이프라인(가드→`_dedupe_statement_rows`)으로 1667사·9319파일 전수 집계된 결과다.

```
전수 account_id 종수          : 2,106
  ├ 신규개념후보(config 미등록) : 2,080
  └ 타표문반복(config 등록ID)   : 26
군집 종수 합(미배정 0 증명)     : 2,106  (= 총 2,106 일치)
과제 명시 분모                  : 2,080
  → 차이 +26 = 타표문반복 26종이 포함된 것.
     과제 '2080종' = 신규개념후보(2080종)와 정확히 일치.
군집 수                         : 64
```

**플래그(요구4):** account_id가 config 등록 `account_ids`에 있으면 그 개념은 이미 어느 재무제표에 canonical로 존재(타 표문에서 반복 등장)이고, 없으면 어디에도 canonical 없는 신규개념 후보다. 판정은 account_id 표준명 기준(현 canonical 매핑 미참조 — 자기참조 금지).

## 2. 군집 축

- **주 sj_div**: account_id 행이 raw에서 가장 많이 쌓인 재무제표 구분(BS/IS/CIS/CF/SCE). 현 매핑이 아니라 데이터 분포로 판정.
- **개념계열**: account_id의 IFRS 영문 표준명을 토큰 규칙으로 판정(`*InvestingActivities`→투자활동흐름, `AdjustmentsFor*`→현금흐름조정, `*FinancialAssets`→기타금융자산, `*Tax*`→세금 등). 현 canonical 미참조.
- 금액은 원천 이상치(예: 일부 corp 자산 122,130조)가 있어 **행수·종수를 우선 지표**로 둔다(amax 미신뢰). 회사수·중앙값은 부가지표로 `_da_cluster.py` 재스캔 시 산출.

## 3. 군집표 (총행수 내림차순)

| # | 군집 (주sj / 개념계열) | 종수 | 총행수 | 신규/반복 | 가치(제안) |
|---|------------------------|-----:|-------:|:---------:|:----------:|
| 1 | CF / 현금흐름조정 | 343 | 76,406 | 343/0 | 높음 |
| 2 | CF / 기타금융자산 | 87 | 66,319 | 87/0 | 높음 |
| 3 | CF / 현금잔액·증감·환율효과 | 25 | 36,663 | 24/1 | 높음 |
| 4 | SCE / 자본구성요소 | 82 | 34,695 | 77/5 | 높음 |
| 5 | BS / 기타금융자산 | 137 | 31,458 | 137/0 | 높음 |
| 6 | CF / 차입·사채 | 31 | 21,852 | 31/0 | 높음 |
| 7 | CF / 투자활동흐름 | 93 | 20,793 | 93/0 | 높음 |
| 8 | BS / 기타금융부채 | 61 | 19,871 | 61/0 | 높음 |
| 9 | BS / 자본구성요소 | 47 | 18,906 | 47/0 | 높음 |
| 10 | CIS / 손익항목(수익·비용·손익) | 233 | 16,822 | 233/0 | 높음 |
| 11 | CF / 재무활동흐름 | 40 | 15,141 | 40/0 | 높음 |
| 12 | BS / 기타비금융부채 | 29 | 13,738 | 29/0 | 높음 |
| 13 | CIS / 세금(법인세·이연) | 81 | 10,921 | 81/0 | 높음 |
| 14 | CF / 비금융자산(유형·무형·재고) | 79 | 10,558 | 79/0 | 높음 |
| 15 | CF / 관계·종속기업투자 | 18 | 10,094 | 18/0 | 높음 |
| 16 | BS / 기타비금융자산 | 42 | 9,985 | 42/0 | 높음 |
| 17 | BS / 세금(법인세·이연) | 16 | 7,040 | 16/0 | 중간 |
| 18 | SCE / 기타포괄손익구성 | 14 | 6,493 | 11/3 | 중간 |
| 19 | SCE / 세금(법인세·이연) | 41 | 6,445 | 35/6 | 중간 |
| 20 | BS / 기타포괄손익구성 | 20 | 5,906 | 20/0 | 중간 |
| 21 | CF / 영업활동흐름 | 17 | 5,770 | 17/0 | 중간 |
| 22 | BS / 차입·사채 | 34 | 4,862 | 34/0 | 중간 |
| 23 | BS / 비금융자산(유형·무형·재고) | 72 | 4,050 | 72/0 | 중간 |
| 24 | CIS / 주당손익(EPS) | 13 | 3,590 | 13/0 | 중간 |
| 25 | BS / 충당부채·종업원급여 | 25 | 3,199 | 25/0 | 중간 |
| 26 | CF / 손익항목(수익·비용·손익) | 34 | 2,972 | 33/1 | 중간 |
| 27 | CIS / 비금융자산(유형·무형·재고) | 32 | 2,483 | 32/0 | 중간 |
| 28 | SCE / 기타금융자산 | 7 | 2,178 | 7/0 | 중간 |
| 29 | SCE / 관계·종속기업투자 | 9 | 2,135 | 8/1 | 중간 |
| 30 | BS / 손익항목(수익·비용·손익) | 32 | 1,729 | 32/0 | 중간 |
| 31 | CF / 기타포괄손익구성 | 7 | 1,695 | 7/0 | 중간 |
| 32 | CF / 자본구성요소 | 7 | 1,509 | 5/2 | 중간 |
| 33 | CIS / 기타금융자산 | 55 | 1,405 | 55/0 | 낮음 |
| 34 | CIS / 관계·종속기업투자 | 14 | 1,305 | 14/0 | 낮음 |
| 35 | BS / 기타개념 | 55 | 1,294 | 55/0 | 낮음 |
| 36 | SCE / 차입·사채 | 7 | 873 | 7/0 | 낮음 |
| 37 | CIS / 기타금융부채 | 14 | 538 | 14/0 | 낮음 |
| 38 | CIS / 충당부채·종업원급여 | 9 | 496 | 9/0 | 낮음 |
| 39 | CIS / 기타포괄손익구성 | 15 | 374 | 15/0 | 낮음 |
| 40 | CF / 기타개념 | 11 | 366 | 9/2 | 낮음 |
| 41 | CIS / 자본구성요소 | 7 | 301 | 7/0 | 낮음 |
| 42 | BS / 관계·종속기업투자 | 7 | 221 | 7/0 | 낮음 |
| 43 | SCE / 현금흐름조정 | 5 | 217 | 5/0 | 낮음 |
| 44 | CF / 기타금융부채 | 8 | 142 | 8/0 | 낮음 |
| 45 | CF / 충당부채·종업원급여 | 15 | 124 | 15/0 | 낮음 |
| 46 | CIS / 현금흐름조정 | 3 | 123 | 3/0 | 낮음 |
| 47 | CF / 세금(법인세·이연) | 8 | 118 | 6/2 | 낮음 |
| 48 | IS / 손익항목(수익·비용·손익) | 11 | 110 | 11/0 | 낮음 |
| 49 | SCE / 재무활동흐름 | 1 | 87 | 0/1 | 낮음 |
| 50 | CF / 기타비금융자산 | 11 | 74 | 11/0 | 낮음 |
| 51 | BS / 현금잔액·증감·환율효과 | 2 | 63 | 2/0 | 낮음 |
| 52 | IS / 비금융자산(유형·무형·재고) | 4 | 57 | 4/0 | 낮음 |
| 53 | CIS / 기타개념 | 9 | 55 | 9/0 | 낮음 |
| 54 | SCE / 충당부채·종업원급여 | 6 | 48 | 6/0 | 낮음 |
| 55 | CIS / 기타비금융자산 | 4 | 37 | 4/0 | 낮음 |
| 56 | CIS / 차입·사채 | 2 | 31 | 2/0 | 낮음 |
| 57 | SCE / 비금융자산(유형·무형·재고) | 2 | 27 | 2/0 | 낮음 |
| 58 | IS / 주당손익(EPS) | 3 | 26 | 3/0 | 낮음 |
| 59 | IS / 관계·종속기업투자 | 1 | 10 | 1/0 | 낮음 |
| 60 | BS / 현금흐름조정 | 3 | 7 | 3/0 | 낮음 |
| 61 | CF / 기타비금융부채 | 2 | 6 | 2/0 | 낮음 |
| 62 | IS / 현금흐름조정 | 1 | 4 | 1/0 | 낮음 |
| 63 | SCE / 투자활동흐름 | 2 | 3 | 0/2 | 낮음 |
| 64 | SCE / 기타금융부채 | 1 | 2 | 1/0 | 낮음 |

종수 합계 = 2,106 (= 전수 2,106, 미배정 0)

## 4. 분류가치 제안 요약 (단정 금지 — 토의 입력)

### 가치 높음: 군집 16개 · 종수 1,428 · 행수 414,222
- 기준(제안): 행수 많고 신규개념 비중 큼 — canonical 추가 시 분류율 기여 큼(제안)
- 군집: CF / 현금흐름조정, CF / 기타금융자산, CF / 현금잔액·증감·환율효과, SCE / 자본구성요소, BS / 기타금융자산, CF / 차입·사채, CF / 투자활동흐름, BS / 기타금융부채, BS / 자본구성요소, CIS / 손익항목(수익·비용·손익) …

### 가치 중간: 군집 16개 · 종수 380 · 행수 62,056
- 기준(제안): 중간 규모 — 개념 정의·표문 의미 토의 후 선별 등록(제안)
- 군집: BS / 세금(법인세·이연), SCE / 기타포괄손익구성, SCE / 세금(법인세·이연), BS / 기타포괄손익구성, CF / 영업활동흐름, BS / 차입·사채, BS / 비금융자산(유형·무형·재고), CIS / 주당손익(EPS), BS / 충당부채·종업원급여, CF / 손익항목(수익·비용·손익) …

### 가치 낮음: 군집 32개 · 종수 298 · 행수 8,544
- 기준(제안): 희소하거나 타표반복(이미 canonical 보유) 비중 큼 — 우선순위 낮음(제안)
- 군집: CIS / 기타금융자산, CIS / 관계·종속기업투자, BS / 기타개념, SCE / 차입·사채, CIS / 기타금융부채, CIS / 충당부채·종업원급여, CIS / 기타포괄손익구성, CF / 기타개념, CIS / 자본구성요소, BS / 관계·종속기업투자 …

## 5. 대표 군집 상세 (상위 12 · 대표 account_id 5개)

행수=전수. flag=신규개념후보/타표문반복. id=IFRS 영문 표준명(local).

### CF / 현금흐름조정  — 종수 343, 행수 76,406, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  5,445  AdjustmentsForReconcileProfitLoss              | 당기순이익조정을 위한 가감 [신규]
  1,972  AdjustmentsForIncomeTaxExpense                 | 법인세비용 [신규]
  1,897  AdjustmentsForDecreaseIncreaseInInventories    | 재고자산의 감소(증가) [신규]
  1,808  AdjustmentsForLossesOnForeignExchangeTransl... | 외화환산손실 [신규]
  1,808  AdjustmentsForProvisionForSeveranceIndemnities | 퇴직급여 [신규]
```

### CF / 기타금융자산  — 종수 87, 행수 66,319, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  5,152  IncreaseInGuaranteeDeposits                    | 임차보증금의 증가 [신규]
  5,126  DecreaseInGuaranteeDeposits                    | 임차보증금의 감소 [신규]
  5,075  ProceedsFromSalesOfShortTermFinancialInstru... | 단기금융상품의 처분 [신규]
  4,975  PurchaseOfShortTermFinancialInstruments        | 단기금융상품의 취득 [신규]
  3,117  PurchaseOfLongTermFinancialInstruments         | 장기금융상품의 취득 [신규]
```

### CF / 현금잔액·증감·환율효과  — 종수 25, 행수 36,663, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  9,285  CashAndCashEquivalentsAtBeginningOfPeriodCf    | 기초현금및현금성자산 [신규]
  9,085  CashAndCashEquivalentsAtEndOfPeriodCf          | 기말현금및현금성자산 [신규]
  7,028  EffectOfExchangeRateChangesOnCashAndCashEqu... | 현금및현금성자산에 대한 환율변동효과 [신규]
  6,678  IncreaseDecreaseInCashAndCashEquivalents       | 현금및현금성자산의순증가(감소) [신규]
  3,606  IncreaseDecreaseInCashAndCashEquivalentsBef... | 환율변동효과 반영전 현금및현금성자산의 순증가(감소) [신규]
```

### SCE / 자본구성요소  — 종수 82, 행수 34,695, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
 12,142  ProfitLoss                                     | 당기순이익(손실) [반복:당기순이익]
  9,244  Equity                                         | 자본총계 [반복:자본총계]
  1,455  IncreaseDecreaseThroughSharebasedPaymentTra... | 주식기준보상거래에 따른 증가(감소), 지분 [신규]
  1,202  IncreaseDecreaseThroughTransfersAndOtherCha... | 기타변동에 따른 증가(감소), 자본 [신규]
  1,000  ChangesInEquity                                | 자본 증가(감소) 합계 [신규]
```

### BS / 기타금융자산  — 종수 137, 행수 31,458, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  5,796  OtherNoncurrentFinancialAssets                 | 기타비유동금융자산 [신규]
  5,423  OtherCurrentFinancialAssets                    | 기타유동금융자산 [신규]
  3,416  LongTermDepositsNotClassifiedAsCashEquivalents | 장기금융상품 [신규]
  3,358  LongTermTradeAndOtherNonCurrentReceivablesG... | 장기매출채권 및 기타비유동채권 [신규]
  1,229  CurrentDerivativeAsset                         | 유동파생상품자산 [신규]
```

### CF / 차입·사채  — 종수 31, 행수 21,852, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  5,840  ProceedsFromShortTermBorrowings                | 단기차입금의 증가 [신규]
  5,705  RepaymentsOfShortTermBorrowings                | 단기차입금의 상환 [신규]
  1,848  ProceedsFromConvertibleBonds                   | 전환사채의 증가 [신규]
  1,653  RepaymentsOfBonds                              | 사채의 상환 [신규]
  1,612  ProceedsFromBonds                              | 사채의 증가 [신규]
```

### CF / 투자활동흐름  — 종수 93, 행수 20,793, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  4,542  ProceedsFromSalesOfIntangibleAssetsClassifi... | 무형자산의 처분 [신규]
  2,233  ProceedsFromGovernmentGrantsClassifiedAsInv... | 정부보조금의 수취 [신규]
  1,173  ProceedsFromSalesOfNonCurrentAssetsOrDispos... | 매각예정자산의 처분 [신규]
  1,157  PaymentForStockIssueCost                       | 신주발행비 지급 [신규]
  1,124  ProceedsFromExerciseOfShareOptions             | 주식선택권행사로 인한 현금유입 [신규]
```

### BS / 기타금융부채  — 종수 61, 행수 19,871, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  4,652  OtherCurrentFinancialLiabilities               | 기타유동금융부채 [신규]
  4,207  OtherNoncurrentFinancialLiabilities            | 기타비유동금융부채 [신규]
  2,729  LongTermTradeAndOtherNonCurrentPayables        | 장기매입채무 및 기타비유동채무 [신규]
  1,973  CurrentDerivativeLiabilities                   | 유동파생상품부채 [신규]
    810  NonCurrentDerivativeLiabilities                | 비유동파생상품부채 [신규]
```

### BS / 자본구성요소  — 종수 47, 행수 18,906, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  7,167  ElementsOfOtherStockholdersEquity              | 기타자본구성요소 [신규]
  6,956  CapitalSurplus                                 | 자본잉여금 [신규]
    712  OtherCapitalAdjustments                        | 자본조정 [신규]
    685  IssuedCapitalOfCommonStock                     | 보통주자본금 [신규]
    666  TreasuryShares                                 | 자기주식 [신규]
```

### CIS / 손익항목(수익·비용·손익)  — 종수 233, 행수 16,822, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  1,427  ProfitLossFromContinuingOperations             | 계속영업이익(손실) [신규]
  1,150  ProfitLossFromDiscontinuedOperations           | 중단영업이익(손실) [신규]
    402  InterestIncomeFinanceIncome                    | 이자수익 [신규]
    369  RevenueFromSaleOfGoodsProduct                  | 제품매출액 [신규]
    355  CostOfSalesFromSaleOfGoodsProduct              | 제품매출원가 [신규]
```

### CF / 재무활동흐름  — 종수 40, 행수 15,141, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  3,077  PaymentsOfFinanceLeaseLiabilitiesClassified... | 리스부채의 상환 [신규]
  2,285  PaymentsOfFinanceLeaseLiabilitiesClassified... | 리스부채의 상환 [신규]
  2,044  RepaymentsOfBorrowingsClassifiedAsFinancing... | 차입금의 상환 [신규]
  1,773  ProceedsFromIssuingShares                      | 유상증자 [신규]
  1,322  PaymentsOfLeaseLiabilitiesClassifiedAsFinan... | 리스부채의 상환 [신규]
```

### BS / 기타비금융부채  — 종수 29, 행수 13,738, 가치(제안) 높음
```
     행수  account_id(local)                               | 예시라벨 [flag]
  4,826  OtherCurrentLiabilities                        | 기타 유동부채 [신규]
  3,350  OtherCurrentLiabilities                        | 기타유동부채 [신규]
  2,624  OtherNoncurrentLiabilities                     | 기타 비유동 부채 [신규]
  1,778  OtherNonCurrentLiabilities                     | 기타비유동부채 [신규]
    293  LiabilitiesIncludedInDisposalGroupsClassifi... | 매각예정부채 [신규]
```

## 6. 한계·주의

- 개념계열은 IFRS 영문명 토큰 규칙이라 일부 복합명은 근사 분류된다. '기타개념'은 규칙 미적중 잔여이며 분류불가가 아니라 **추가 정의 필요** 잔여다(종수 명시).
- CF 방향성 흐름은 활동어(`...Activities`)가 있으면 투자/재무활동으로, 없으면 그 계정의 자산·부채 성격(예: 차입·사채, 기타금융자산)으로 세분된다 — 의도된 분류다.
- **행수는 전수**지만, account_id별 **고유 회사수·금액 중앙값**은 본 표에 없다(`_audit_unmapped.json`에 미수록). 필요 시 `_da_cluster.py`로 raw 전수 재스캔하면 군집별 합집합 회사수·중앙값까지 산출된다(부가지표).
- 분류가치 버킷은 행수·신규비중 휴리스틱일 뿐, 등록 여부는 개념 정의·표문 의미 토의 후 사용자 결정(§8).

