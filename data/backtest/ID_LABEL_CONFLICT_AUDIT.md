# id-label 의미 모순 전수 측정 (N5 1단계 — 측정만, 매핑 변경 없음)

> production 매퍼(map_row)의 id_label_conflict 플래그를 수집 전체 raw에 직접 적용해 집계.
> 매핑은 id-first 유지(무회귀). 본 측정이 2단계(규칙 결정)의 입력이다.

## 요약
- 스캔: 1667개 회사 / 4773 회사연도(raw 보유) / 본문 행 1,576,214
- 모순 행: **159,863건** (금액 |합| 112,266,569,861백만)
- 패턴 분포: ③완전이질 93,726 · ②유동비유동계열 65,422 · ①폐지개념 715
- 고유 canonical 쌍: 3,484종

## 측정 범위 주의 (해석 시 필수)
- **raw 기준 측정**: map_row의 모순 플래그만 적용(statement-guard 미적용). 실제 정규화 산출물에서는
  cross-statement 모순(IS id ↔ CF 라벨 등)이 `_apply_statement_guard`로 '기타'(UNMAPPED) 강등되어
  저장 `id_label_conflict`는 본 수치보다 적다. 본 측정은 "모순 총량"의 상한.
- **보수적 규칙**: label이 alias 사전에 **정확히** 일치할 때만 모순으로 센다(유사일치 제외). HTM 예시
  (00120526/2021 CF 308,172, label '기타포괄손익-공정가치 지분상품의 처분')는 label이 비등록 free-text라
  플래그 안 됨 — 자유서술 라벨은 본 측정에 안 잡힌다(역방향 오염 방지의 트레이드오프).
- ②/③ 다수는 표준 id가 라벨보다 정밀한 정상 id-first 케이스(예: 비유동리스부채 id ↔ '리스부채' 라벨).
  의미 오염 후보는 주로 ①폐지개념·③완전이질 일부 — 2단계는 ③ 표본 정독으로 진짜 오염을 가린다.

## 3패턴 분류표

| 패턴 | 건수 | 의미 |
|------|------|------|
| ①폐지개념 | 715 | IFRS9 폐지 분류(HTM·AFS) id에 다른 실질 신고 |
| ②유동비유동계열 | 65,422 | id·label이 유동/비유동·장단기 접두만 다른 같은 계열 |
| ③완전이질 | 93,726 | 서로 다른 계정 family(진짜 의미 오염 후보) |

## 상위 모순 canonical 쌍 (id ⟸ | label ⟹, 빈도순 30)

| 빈도 | id canonical | label canonical |
|------|--------------|-----------------|
| 5792 | 자본금변동 | 주식발행 |
| 4360 | 법인세비용 | 법인세비용조정 |
| 4152 | FVOCI적립금변동 | FVOCI지분상품평가손익 |
| 3696 | 비지배지분 | 비지배지분순이익 |
| 3567 | 회계정책변경효과 | 연결대상범위변동 |
| 2790 | 기타포괄손익(SCE) | 기타포괄손익 |
| 2418 | 법인세납부 | 법인세환급(납부) |
| 2363 | 해외사업환산손익(SCE) | 해외사업환산손익 |
| 2252 | 환율변동효과 | 해외사업환산손익 |
| 2223 | 당기순이익(손실) | 당기순이익 |
| 2214 | 법인세납부 | 법인세납부(환급) |
| 2076 | 지분법자본변동(SCE) | 지분법기타포괄손익재분류가능 |
| 1591 | 배당변동 | 배당금지급 |
| 1558 | 비지배지분총포괄손익 | 비지배지분순이익 |
| 1529 | 배당금의 지급 | 배당변동 |
| 1526 | 순확정급여부채 | 퇴직급여부채 |
| 1523 | 자기주식변동 | 자기주식취득 |
| 1492 | 비유동FVOCI금융자산 | FVOCI금융자산 |
| 1492 | 비유동리스부채 | 리스부채 |
| 1484 | 기타포괄손익-공정가치측정금융자산평가손익 | FVOCI지분상품평가손익 |
| 1233 | 기타유동금융자산 | 기타금융자산 |
| 1206 | 복합금융상품 전환 | 전환사채의 전환 |
| 1108 | 유상증자 | 주식발행 |
| 1004 | 기타비유동금융자산 | 기타금융자산 |
| 986 | 유동리스부채 | 리스부채 |
| 983 | 기타비용 | 기타영업외비용 |
| 951 | 기타유동금융부채 | 기타금융부채 |
| 940 | 장기충당부채 | 충당부채 |
| 912 | 기타수익 | 기타영업외수익 |
| 821 | 지배기업귀속총포괄손익 | 지배기업소유주지분 |

## ①폐지개념 — 금액 상위 12 예시

| 회사/연도 | fs/sj | label | account_id | id→canonical | label→canonical | 금액(백만) |
|---|---|---|---|---|---|---|
| 00265324/2025 | CFS/BS | 비유동매도가능금융자산 | ifrs-full_NoncurrentFinancialAssetsAvail | 비유동매도가능금융자산(BS) | 비유동매도가능금융자산 | 687,752 |
| 00265324/2021 | CFS/BS | 매도가능금융자산 | dart_NonCurrentAvailableForSaleFinancial | 비유동매도가능금융자산 | 매도가능금융자산 | 618,712 |
| 00265324/2020 | CFS/BS | 매도가능금융자산 | dart_NonCurrentAvailableForSaleFinancial | 비유동매도가능금융자산 | 매도가능금융자산 | 540,018 |
| 00265324/2024 | CFS/BS | 비유동매도가능금융자산 | ifrs-full_NoncurrentFinancialAssetsAvail | 비유동매도가능금융자산(BS) | 비유동매도가능금융자산 | 529,020 |
| 00265324/2022 | CFS/BS | 매도가능금융자산 | dart_NonCurrentAvailableForSaleFinancial | 비유동매도가능금융자산 | 매도가능금융자산 | 515,236 |
| 00265324/2023 | CFS/BS | 비유동매도가능금융자산 | ifrs-full_NoncurrentFinancialAssetsAvail | 비유동매도가능금융자산(BS) | 비유동매도가능금융자산 | 503,964 |
| 00265324/2025 | OFS/BS | 비유동매도가능금융자산 | ifrs-full_NoncurrentFinancialAssetsAvail | 비유동매도가능금융자산(BS) | 비유동매도가능금융자산 | 420,793 |
| 00265324/2024 | OFS/BS | 비유동매도가능금융자산 | ifrs-full_NoncurrentFinancialAssetsAvail | 비유동매도가능금융자산(BS) | 비유동매도가능금융자산 | 390,725 |
| 00265324/2021 | OFS/BS | 매도가능금융자산 | dart_NonCurrentAvailableForSaleFinancial | 비유동매도가능금융자산 | 매도가능금융자산 | 389,278 |
| 00265324/2022 | OFS/BS | 매도가능금융자산 | dart_NonCurrentAvailableForSaleFinancial | 비유동매도가능금융자산 | 매도가능금융자산 | 382,700 |
| 00265324/2023 | OFS/BS | 비유동매도가능금융자산 | ifrs-full_NoncurrentFinancialAssetsAvail | 비유동매도가능금융자산(BS) | 비유동매도가능금융자산 | 353,539 |
| 00549891/2023 | CFS/CF | 상각후원가측정금융자산의 취득 | dart_PurchaseOfFinancialAssetsHeldToMatu | 만기보유금융자산의 취득 | 상각후원가측정금융자산의 취득 | 325,272 |

## ②유동비유동계열 — 금액 상위 12 예시

| 회사/연도 | fs/sj | label | account_id | id→canonical | label→canonical | 금액(백만) |
|---|---|---|---|---|---|---|
| 00204226/2022 | CFS/CF | 당기순이익(손실) | dart_ProfitLossForStatementOfCashFlows | 당기순이익(손실) | 당기순이익 | 11,587,270,444 |
| 00204226/2022 | CFS/BS | 비지배지분 | ifrs-full_NoncontrollingInterests | 비지배지분 | 비지배지분순이익 | 10,861,823,430 |
| 00204226/2022 | OFS/CF | 당기순이익(손실) | dart_ProfitLossForStatementOfCashFlows | 당기순이익(손실) | 당기순이익 | 10,395,270,779 |
| 00204226/2022 | CFS/BS | 기타자산 | dart_OtherCurrentAssets | 기타유동자산 | 기타자산 | 1,066,327,881 |
| 00204226/2022 | OFS/BS | 기타자산 | dart_OtherCurrentAssets | 기타유동자산 | 기타자산 | 440,534,818 |
| 00158909/2025 | CFS/BS | 대출채권 | dart_LoansAtAmortisedCost | 상각후원가측정대출채권 | 대출채권 | 396,923,416 |
| 00158909/2025 | OFS/BS | 대출채권 | dart_LoansAtAmortisedCost | 상각후원가측정대출채권 | 대출채권 | 378,939,756 |
| 00158909/2024 | CFS/BS | 대출채권 | dart_LoansAtAmortisedCost | 상각후원가측정대출채권 | 대출채권 | 367,214,258 |
| 00158909/2024 | OFS/BS | 대출채권 | dart_LoansAtAmortisedCost | 상각후원가측정대출채권 | 대출채권 | 350,575,067 |
| 00158909/2023 | CFS/BS | 대출채권 | dart_LoansAtAmortisedCost | 상각후원가측정대출채권 | 대출채권 | 347,246,910 |
| 00158909/2023 | OFS/BS | 대출채권 | dart_LoansAtAmortisedCost | 상각후원가측정대출채권 | 대출채권 | 331,908,481 |
| 00160588/2025 | CFS/BS | 보험계약부채 | ifrs-full_InsuranceContractsThatAreLiabi | 보험계약부채(BS) | 보험계약부채 | 122,462,122 |

## ③완전이질 — 금액 상위 12 예시

| 회사/연도 | fs/sj | label | account_id | id→canonical | label→canonical | 금액(백만) |
|---|---|---|---|---|---|---|
| 00204226/2022 | CFS/BS | 유동성장기부채 | dart_CurrentPortionOfConvertibleBonds | 유동성전환사채 | 유동성장기차입금 | 15,262,170,935 |
| 00204226/2022 | OFS/BS | 유동성장기부채 | dart_CurrentPortionOfConvertibleBonds | 유동성전환사채 | 유동성장기차입금 | 15,262,170,935 |
| 00204226/2022 | CFS/BS | 관계기업투자 | ifrs-full_InvestmentAccountedForUsingEqu | 지분법적용투자 | 관계기업투자 | 5,197,684,536 |
| 00204226/2022 | CFS/CF | 법인세환급(납부) | ifrs-full_IncomeTaxesPaidRefundClassifie | 법인세납부 | 법인세환급(납부) | 2,267,888,474 |
| 00204226/2022 | CFS/CF | 파생상품평가이익 | dart_AdjustmentsForGainsOnEvaluationOfDe | 파생금융부채평가이익 | 파생상품평가이익 | 1,499,964,272 |
| 00204226/2022 | OFS/CF | 파생상품평가이익 | dart_AdjustmentsForGainsOnEvaluationOfDe | 파생금융부채평가이익 | 파생상품평가이익 | 1,499,964,272 |
| 00204226/2022 | CFS/CF | 기타수취채권의 감소(증가) | dart_AdjustmentsForDecreaseincreaseInTra | 매출채권 및 기타유동채권의 감소(증가) | 기타수취채권의 감소(증가) | -1,430,324,427 |
| 00204226/2022 | CFS/SCE | 해외사업환산손익 | dart_ChangesInForeignExchangeRates | 환율변동효과 | 해외사업환산손익 | -1,061,051,726 |
| 00204226/2022 | CFS/BS | 기타지급채무 | ifrs-full_TradeAndOtherCurrentPayables | 매입채무및기타유동채무 | 기타지급채무 | 945,571,174 |
| 00204226/2022 | CFS/BS | 당기손익-공정가치측정금융자산 | ifrs-full_NoncurrentFinancialAssetsAtFai | 비유동 당기손익-공정가치 측정 지정 금융자산 | FVPL금융자산 | 920,889,852 |
| 00204226/2022 | CFS/SCE | 해외사업환산손익 | dart_ChangesInForeignExchangeRates | 환율변동효과 | 해외사업환산손익 | -800,825,132 |
| 00204226/2022 | CFS/SCE | 해외사업환산손익 | dart_ChangesInForeignExchangeRates | 환율변동효과 | 해외사업환산손익 | -800,825,132 |

## 2단계 후보 규칙 (별도 회차 — 본 측정 보고 후 사용자 결정)
- ⓐ ①폐지개념 id → label 우선(안전: 폐지 id는 낡은 태깅 증거).
- ⓑ label 정확 alias 일치 시 label 우선.
- ⓒ 미해결 모순 → '기타 중요 계정' 강등+플래그.
- 측정 리포트 없이 선반영하지 않는다(매핑 동작 변경은 무회귀 검증 동반).
