# BACKTEST_REPORT — Stage1 결정론 백테스트

- 발굴 recall: 3/3
- 기존 단일 통합 top10 strict hit: 3/3
- 새 두 트랙 quota hit: 2/3
- 채점에서 `cfs_ofs_gap`은 구조적 노이즈로 제외했다. raw fired_signals에는 남긴다.
- mvp1 Tier 1 가드: `single_account_yoy` 채점 신호에서 CF 계정을 제외하고, `growth_divergence`는 양쪽 전년 기저가 동적 floor 이상·동일 부호일 때만 발화한다.
- `%/pp` 기반 신호의 normalized_strength는 `signal_strength_cap`으로 캡한다. raw 값은 증거로 보존한다.
- 채점 hit 규칙·신호 임계값·상위10 기준은 변경하지 않았다.
- 두 트랙 quota는 자산 대비 규모로 게시 칸을 나누는 보조 잣대이며, legacy top10 결과와 병기한다.

| 회사 | label | window | available | discovered | legacy_strict | track_hit | miss_reason | fired |
|---|---|---|---|---|---|---|---|---:|
| 티피씨메카트로닉스 | positive | [2015, 2016] | [2015, 2016] | True | True | True | None | 33 |
| 유네코 | positive | [2015, 2016, 2017, 2018, 2019] | [2017, 2018, 2019] | True | True | False | None | 55 |
| 본느 | positive | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | True | True | True | None | 97 |
| NAVER | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 85 |
| KT&G | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 60 |
| 오리온 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 64 |
| 한미반도체 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 53 |
| 영원무역 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 108 |

## 분식계정별 최고 강도와 순위
| 회사 | 분식계정 | status | 최고강도 | 순위 |
|---|---|---|---:|---:|
| 티피씨메카트로닉스 | 재고자산 | 포착 | 3.7033 | 2 |
| 티피씨메카트로닉스 | 매출원가 | 변동미미 | None | None |
| 유네코 | 매출채권 | 포착 | 3.3093 | 8 |
| 유네코 | 대손충당금 | 계정부재 | None | None |
| 유네코 | 차입금 | 상위10밖 | 1.9627 | 14 |
| 본느 | 재고자산 | 포착 | 5.2987 | 3 |
| 본느 | 충당부채 | 규모미달 | None | None |

## 두 트랙 분식계정 상태
| 회사 | 분식계정 | track_status | track | track_rank | 최고강도 |
|---|---|---|---|---:|---:|
| 티피씨메카트로닉스 | 재고자산 | 포착 | A | 2 | 3.7033 |
| 티피씨메카트로닉스 | 매출원가 | 변동미미 | None | None | None |
| 유네코 | 매출채권 | 상위10밖 | A | 7 | 3.3093 |
| 유네코 | 대손충당금 | 계정부재 | None | None | None |
| 유네코 | 차입금 | 상위10밖 | A | 10 | 1.9627 |
| 본느 | 재고자산 | 포착 | A | 2 | 5.2987 |
| 본느 | 충당부채 | 규모미달 | None | None | None |

## 정상 회사 채점 신호 상위 5
| 회사 | 채점신호수 | 상위5 | 잔여 아티팩트 후보 |
|---|---:|---|---|
| NAVER | 10 | 당기순이익 / growth_divergence / 10.0<br>유형자산취득 / growth_divergence / 10.0<br>관계기업투자 / single_account_yoy / 10.0<br>이익잉여금 / universal_yoy / 4.9364<br>지배기업소유주지분 / single_account_yoy / 4.3892 | 당기순이익 divergence -1840.96pp<br>유형자산취득 divergence -458.52pp<br>관계기업투자 YoY 1574.99 |
| KT&G | 9 | 당기순이익 / growth_divergence / 3.3887<br>매출채권 / growth_divergence / 2.6007<br>관계기업투자 / single_account_yoy / 1.6764<br>자기주식 / universal_yoy / 1.3106<br>기타비용 / single_account_yoy / 1.1812 | 없음 |
| 오리온 | 9 | 유형자산취득 / growth_divergence / 10.0<br>장기차입금 / growth_divergence / 8.2333<br>단기금융예치금 / universal_yoy / 3.7156<br>당기순이익 / growth_divergence / 1.7287<br>유동성장기차입금 / universal_yoy / 1.125 | 없음 |
| 한미반도체 | 10 | 당기순이익 / growth_divergence / 10.0<br>유형자산취득 / growth_divergence / 9.0807<br>관계기업투자 / universal_yoy / 7.8298<br>기타유동금융부채 / universal_yoy / 6.3564<br>재고자산 / growth_divergence / 4.7087 | 없음 |
| 영원무역 | 10 | 당기순이익 / growth_divergence / 6.6813<br>유형자산취득 / growth_divergence / 6.454<br>기타비용 / single_account_yoy / 4.8494<br>기타수익 / single_account_yoy / 4.5592<br>기타유동자산 / single_account_yoy / 4.4438 | 없음 |

## 한계
- LLM·외부검색 없이 L0~L2 숫자 신호만 본다.
- 새 임계값을 만들지 않고 기존 red_flags/universal 신호만 채점했다.
- cfs_ofs_gap은 자회사 구조가 있으면 넓게 발생하므로 발굴·strict 판정에서 제외했다.
- 중과실·연결특화·다년분식·단일연도 데이터는 Stage1 숫자 신호만으로 한계가 있다.
