# BACKTEST_REPORT — Stage1 결정론 백테스트

- 발굴 recall: 5/6
- 기존 단일 통합 top10 strict hit: 5/6
- 새 두 트랙 quota hit: 5/6
- 채점에서 `cfs_ofs_gap`은 구조적 노이즈로 제외했다. raw fired_signals에는 남긴다.
- 삼성전자 거짓양성 변화: 기존 raw 127 → 신규 raw 113, cfs_ofs_gap 제외 79, legacy 채점대상 10, track 채점대상 11
- KAI 반응: 분식계정 발굴 여부 False, legacy strict False, track False (변동미미)
- mvp1 Tier 1 가드: `single_account_yoy` 채점 신호에서 CF 계정을 제외하고, `growth_divergence`는 양쪽 전년 기저가 동적 floor 이상·동일 부호일 때만 발화한다.
- `%/pp` 기반 신호의 normalized_strength는 `signal_strength_cap`으로 캡한다. raw 값은 증거로 보존한다.
- 채점 hit 규칙·신호 임계값·상위10 기준은 변경하지 않았다.
- 두 트랙 quota는 자산 대비 규모로 게시 칸을 나누는 보조 잣대이며, legacy top10 결과와 병기한다.

| 회사 | label | window | available | discovered | legacy_strict | track_hit | miss_reason | fired |
|---|---|---|---|---|---|---|---|---:|
| 두산에너빌리티 | positive | [2015, 2016, 2017, 2018, 2019] | [2015, 2016, 2017, 2018, 2019] | True | True | True | None | 124 |
| 아스트 | positive | [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022] | [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022] | True | True | True | None | 296 |
| 디아이동일 | positive | [2015, 2016, 2017, 2018, 2019] | [2015, 2016, 2017, 2018, 2019] | True | True | True | None | 117 |
| 모델솔루션 | positive | [2020, 2021, 2022, 2023] | [2022, 2023] | True | True | True | None | 20 |
| 셀트리온 | positive | [2015, 2016, 2017, 2018, 2019, 2020] | [2015, 2016, 2017, 2018, 2019, 2020] | True | True | True | None | 188 |
| 세토피아 | positive | [2017, 2018, 2019] | [2017, 2018, 2019] | False | False | False | 변동미미 | 48 |
| 삼성전자 | clean | [2022, 2023, 2024, 2025] | [2022, 2023, 2024, 2025] | False | False | False | 해당없음 | 113 |
| 한국항공우주산업(KAI) | negative | [2016, 2017] | [2016, 2017] | False | False | False | 변동미미 | 21 |

## 분식계정별 최고 강도와 순위
| 회사 | 분식계정 | status | 최고강도 | 순위 |
|---|---|---|---:|---:|
| 두산에너빌리티 | 공사매출 | 변동미미 | None | None |
| 두산에너빌리티 | 미청구공사 | 포착 | 5.0 | 1 |
| 두산에너빌리티 | 공사손실충당부채 | 계정부재 | None | None |
| 두산에너빌리티 | 종속기업투자주식 | 변동미미 | None | None |
| 두산에너빌리티 | 손상차손 | 계정부재 | None | None |
| 아스트 | 재고자산 | 포착 | 7.3907 | 6 |
| 아스트 | 매출원가 | 상위10밖 | 3.234 | 13 |
| 아스트 | 자기자본 | 계정부재 | None | None |
| 디아이동일 | 종속기업투자 | 계정부재 | None | None |
| 디아이동일 | 자기자본 | 계정부재 | None | None |
| 디아이동일 | 수익 | 포착 | 1.2314 | 5 |
| 디아이동일 | 이연법인세부채 | 변동미미 | None | None |
| 모델솔루션 | 매출 | 변동미미 | None | None |
| 모델솔루션 | 매출원가 | 규모미달 | None | None |
| 모델솔루션 | 자기자본 | 계정부재 | None | None |
| 모델솔루션 | 당기순이익 | 포착 | 10.0 | 1 |
| 셀트리온 | 개발비(무형자산) | 포착 | 2.55 | 10 |
| 셀트리온 | 무형자산 | 포착 | 2.55 | 10 |
| 셀트리온 | 재고자산 | 포착 | 5.996 | 2 |
| 셀트리온 | 재고자산평가손실 | 포착 | 5.996 | 2 |
| 세토피아 | 금융자산 | 변동미미 | None | None |
| 세토피아 | 금융부채 | 변동미미 | None | None |
| 한국항공우주산업(KAI) | 개발비(무형자산) | 변동미미 | None | None |
| 한국항공우주산업(KAI) | 선급금 | 계정부재 | None | None |
| 한국항공우주산업(KAI) | 공사진행률 | 변동미미 | None | None |
| 한국항공우주산업(KAI) | 매출 | 변동미미 | None | None |

## 두 트랙 분식계정 상태
| 회사 | 분식계정 | track_status | track | track_rank | 최고강도 |
|---|---|---|---|---:|---:|
| 두산에너빌리티 | 공사매출 | 변동미미 | None | None | None |
| 두산에너빌리티 | 미청구공사 | 포착 | A | 1 | 5.0 |
| 두산에너빌리티 | 공사손실충당부채 | 계정부재 | None | None | None |
| 두산에너빌리티 | 종속기업투자주식 | 변동미미 | None | None | None |
| 두산에너빌리티 | 손상차손 | 계정부재 | None | None | None |
| 아스트 | 재고자산 | 포착 | A | 6 | 7.3907 |
| 아스트 | 매출원가 | 상위10밖 | A | 9 | 3.234 |
| 아스트 | 자기자본 | 계정부재 | None | None | None |
| 디아이동일 | 종속기업투자 | 계정부재 | None | None | None |
| 디아이동일 | 자기자본 | 계정부재 | None | None | None |
| 디아이동일 | 수익 | 포착 | A | 1 | 1.22 |
| 디아이동일 | 이연법인세부채 | 변동미미 | None | None | None |
| 모델솔루션 | 매출 | 변동미미 | None | None | None |
| 모델솔루션 | 매출원가 | 규모미달 | None | None | None |
| 모델솔루션 | 자기자본 | 계정부재 | None | None | None |
| 모델솔루션 | 당기순이익 | 포착 | B | 1 | 10.0 |
| 셀트리온 | 개발비(무형자산) | 포착 | A | 5 | 2.55 |
| 셀트리온 | 무형자산 | 포착 | A | 5 | 2.55 |
| 셀트리온 | 재고자산 | 포착 | B | 1 | 5.996 |
| 셀트리온 | 재고자산평가손실 | 포착 | B | 1 | 5.996 |
| 세토피아 | 금융자산 | 변동미미 | None | None | None |
| 세토피아 | 금융부채 | 변동미미 | None | None | None |
| 한국항공우주산업(KAI) | 개발비(무형자산) | 변동미미 | None | None | None |
| 한국항공우주산업(KAI) | 선급금 | 계정부재 | None | None | None |
| 한국항공우주산업(KAI) | 공사진행률 | 변동미미 | None | None | None |
| 한국항공우주산업(KAI) | 매출 | 변동미미 | None | None | None |

## mvp1 가드 확인
- 두산에너빌리티 미청구공사: status 포착, rank 1, strength 5.0
- 아스트 재고자산: status 포착, rank 6, strength 7.3907
- 디아이동일 수익: status 포착, rank 5, strength 1.2314
- 아스트 `cogs-vs-inventory` 관계 신호는 material 기저라 유지되고, 0 근처 기저 폭발성 divergence는 제외된다.

## 삼성전자 거짓양성 상위 10
| 순위 | 계정 | 유형 | 강도 | 값 | 연도 |
|---:|---|---|---:|---:|---:|
| 1 | 당기순이익 | growth_divergence | 10.0 | 275.89 | 2024 |
| 2 | 영업이익 | single_account_yoy | 7.9668 | 398.34 | 2024 |
| 3 | 법인세비용차감전순이익 | single_account_yoy | 4.8198 | 240.99 | 2024 |
| 4 | 단기금융상품 | single_account_yoy | 3.1924 | 159.62 | 2024 |
| 5 | 지배기업귀속순이익 | single_account_yoy | 2.646 | 132.3 | 2024 |
| 6 | 기타비유동자산 | universal_yoy | 2.026 | 101.3 | 2023 |
| 7 | 이연법인세자산 | universal_yoy | 2.0036 | 100.18 | 2023 |
| 8 | 단기차입금 | single_account_yoy | 1.703 | 85.15 | 2024 |
| 9 | 계속영업이익(손실) | universal_yoy | 1.4434 | -72.17 | 2023 |
| 10 | 매출채권 | growth_divergence | 1.128 | -16.92 | 2023 |

## 삼성전자 두 트랙 상위 신호
| 트랙 | 순위 | 계정 | 유형 | 강도 | 값 | 규모비율 |
|---|---:|---|---|---:|---:|---:|
| A | 1 | 당기순이익 | growth_divergence | 10.0 | 275.89 | 6.70% |
| A | 2 | 영업이익 | single_account_yoy | 7.9668 | 398.34 | 6.36% |
| A | 3 | 법인세비용차감전순이익 | single_account_yoy | 4.8198 | 240.99 | 7.29% |
| A | 4 | 단기금융상품 | single_account_yoy | 3.1924 | 159.62 | 11.45% |
| A | 5 | 지배기업귀속순이익 | single_account_yoy | 2.646 | 132.3 | 6.53% |
| A | 6 | 매출원가 | universal_mix_shift | 1.364 | 6.82 | 39.57% |
| B | 1 | 기타비유동자산 | universal_yoy | 2.026 | 101.3 | 3.11% |
| B | 2 | 이연법인세자산 | universal_yoy | 2.0036 | 100.18 | 2.24% |
| B | 3 | 단기차입금 | single_account_yoy | 1.703 | 85.15 | 2.56% |
| B | 4 | 계속영업이익(손실) | universal_yoy | 1.4434 | -72.17 | 3.40% |
| B | 5 | 법인세비용 | single_account_yoy | 1.0274 | 51.37 | 0.98% |

## 정상 회사 채점 신호 상위 5
| 회사 | 채점신호수 | 상위5 | 잔여 아티팩트 후보 |
|---|---:|---|---|
| 삼성전자 | 10 | 당기순이익 / growth_divergence / 10.0<br>영업이익 / single_account_yoy / 7.9668<br>법인세비용차감전순이익 / single_account_yoy / 4.8198<br>단기금융상품 / single_account_yoy / 3.1924<br>지배기업귀속순이익 / single_account_yoy / 2.646 | 없음 |

## 한계
- LLM·외부검색 없이 L0~L2 숫자 신호만 본다.
- 새 임계값을 만들지 않고 기존 red_flags/universal 신호만 채점했다.
- cfs_ofs_gap은 자회사 구조가 있으면 넓게 발생하므로 발굴·strict 판정에서 제외했다.
- 중과실·연결특화·다년분식·단일연도 데이터는 Stage1 숫자 신호만으로 한계가 있다.
