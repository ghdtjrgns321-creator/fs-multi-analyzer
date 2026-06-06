# BACKTEST_REPORT — Stage1 결정론 백테스트

- 발굴 recall: 0/0
- 상위10 strict hit: 0/0
- 채점에서 `cfs_ofs_gap`은 구조적 노이즈로 제외했다. raw fired_signals에는 남긴다.
- mvp1 Tier 1 가드: `single_account_yoy` 채점 신호에서 CF 계정을 제외하고, `growth_divergence`는 양쪽 전년 기저가 동적 floor 이상·동일 부호일 때만 발화한다.
- `%/pp` 기반 신호의 normalized_strength는 `signal_strength_cap`으로 캡한다. raw 값은 증거로 보존한다.
- 채점 hit 규칙·신호 임계값·상위10 기준은 변경하지 않았다.

| 회사 | label | window | available | discovered | strict_hit | miss_reason | fired |
|---|---|---|---|---|---|---|---:|
| 현대건설 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 90 |
| GS건설 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 91 |
| DL이앤씨 | clean | [2021, 2022, 2023] | [2021, 2022, 2023] | False | False | 해당없음 | 72 |
| HDC현대산업개발 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 80 |
| SK텔레콤 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 102 |
| KT | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 85 |
| LG유플러스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 47 |
| 한국전력공사 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 84 |
| 한국가스공사 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 84 |
| 엔씨소프트 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 73 |
| 크래프톤 | clean | [2021, 2022, 2023] | [2021, 2022, 2023] | False | False | 해당없음 | 43 |
| 카카오 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 112 |
| 펄어비스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 95 |
| 대한항공 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 79 |
| CJ대한통운 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 86 |
| 이마트 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 91 |
| 메가스터디교육 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 71 |

## 분식계정별 최고 강도와 순위
| 회사 | 분식계정 | status | 최고강도 | 순위 |
|---|---|---|---:|---:|

## 정상 회사 채점 신호 상위 5
| 회사 | 채점신호수 | 상위5 | 잔여 아티팩트 후보 |
|---|---:|---|---|
| 현대건설 | 10 | 당기순이익 / growth_divergence / 10.0<br>파생상품자산 / universal_yoy / 10.0<br>당기법인세부채 / universal_yoy / 7.3992<br>이연법인세부채 / universal_yoy / 4.8908<br>장기금융상품 / universal_yoy / 4.8488 | 파생상품자산 YoY 14143.19 |
| GS건설 | 10 | 지분법이익 / universal_yoy / 10.0<br>비지배지분순이익 / universal_yoy / 8.03<br>충당부채 / single_account_yoy / 5.2616<br>관계회사지분증권손익 / universal_yoy / 5.1244<br>당기순이익 / growth_divergence / 4.6587 | 없음 |
| DL이앤씨 | 10 | 장기금융상품 / universal_yoy / 10.0<br>기타 비유동 부채 / universal_yoy / 10.0<br>당기순이익 / growth_divergence / 7.0253<br>파생상품자산 / universal_yoy / 5.5318<br>단기금융상품 / single_account_yoy / 2.7412 | 없음 |
| HDC현대산업개발 | 10 | 투자부동산 / universal_yoy / 10.0<br>기타자본구성요소 / universal_yoy / 10.0<br>금융수익 / universal_yoy / 10.0<br>재고자산 / growth_divergence / 6.4287<br>이연법인세부채 / universal_yoy / 5.5786 | 투자부동산 YoY 8926.3<br>기타자본구성요소 YoY -1131.45 |
| SK텔레콤 | 10 | 기타자본구성요소 / universal_yoy / 10.0<br>이연법인세자산 / universal_yoy / 10.0<br>단기차입금 / universal_yoy / 10.0<br>확정급여자산 / universal_yoy / 10.0<br>유동파생금융자산 / universal_yoy / 9.194 | 기타자본구성요소 YoY 1731.73<br>이연법인세자산 YoY 5259.38<br>단기차입금 YoY 1000.15 |
| KT | 10 | 기타유동금융부채 / universal_yoy / 10.0<br>관계기업 및 공동기업 순손익 지분 / universal_yoy / 10.0<br>당기순이익 / growth_divergence / 6.0093<br>장기차입금 / growth_divergence / 5.3287<br>당기법인세자산 / universal_yoy / 3.7834 | 기타유동금융부채 YoY 2820.46 |
| LG유플러스 | 10 | 기타포괄손익누계액 / universal_yoy / 10.0<br>지분법이익 / universal_yoy / 5.5064<br>현금흐름위험회피파생부채 / universal_yoy / 4.8544<br>당기법인세부채 / universal_yoy / 3.8398<br>계속영업당기순이익 / universal_yoy / 3.735 | 없음 |
| 한국전력공사 | 10 | 매각예정자산 / universal_yoy / 10.0<br>매출총이익 / single_account_yoy / 10.0<br>순확정급여자산 / universal_yoy / 10.0<br>이연법인세자산 / universal_yoy / 9.4978<br>영업이익 / single_account_yoy / 9.1448 | 매각예정자산 YoY 1616.65 |
| 한국가스공사 | 10 | 당기법인세자산 / universal_yoy / 10.0<br>유동비금융부채 / universal_yoy / 10.0<br>당기순이익 / growth_divergence / 10.0<br>기타포괄손익누계액 / universal_yoy / 9.7292<br>비유동비금융자산 / universal_yoy / 9.1066 | 당기법인세자산 YoY 1300.87<br>당기순이익 divergence -659.42pp |
| 엔씨소프트 | 10 | 유형자산취득 / growth_divergence / 10.0<br>기타불입자본 / universal_yoy / 10.0<br>단기차입금 / universal_yoy / 10.0<br>재고자산 / universal_yoy / 10.0<br>이연법인세자산 / universal_yoy / 10.0 | 기타불입자본 YoY -4255.02<br>단기차입금 YoY 2653.34<br>이연법인세자산 YoY 1292.47 |
| 크래프톤 | 10 | 이연법인세부채 / universal_yoy / 10.0<br>당기법인세자산 / universal_yoy / 10.0<br>비지배지분 / universal_yoy / 10.0<br>이익잉여금 / universal_yoy / 10.0<br>기타비유동자산 / universal_yoy / 10.0 | 이연법인세부채 YoY 3310.3<br>당기법인세자산 YoY 1126.97 |
| 카카오 | 10 | 당기순이익 / growth_divergence / 10.0<br>장기차입금 / growth_divergence / 10.0<br>유형자산취득 / growth_divergence / 10.0<br>기타유동금융부채 / universal_yoy / 10.0<br>예치금 / universal_yoy / 10.0 | 당기순이익 divergence -840.33pp<br>기타유동금융부채 YoY 1830.78<br>예치금 YoY 1149.44 |
| 펄어비스 | 10 | 유형자산취득 / growth_divergence / 10.0<br>장기차입금 / single_account_yoy / 10.0<br>당기손익-공정가치측정금융자산 / universal_yoy / 10.0<br>관계기업투자 / universal_yoy / 10.0<br>기타비유동부채 / universal_yoy / 4.0554 | 유형자산취득 divergence -315.32pp<br>당기손익-공정가치측정금융자산 YoY 1924.5<br>관계기업투자 YoY 1442.23 |
| 대한항공 | 10 | 장기차입금 / growth_divergence / 10.0<br>이익잉여금 / universal_yoy / 10.0<br>단기금융상품 / single_account_yoy / 9.8436<br>당기순이익 / growth_divergence / 9.35<br>파생상품부채 / universal_yoy / 5.9814 | 이익잉여금 YoY 1765.68 |
| CJ대한통운 | 10 | 매각예정자산 / universal_yoy / 10.0<br>단기금융상품 / universal_yoy / 10.0<br>비지배지분순이익 / universal_yoy / 8.5688<br>유형자산취득 / growth_divergence / 5.6673<br>이연법인세자산 / universal_yoy / 5.4676 | 매각예정자산 YoY 12936.41<br>단기금융상품 YoY 1734.02 |
| 이마트 | 10 | 당기순이익 / growth_divergence / 10.0<br>비지배지분순이익 / universal_yoy / 10.0<br>단기파생상품자산 / universal_yoy / 10.0<br>순확정급여자산 / universal_yoy / 10.0<br>무형자산 / single_account_yoy / 7.3982 | 당기순이익 divergence -304.7pp<br>비지배지분순이익 YoY 2256.4<br>단기파생상품자산 YoY 2023.4 |
| 메가스터디교육 | 10 | 당기순이익 / growth_divergence / 10.0<br>유형자산취득 / growth_divergence / 10.0<br>당기법인세부채 / universal_yoy / 10.0<br>확정급여부채 / universal_yoy / 10.0<br>기타금융자산 / universal_yoy / 10.0 | 유형자산취득 divergence -838.44pp<br>당기법인세부채 YoY 1924.19<br>확정급여부채 YoY 1046.89 |

## 한계
- LLM·외부검색 없이 L0~L2 숫자 신호만 본다.
- 새 임계값을 만들지 않고 기존 red_flags/universal 신호만 채점했다.
- cfs_ofs_gap은 자회사 구조가 있으면 넓게 발생하므로 발굴·strict 판정에서 제외했다.
- 중과실·연결특화·다년분식·단일연도 데이터는 Stage1 숫자 신호만으로 한계가 있다.
