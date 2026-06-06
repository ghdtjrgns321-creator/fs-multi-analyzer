# BACKTEST_REPORT — Stage1 결정론 백테스트

- 발굴 recall: 2/2
- 상위10 strict hit: 1/2
- 채점에서 `cfs_ofs_gap`은 구조적 노이즈로 제외했다. raw fired_signals에는 남긴다.
- mvp1 Tier 1 가드: `single_account_yoy` 채점 신호에서 CF 계정을 제외하고, `growth_divergence`는 양쪽 전년 기저가 동적 floor 이상·동일 부호일 때만 발화한다.
- `%/pp` 기반 신호의 normalized_strength는 `signal_strength_cap`으로 캡한다. raw 값은 증거로 보존한다.
- 채점 hit 규칙·신호 임계값·상위10 기준은 변경하지 않았다.

| 회사 | label | window | available | discovered | strict_hit | miss_reason | fired |
|---|---|---|---|---|---|---|---:|
| 이트론 | positive | [2017, 2018, 2019, 2020, 2021, 2022] | [2017, 2018, 2019, 2020, 2021, 2022] | True | True | None | 99 |
| 웨이브일렉트로닉스 | positive | [2015, 2016, 2017, 2018, 2019] | [2015, 2016, 2017, 2018, 2019] | True | False | 상위10밖 | 118 |
| 농심 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 82 |
| 빙그레 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 78 |
| 한섬 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 27 |
| 대한제강 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 110 |
| 인탑스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 95 |
| 동원F&B | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | 해당없음 | 83 |

## 분식계정별 최고 강도와 순위
| 회사 | 분식계정 | status | 최고강도 | 순위 |
|---|---|---|---:|---:|
| 이트론 | 무형자산 | 상위10밖 | 1.7028 | 27 |
| 이트론 | 관계기업투자 | 규모미달 | None | None |
| 이트론 | 당기순이익 | 포착 | 10.0 | 5 |
| 이트론 | 자기자본 | 계정부재 | None | None |
| 웨이브일렉트로닉스 | 무형자산 | 상위10밖 | 1.2536 | 29 |
| 웨이브일렉트로닉스 | 관계기업투자 | 변동미미 | None | None |
| 웨이브일렉트로닉스 | 당기순이익 | 상위10밖 | 2.2448 | 15 |
| 웨이브일렉트로닉스 | 자기자본 | 계정부재 | None | None |

## 정상 회사 채점 신호 상위 5
| 회사 | 채점신호수 | 상위5 | 잔여 아티팩트 후보 |
|---|---:|---|---|
| 농심 | 10 | 기타비용 / universal_yoy / 9.9386<br>단기차입금 / universal_yoy / 8.8324<br>유형자산취득 / growth_divergence / 8.7473<br>당기법인세자산 / universal_yoy / 8.0606<br>퇴직급여자산 / universal_yoy / 4.0098 | 없음 |
| 빙그레 | 10 | 비유동리스부채 / universal_yoy / 5.0732<br>당기순이익 / single_account_yoy / 4.7134<br>미수수익 / universal_yoy / 4.2824<br>재고자산 / growth_divergence / 4.0787<br>법인세비용차감전순이익 / single_account_yoy / 4.0428 | 없음 |
| 한섬 | 10 | 단기차입금 / universal_yoy / 10.0<br>순확정급여자산 / universal_yoy / 6.439<br>당기순이익 / growth_divergence / 4.6113<br>기타포괄손익누계액 / universal_yoy / 4.4582<br>기타유동자산 / universal_yoy / 2.2934 | 없음 |
| 대한제강 | 10 | 당기순이익 / growth_divergence / 10.0<br>비유동 기타포괄손익-공정가치 측정 금융자산 / universal_yoy / 10.0<br>순확정급여자산 / universal_yoy / 10.0<br>기타유동금융자산 / universal_yoy / 10.0<br>기타자본구성요소 / universal_yoy / 8.5376 | 순확정급여자산 YoY 1955.75 |
| 인탑스 | 10 | 당기순이익 / growth_divergence / 5.736<br>기타채권 / universal_yoy / 4.305<br>장기기타채무 / universal_yoy / 3.8584<br>기타비유동자산 / universal_yoy / 3.5446<br>매출채권 / growth_divergence / 3.362 | 없음 |
| 동원F&B | 10 | 단기금융상품 / universal_yoy / 10.0<br>장기차입금 / growth_divergence / 10.0<br>유동성사채 / universal_yoy / 9.197<br>당기순이익 / growth_divergence / 5.8607<br>당기손익-공정가치측정금융자산 / universal_yoy / 5.4224 | 없음 |

## 한계
- LLM·외부검색 없이 L0~L2 숫자 신호만 본다.
- 새 임계값을 만들지 않고 기존 red_flags/universal 신호만 채점했다.
- cfs_ofs_gap은 자회사 구조가 있으면 넓게 발생하므로 발굴·strict 판정에서 제외했다.
- 중과실·연결특화·다년분식·단일연도 데이터는 Stage1 숫자 신호만으로 한계가 있다.
