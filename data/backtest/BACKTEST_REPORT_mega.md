# BACKTEST_REPORT — Stage1 결정론 백테스트

- 발굴 recall: 15/16
- 기존 단일 통합 top10 strict hit: 15/16
- 새 두 트랙 quota hit: 14/16
- 채점에서 `cfs_ofs_gap`은 구조적 노이즈로 제외했다. raw fired_signals에는 남긴다.
- mvp1 Tier 1 가드: `single_account_yoy` 채점 신호에서 CF 계정을 제외하고, `growth_divergence`는 양쪽 전년 기저가 동적 floor 이상·동일 부호일 때만 발화한다.
- `%/pp` 기반 신호의 normalized_strength는 `signal_strength_cap`으로 캡한다. raw 값은 증거로 보존한다.
- 채점 hit 규칙·신호 임계값·상위10 기준은 변경하지 않았다.
- 두 트랙 quota는 자산 대비 규모로 게시 칸을 나누는 보조 잣대이며, legacy top10 결과와 병기한다.

| 회사 | label | window | available | discovered | legacy_strict | track_hit | miss_reason | fired |
|---|---|---|---|---|---|---|---|---:|
| 두산에너빌리티 | positive | [2015, 2016, 2017, 2018, 2019] | [2015, 2016, 2017, 2018, 2019] | True | True | True | None | 131 |
| 아스트 | positive | [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022] | [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022] | True | True | True | None | 300 |
| 디아이동일 | positive | [2015, 2016, 2017, 2018, 2019] | [2015, 2016, 2017, 2018, 2019] | True | True | True | None | 118 |
| 모델솔루션 | positive | [2020, 2021, 2022, 2023] | [2022, 2023] | True | True | True | None | 20 |
| 셀트리온 | positive | [2015, 2016, 2017, 2018, 2019, 2020] | [2015, 2016, 2017, 2018, 2019, 2020] | True | True | True | None | 190 |
| 세토피아 | positive | [2017, 2018, 2019] | [2017, 2018, 2019] | False | False | False | 변동미미 | 50 |
| 티피씨메카트로닉스 | positive | [2015, 2016] | [2015, 2016] | True | True | True | None | 37 |
| 유네코 | positive | [2015, 2016, 2017, 2018, 2019] | [2017, 2018, 2019] | True | True | False | None | 94 |
| 본느 | positive | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | True | True | True | None | 133 |
| 이트론 | positive | [2017, 2018, 2019, 2020, 2021, 2022] | [2017, 2018, 2019, 2020, 2021, 2022] | True | True | True | None | 170 |
| 웨이브일렉트로닉스 | positive | [2015, 2016, 2017, 2018, 2019] | [2015, 2016, 2017, 2018, 2019] | True | True | True | None | 191 |
| 웰바이오텍 | positive | [2017, 2018, 2019, 2020, 2021, 2022] | [2017, 2018, 2019, 2020, 2021, 2022] | True | True | True | None | 277 |
| 에스엘 | positive | [2016, 2017, 2018] | [2016, 2017, 2018] | True | True | True | None | 71 |
| 이렘 | positive | [2016, 2017, 2018, 2019, 2020] | [2016, 2017, 2018, 2019, 2020] | True | True | True | None | 135 |
| 더테크놀로지 | positive | [2019, 2020, 2021, 2022] | [2019, 2020, 2021, 2022] | True | True | True | None | 70 |
| 한창 | positive | [2019, 2020, 2021, 2022] | [2019, 2020, 2021, 2022] | True | True | True | None | 216 |
| KB금융 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 12 |
| 신한지주 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 12 |
| 삼성생명 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 11 |
| SK(지주) | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 88 |
| 삼성엔지니어링 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 109 |
| 삼성중공업 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 120 |
| ESR켄달스퀘어리츠 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 69 |
| 코텍 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 78 |
| YW | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 49 |
| KSS해운 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 73 |
| 지나인제약 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 103 |
| 와이랩 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 9 |
| 리튬포어스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 53 |
| 휴비스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 80 |
| 한진 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 94 |
| 동성제약 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 62 |
| JYP Ent. | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 137 |
| 화승코퍼레이션 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 81 |
| 소프트센 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 71 |
| 바이오노트 | clean | [2020, 2021, 2022, 2023] | [2022, 2023] | False | False | False | 해당없음 | 43 |
| 라임 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 12 |
| 알파칩스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 158 |
| 한국테크놀로지 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 155 |
| 한컴라이프케어 | clean | [2020, 2021, 2022, 2023] | [2021, 2022, 2023] | False | False | False | 해당없음 | 57 |
| 아이스크림에듀 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 32 |
| HDC현대EP | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 119 |
| 세운메디칼 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 75 |
| 새론오토모티브 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 83 |
| 문배철강 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 25 |
| 한국종합기술 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 26 |
| HB솔루션 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 102 |
| 한미약품 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 91 |
| 폴라리스우노 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 112 |
| 창해에탄올 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 79 |
| 한국씨티은행 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 0 |
| GS | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 123 |
| 진도 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 40 |
| 아이비케이에스제20호기업인수목적 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 0 |
| 퓨쳐메디신 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 2 |
| 마이크로투나노 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 0 |
| 광무 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 144 |
| 지노믹트리 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 89 |
| SNT모티브 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 38 |
| 케이에이치미래물산 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 135 |
| 이니텍 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 53 |
| LS | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 112 |
| 하이트진로홀딩스 | clean | [2020, 2021, 2022, 2023] | [2020, 2022, 2023] | False | False | False | 해당없음 | 47 |
| 킵스파마 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 110 |
| 유니트론텍 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 120 |
| DL | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 147 |
| 남광토건 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 59 |
| 다산솔루에타 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 151 |
| 액트로 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 109 |
| 코맥스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 81 |
| 앤에스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 119 |
| 미래에셋맵스리츠 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 6 |
| 켐트로스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 33 |
| 코닉오토메이션 | clean | [2020, 2021, 2022, 2023] | [2022, 2023] | False | False | False | 해당없음 | 22 |
| 옵티코어 | clean | [2020, 2021, 2022, 2023] | [2022, 2023] | False | False | False | 해당없음 | 29 |
| 한국정보공학 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 83 |
| 혜인 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 58 |
| 오에스피 | clean | [2020, 2021, 2022, 2023] | [2022, 2023] | False | False | False | 해당없음 | 25 |
| 프리엠스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 34 |
| 퀄리타스반도체 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 0 |
| 예스티 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 138 |
| 환인제약 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 36 |
| 나노신소재 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 112 |
| 티에스넥스젠 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 81 |
| 대원미디어 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 108 |
| 토니모리 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 123 |
| 아바텍 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 26 |
| 삼보산업 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 87 |
| 대한방직 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 43 |
| 한프 | clean | [2020, 2021, 2022, 2023] | [2020, 2021] | False | False | False | 해당없음 | 53 |
| 에스디시스템 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 40 |
| 라파스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 101 |
| 팜젠사이언스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 123 |
| SK리츠 | clean | [2020, 2021, 2022, 2023] | [2021, 2022, 2023] | False | False | False | 해당없음 | 37 |
| 아이앤씨 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 83 |
| 서플러스글로벌 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 115 |
| 영흥 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 95 |
| 화신 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 110 |
| 아미코젠 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 109 |
| 엠에프엠코리아 | clean | [2020, 2021, 2022, 2023] | [2021, 2022, 2023] | False | False | False | 해당없음 | 82 |
| AP시스템 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 84 |
| 마니커에프앤지 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 32 |
| 대동기어 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 33 |
| 졸스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 63 |
| 뷰웍스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 55 |
| 성도이엔지 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 114 |
| 한국경제TV | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 50 |
| 에스엠 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 95 |
| 비트플래닛 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 54 |
| 웰크론 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 95 |
| 보라티알 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 92 |
| 전방 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 64 |
| 우진비앤지 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 113 |
| 에스티큐브 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 106 |
| 대모 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 63 |
| 한일시멘트 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 99 |
| 테라사이언스 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 90 |
| 한국화장품제조 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 38 |
| SK증권 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 9 |
| 이구산업 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 20 |
| 가온그룹 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 95 |
| 하나금융20호기업인수목적 | clean | [2020, 2021, 2022, 2023] | [2021, 2022] | False | False | False | 해당없음 | 4 |
| 온타이드 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 115 |
| 나래나노텍 | clean | [2020, 2021, 2022, 2023] | [2021, 2022, 2023] | False | False | False | 해당없음 | 72 |
| 한국큐빅 | clean | [2020, 2021, 2022, 2023] | [2020, 2021, 2022, 2023] | False | False | False | 해당없음 | 91 |
| KB스타리츠 | clean | [2020, 2021, 2022, 2023] | [2023] | False | False | False | 해당없음 | 12 |

## 분식계정별 최고 강도와 순위
| 회사 | 분식계정 | status | 최고강도 | 순위 |
|---|---|---|---:|---:|
| 두산에너빌리티 | 공사매출 | 변동미미 | None | None |
| 두산에너빌리티 | 미청구공사 | 포착 | 5.0 | 2 |
| 두산에너빌리티 | 공사손실충당부채 | 계정부재 | None | None |
| 두산에너빌리티 | 종속기업투자주식 | 변동미미 | None | None |
| 두산에너빌리티 | 손상차손 | 계정부재 | None | None |
| 아스트 | 재고자산 | 포착 | 7.3907 | 6 |
| 아스트 | 매출원가 | 상위10밖 | 3.234 | 14 |
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
| 티피씨메카트로닉스 | 재고자산 | 포착 | 3.7033 | 3 |
| 티피씨메카트로닉스 | 매출원가 | 변동미미 | None | None |
| 유네코 | 매출채권 | 상위10밖 | 3.3093 | 11 |
| 유네코 | 대손충당금 | 계정부재 | None | None |
| 유네코 | 차입금 | 포착 | 6.5627 | 9 |
| 본느 | 재고자산 | 포착 | 5.2987 | 2 |
| 본느 | 충당부채 | 규모미달 | None | None |
| 이트론 | 무형자산 | 변동미미 | None | None |
| 이트론 | 관계기업투자 | 상위10밖 | 1.0554 | 24 |
| 이트론 | 당기순이익 | 포착 | 10.0 | 3 |
| 이트론 | 자기자본 | 계정부재 | None | None |
| 웨이브일렉트로닉스 | 무형자산 | 상위10밖 | 1.2536 | 22 |
| 웨이브일렉트로닉스 | 관계기업투자 | 변동미미 | None | None |
| 웨이브일렉트로닉스 | 당기순이익 | 포착 | 6.5027 | 2 |
| 웨이브일렉트로닉스 | 자기자본 | 계정부재 | None | None |
| 웰바이오텍 | 매출 | 상위10밖 | 3.3666 | 12 |
| 웰바이오텍 | 매출원가 | 상위10밖 | 1.6684 | 26 |
| 웰바이오텍 | 매출채권 | 변동미미 | None | None |
| 웰바이오텍 | 재고자산 | 포착 | 10.0 | 2 |
| 에스엘 | 영업이익 | 포착 | 1.8556 | 2 |
| 에스엘 | 매출원가 | 변동미미 | None | None |
| 에스엘 | 재고자산 | 변동미미 | None | None |
| 이렘 | 관계기업투자 | 상위10밖 | 1.6756 | 16 |
| 이렘 | 당기순이익 | 포착 | 10.0 | 3 |
| 이렘 | 대손충당금 | 변동미미 | None | None |
| 더테크놀로지 | 매출 | 포착 | 5.1902 | 2 |
| 더테크놀로지 | 매출원가 | 규모미달 | None | None |
| 더테크놀로지 | 매출채권 | 포착 | 5.1902 | 2 |
| 한창 | 매출 | 포착 | 10.0 | 1 |
| 한창 | 매출원가 | 상위10밖 | 2.0902 | 29 |

## 두 트랙 분식계정 상태
| 회사 | 분식계정 | track_status | track | track_rank | 최고강도 |
|---|---|---|---|---:|---:|
| 두산에너빌리티 | 공사매출 | 변동미미 | None | None | None |
| 두산에너빌리티 | 미청구공사 | 포착 | A | 1 | 5.0 |
| 두산에너빌리티 | 공사손실충당부채 | 계정부재 | None | None | None |
| 두산에너빌리티 | 종속기업투자주식 | 변동미미 | None | None | None |
| 두산에너빌리티 | 손상차손 | 계정부재 | None | None | None |
| 아스트 | 재고자산 | 포착 | A | 6 | 7.3907 |
| 아스트 | 매출원가 | 상위10밖 | A | 10 | 3.234 |
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
| 티피씨메카트로닉스 | 재고자산 | 포착 | A | 3 | 3.7033 |
| 티피씨메카트로닉스 | 매출원가 | 변동미미 | None | None | None |
| 유네코 | 매출채권 | 상위10밖 | A | 10 | 3.3093 |
| 유네코 | 대손충당금 | 계정부재 | None | None | None |
| 유네코 | 차입금 | 상위10밖 | A | 8 | 6.5627 |
| 본느 | 재고자산 | 포착 | A | 2 | 5.2987 |
| 본느 | 충당부채 | 규모미달 | None | None | None |
| 이트론 | 무형자산 | 변동미미 | None | None | None |
| 이트론 | 관계기업투자 | 상위10밖 | A | 20 | 1.388 |
| 이트론 | 당기순이익 | 포착 | A | 2 | 10.0 |
| 이트론 | 자기자본 | 계정부재 | None | None | None |
| 웨이브일렉트로닉스 | 무형자산 | 상위10밖 | A | 20 | 1.2536 |
| 웨이브일렉트로닉스 | 관계기업투자 | 변동미미 | None | None | None |
| 웨이브일렉트로닉스 | 당기순이익 | 포착 | A | 2 | 6.5027 |
| 웨이브일렉트로닉스 | 자기자본 | 계정부재 | None | None | None |
| 웰바이오텍 | 매출 | 상위10밖 | A | 8 | 3.3666 |
| 웰바이오텍 | 매출원가 | 상위10밖 | A | 18 | 1.6684 |
| 웰바이오텍 | 매출채권 | 상위10밖 | A | 16 | 1.8308 |
| 웰바이오텍 | 재고자산 | 포착 | B | 1 | 10.0 |
| 에스엘 | 영업이익 | 포착 | B | 1 | 1.8556 |
| 에스엘 | 매출원가 | 변동미미 | None | None | None |
| 에스엘 | 재고자산 | 변동미미 | None | None | None |
| 이렘 | 관계기업투자 | 상위10밖 | A | 15 | 1.6756 |
| 이렘 | 당기순이익 | 포착 | A | 3 | 10.0 |
| 이렘 | 대손충당금 | 변동미미 | None | None | None |
| 더테크놀로지 | 매출 | 포착 | A | 1 | 5.1902 |
| 더테크놀로지 | 매출원가 | 규모미달 | None | None | None |
| 더테크놀로지 | 매출채권 | 포착 | A | 1 | 5.1902 |
| 한창 | 매출 | 포착 | A | 1 | 10.0 |
| 한창 | 매출원가 | 상위10밖 | A | 29 | 2.0902 |

## mvp1 가드 확인
- 두산에너빌리티 미청구공사: status 포착, rank 2, strength 5.0
- 아스트 재고자산: status 포착, rank 6, strength 7.3907
- 디아이동일 수익: status 포착, rank 5, strength 1.2314

## 정상 회사 채점 신호 상위 5
| 회사 | 채점신호수 | 상위5 | 잔여 아티팩트 후보 |
|---|---:|---|---|
| KB금융 | 0 |  | 없음 |
| 신한지주 | 0 |  | 없음 |
| 삼성생명 | 0 |  | 없음 |
| SK(지주) | 10 | 장기차입금 / growth_divergence / 10.0<br>당기순이익 / growth_divergence / 6.1887<br>재고자산 / growth_divergence / 3.916<br>금융수익 / single_account_yoy / 3.119<br>이자비용 / single_account_yoy / 2.8 | 없음 |
| 삼성엔지니어링 | 10 | 당기순이익 / growth_divergence / 6.108<br>단기금융상품 / universal_yoy / 5.4914<br>계약자산 / growth_divergence / 4.146<br>매출채권 / growth_divergence / 3.254<br>이자비용 / single_account_yoy / 2.5738 | 없음 |
| 삼성중공업 | 10 | 유동파생금융자산 / universal_yoy / 8.837<br>장기차입금 / single_account_yoy / 7.0936<br>매출채권 / growth_divergence / 5.2887<br>계약자산 / growth_divergence / 4.1033<br>유동파생금융부채 / universal_yoy / 3.535 | 없음 |
| ESR켄달스퀘어리츠 | 8 | 현금및현금성자산 / universal_mix_shift / 6.084<br>자본금 / single_account_yoy / 3.9444<br>지배기업소유주지분 / single_account_yoy / 3.8588<br>장기차입금 / growth_divergence / 1.3993<br>기타불입자본 / universal_yoy / 1.3272 | 없음 |
| 코텍 | 10 | 현금및현금성자산 / single_account_yoy / 10.0<br>재고자산 / growth_divergence / 6.5993<br>매출총이익 / single_account_yoy / 4.3516<br>단기차입금 / single_account_yoy / 2.5<br>매입채무및기타유동채무 / universal_yoy / 2.313 | 없음 |
| YW | 10 | 현금및현금성자산 / single_account_yoy / 10.0<br>당기순이익 / growth_divergence / 2.3693<br>영업이익 / single_account_yoy / 2.237<br>매출채권 / growth_divergence / 2.1833<br>단기금융상품 / single_account_yoy / 1.8834 | 없음 |
| KSS해운 | 10 | 당기순이익 / growth_divergence / 10.0<br>장기차입금 / growth_divergence / 6.5047<br>미처분이익잉여금(미처리결손금) / universal_yoy / 3.1076<br>재고자산 / growth_divergence / 2.5347<br>이자비용 / single_account_yoy / 2.3154 | 당기순이익 divergence -312.58pp |
| 지나인제약 | 10 | 당기순이익 / growth_divergence / 10.0<br>현금및현금성자산 / single_account_yoy / 10.0<br>금융수익 / single_account_yoy / 10.0<br>지배기업소유주지분 / single_account_yoy / 8.362<br>기타비용 / single_account_yoy / 4.5488 | 당기순이익 divergence -1804.84pp<br>현금및현금성자산 YoY 1550.5 |
| 와이랩 | 0 |  | 없음 |
| 리튬포어스 | 8 | 기타유동금융부채 / universal_yoy / 10.0<br>이익잉여금 / universal_yoy / 10.0<br>FVPL금융자산 / universal_yoy / 10.0<br>전환사채 / universal_yoy / 7.9446<br>Ⅱ. 자본잉여금 / universal_mix_shift / 5.124 | 없음 |
| 휴비스 | 10 | 당기순이익 / growth_divergence / 6.598<br>무형자산 / single_account_yoy / 2.8162<br>법인세비용차감전순이익 / single_account_yoy / 1.956<br>매출총이익 / single_account_yoy / 1.9532<br>지배기업귀속순이익 / single_account_yoy / 1.911 | 없음 |
| 한진 | 9 | 당기순이익 / growth_divergence / 6.6413<br>장기차입금 / growth_divergence / 3.9713<br>단기차입금 / single_account_yoy / 3.2846<br>사채 / single_account_yoy / 1.776<br>법인세비용차감전순이익 / single_account_yoy / 1.6454 | 없음 |
| 동성제약 | 8 | 장기차입금 / universal_yoy / 3.8982<br>단기차입금 / universal_yoy / 1.8816<br>파생상품부채 / universal_yoy / 1.6828<br>미처분이익잉여금 / universal_yoy / 1.679<br>현금및현금성자산 / universal_yoy / 1.5624 | 없음 |
| JYP Ent. | 10 | 당기순이익 / growth_divergence / 6.438<br>당기손익-공정가치측정금융자산(비유동) / universal_yoy / 3.9304<br>현금및현금성자산 / single_account_yoy / 3.6838<br>이자비용 / single_account_yoy / 2.8466<br>매출채권및기타유동채권 / universal_yoy / 2.8256 | 없음 |
| 화승코퍼레이션 | 10 | 당기순이익 / growth_divergence / 4.9467<br>기타수익 / single_account_yoy / 4.2426<br>투자부동산 / universal_yoy / 3.5588<br>비지배지분순이익 / single_account_yoy / 2.6234<br>영업이익 / single_account_yoy / 1.6234 | 없음 |
| 소프트센 | 10 | 당기순이익 / growth_divergence / 10.0<br>법인세비용차감전순이익 / single_account_yoy / 10.0<br>유형자산 / single_account_yoy / 8.265<br>영업이익 / single_account_yoy / 8.1714<br>장기차입금 / growth_divergence / 7.4213 | 당기순이익 divergence -1240.67pp |
| 바이오노트 | 7 | 재고자산 / growth_divergence / 2.29<br>현금및현금성자산 / universal_mix_shift / 2.046<br>기타비용 / single_account_yoy / 1.8716<br>매출 / single_account_yoy / 1.6244<br>이연법인세부채 / universal_yoy / 1.5926 | 없음 |
| 라임 | 0 |  | 없음 |
| 알파칩스 | 10 | 당기순이익 / growth_divergence / 10.0<br>법인세비용차감전순이익 / single_account_yoy / 10.0<br>매각예정자산 / universal_yoy / 10.0<br>이익잉여금 / universal_yoy / 5.97<br>지배기업귀속순이익 / single_account_yoy / 5.5808 | 없음 |
| 한국테크놀로지 | 10 | 당기순이익 / growth_divergence / 10.0<br>재고자산 / growth_divergence / 7.2773<br>기타유동자산 / single_account_yoy / 5.8884<br>이익잉여금 / universal_mix_shift / 5.874<br>법인세비용차감전순이익 / single_account_yoy / 4.3432 | 없음 |
| 한컴라이프케어 | 10 | 당기순이익 / growth_divergence / 10.0<br>기타유동자산 / single_account_yoy / 4.3466<br>법인세비용차감전순이익 / single_account_yoy / 2.732<br>재고자산 / growth_divergence / 2.0007<br>금융수익 / single_account_yoy / 1.9028 | 없음 |
| 아이스크림에듀 | 7 | 이익잉여금 / universal_mix_shift / 2.52<br>유형자산 / universal_yoy / 2.1478<br>매출채권및기타유동채권 / universal_yoy / 2.039<br>재고자산 / universal_yoy / 1.7824<br>계약자산 / universal_yoy / 1.644 | 없음 |
| HDC현대EP | 10 | 당기순이익 / growth_divergence / 10.0<br>재고자산 / growth_divergence / 3.4347<br>기타비용 / single_account_yoy / 1.7398<br>지배기업귀속순이익 / single_account_yoy / 1.7046<br>단기차입금 / single_account_yoy / 1.6592 | 당기순이익 divergence 399.63pp |
| 세운메디칼 | 7 | 당기순이익 / growth_divergence / 6.8847<br>단기금융상품 / single_account_yoy / 5.1428<br>현금및현금성자산 / single_account_yoy / 2.7314<br>기타비용 / single_account_yoy / 1.6078<br>기타수익 / single_account_yoy / 1.1708 | 없음 |
| 새론오토모티브 | 8 | 당기순이익 / growth_divergence / 6.2307<br>지배기업귀속순이익 / single_account_yoy / 4.126<br>영업이익 / single_account_yoy / 2.9222<br>금융수익 / single_account_yoy / 2.7574<br>이자비용 / single_account_yoy / 1.9484 | 없음 |
| 문배철강 | 5 | 재고자산 / universal_yoy / 3.0722<br>이익잉여금 / universal_mix_shift / 1.326<br>유동성장기차입금 / universal_yoy / 1.147<br>이연법인세부채 / universal_yoy / 1.0968<br>FVPL금융자산 / universal_yoy / 1.0816 | 없음 |
| 한국종합기술 | 5 | 당기순이익 / universal_yoy / 5.0234<br>순확정급여부채 / universal_yoy / 3.4598<br>법인세비용차감전순이익 / universal_yoy / 1.8464<br>기타유동자산 / universal_yoy / 1.3218<br>영업이익 / universal_yoy / 1.1182 | 없음 |
| HB솔루션 | 10 | 재고자산 / growth_divergence / 10.0<br>계약자산 / growth_divergence / 10.0<br>매출채권 / growth_divergence / 10.0<br>매출총이익 / single_account_yoy / 10.0<br>기타수익 / single_account_yoy / 10.0 | 재고자산 divergence -493.47pp<br>계약자산 divergence -436.35pp<br>기타수익 YoY 1449.46 |
| 한미약품 | 10 | 장기차입금 / growth_divergence / 10.0<br>법인세비용차감전순이익 / single_account_yoy / 7.3714<br>영업이익 / single_account_yoy / 3.1214<br>당기순이익 / growth_divergence / 2.952<br>유동성사채 / universal_yoy / 2.2854 | 없음 |
| 폴라리스우노 | 10 | 당기순이익 / growth_divergence / 10.0<br>비유동FVOCI금융자산 / universal_yoy / 8.0656<br>자본금 / single_account_yoy / 6.8538<br>단기금융상품 / single_account_yoy / 5.5546<br>기타비용 / single_account_yoy / 4.137 | 없음 |
| 창해에탄올 | 8 | 장기차입금 / growth_divergence / 7.3693<br>당기순이익 / growth_divergence / 4.4207<br>재고자산 / growth_divergence / 3.3007<br>기타유동자산 / single_account_yoy / 3.1662<br>매입채무 / single_account_yoy / 2.8778 | 없음 |
| 한국씨티은행 | 0 |  | 없음 |
| GS | 10 | 법인세비용차감전순이익 / single_account_yoy / 10.0<br>당기순이익 / growth_divergence / 7.734<br>기타비유동금융자산 / universal_yoy / 6.0542<br>영업이익 / single_account_yoy / 3.7362<br>재고자산 / growth_divergence / 3.0927 | 없음 |
| 진도 | 9 | 현금및현금성자산 / single_account_yoy / 7.7934<br>투자부동산 / universal_yoy / 3.8372<br>당기순이익 / growth_divergence / 3.1893<br>기타수익 / single_account_yoy / 1.6022<br>재고자산 / growth_divergence / 1.4647 | 없음 |
| 아이비케이에스제20호기업인수목적 | 0 |  | 없음 |
| 퓨쳐메디신 | 0 |  | 없음 |
| 마이크로투나노 | 0 |  | 없음 |
| 광무 | 10 | 현금및현금성자산 / single_account_yoy / 10.0<br>단기차입금 / single_account_yoy / 10.0<br>매출채권 / growth_divergence / 10.0<br>금융수익 / single_account_yoy / 10.0<br>기타금융자산 / universal_yoy / 10.0 | 매출채권 divergence -429.09pp |
| 지노믹트리 | 10 | 재고자산 / growth_divergence / 10.0<br>기타자본항목 / universal_yoy / 10.0<br>매출채권 / growth_divergence / 10.0<br>매출총이익 / single_account_yoy / 10.0<br>매출 / single_account_yoy / 9.6218 | 재고자산 divergence 391.73pp<br>매출채권 divergence 535.6pp |
| SNT모티브 | 8 | 당기순이익 / growth_divergence / 6.9573<br>기타비용 / single_account_yoy / 1.9556<br>비유동금융자산 / universal_yoy / 1.8938<br>이자비용 / single_account_yoy / 1.6856<br>당기법인세부채 / universal_yoy / 1.6854 | 없음 |
| 케이에이치미래물산 | 10 | 당기순이익 / growth_divergence / 10.0<br>기타자본항목 / universal_yoy / 10.0<br>법인세비용차감전순이익 / single_account_yoy / 9.32<br>이익잉여금 / universal_yoy / 9.095<br>매출채권 / growth_divergence / 7.572 | 당기순이익 divergence 461.65pp |
| 이니텍 | 5 | 단기금융상품 / universal_yoy / 10.0<br>현금및현금성자산 / universal_yoy / 9.5306<br>매출채권 / universal_yoy / 2.8188<br>기타유동금융부채 / universal_yoy / 1.7036<br>자본조정 / universal_yoy / 1.4128 | 없음 |
| LS | 10 | 장기차입금 / growth_divergence / 10.0<br>재고자산 / growth_divergence / 5.0707<br>매출채권 / growth_divergence / 2.7907<br>당기순이익 / growth_divergence / 2.7727<br>단기차입금 / single_account_yoy / 2.6812 | 없음 |
| 하이트진로홀딩스 | 5 | 당기순이익 / growth_divergence / 2.8507<br>재고자산 / growth_divergence / 1.3873<br>비지배지분순이익 / single_account_yoy / 1.169<br>순확정급여부채 / universal_yoy / 1.1118<br>법인세비용차감전순이익 / single_account_yoy / 1.0158 | 없음 |
| 킵스파마 | 10 | 당기순이익 / growth_divergence / 10.0<br>법인세비용차감전순이익 / single_account_yoy / 10.0<br>지배기업귀속순이익 / single_account_yoy / 10.0<br>매출채권 / growth_divergence / 10.0<br>재고자산 / growth_divergence / 10.0 | 없음 |
| 유니트론텍 | 10 | 당기순이익 / growth_divergence / 4.6747<br>법인세비용차감전순이익 / single_account_yoy / 4.5572<br>영업이익 / single_account_yoy / 4.1338<br>사채 / single_account_yoy / 3.2386<br>현금및현금성자산 / single_account_yoy / 3.1528 | 없음 |
| DL | 10 | 재고자산 / growth_divergence / 9.02<br>당기순이익 / growth_divergence / 8.9893<br>판매비와관리비 / single_account_yoy / 4.322<br>단기차입금 / single_account_yoy / 4.2626<br>매입채무및기타유동채무 / universal_yoy / 3.2822 | 없음 |
| 남광토건 | 10 | 매출채권 / growth_divergence / 10.0<br>단기차입금 / single_account_yoy / 5.4084<br>계약자산 / growth_divergence / 4.4693<br>장기차입금 / single_account_yoy / 3.698<br>기타유동자산 / single_account_yoy / 2.6888 | 매출채권 divergence -1127.24pp |
| 다산솔루에타 | 10 | 장기차입금 / growth_divergence / 10.0<br>장기투자자산 / universal_yoy / 10.0<br>당기순이익 / growth_divergence / 10.0<br>지배기업귀속순이익 / single_account_yoy / 10.0<br>법인세비용차감전순이익 / single_account_yoy / 9.7178 | 장기차입금 divergence 633.18pp<br>장기투자자산 YoY 1225.56 |
| 액트로 | 10 | 당기순이익 / growth_divergence / 10.0<br>매출총이익 / single_account_yoy / 10.0<br>현금및현금성자산 / single_account_yoy / 9.453<br>재고자산 / growth_divergence / 4.81<br>영업이익 / single_account_yoy / 3.3508 | 당기순이익 divergence 764.07pp |
| 코맥스 | 10 | 기타수취채권 / universal_yoy / 10.0<br>유형자산 / single_account_yoy / 10.0<br>당기순이익 / growth_divergence / 9.03<br>기타유동부채 / universal_yoy / 4.298<br>기타비유동금융자산 / universal_yoy / 3.9652 | 유형자산 YoY 1180.44 |
| 앤에스 | 10 | 장기차입금 / growth_divergence / 10.0<br>영업이익 / single_account_yoy / 7.876<br>매출총이익 / single_account_yoy / 7.2952<br>재고자산 / growth_divergence / 3.2627<br>당기순이익 / growth_divergence / 3.0953 | 없음 |
| 미래에셋맵스리츠 | 0 |  | 없음 |
| 켐트로스 | 6 | 단기금융상품 / universal_yoy / 8.7264<br>유동성장기차입금 / universal_yoy / 2.0812<br>유형자산 / universal_mix_shift / 1.58<br>재고자산 / universal_yoy / 1.5534<br>장기차입금 / universal_yoy / 1.2966 | 없음 |
| 코닉오토메이션 | 7 | 비유동FVOCI금융자산 / universal_yoy / 10.0<br>재고자산 / universal_yoy / 9.5188<br>기타부채 / universal_yoy / 4.7334<br>기타지급채무 / universal_yoy / 3.5046<br>기타수취채권 / universal_yoy / 3.0552 | 없음 |
| 옵티코어 | 10 | 당기순이익 / growth_divergence / 7.3007<br>재고자산 / growth_divergence / 3.1373<br>유동성장기차입금 / universal_yoy / 3.0936<br>현금및현금성자산 / single_account_yoy / 2.5658<br>이자비용 / single_account_yoy / 1.9048 | 없음 |
| 한국정보공학 | 8 | 재고자산 / growth_divergence / 6.424<br>당기순이익 / growth_divergence / 4.9<br>단기금융상품 / single_account_yoy / 2.6338<br>기타비용 / single_account_yoy / 1.973<br>매출총이익 / single_account_yoy / 1.939 | 없음 |
| 혜인 | 10 | 장기차입금 / growth_divergence / 10.0<br>단기선급금 / universal_yoy / 4.0588<br>충당부채 / universal_yoy / 3.3108<br>선수금 / universal_yoy / 2.5628<br>장기매입채무 및 기타비유동채무 / universal_yoy / 1.8746 | 없음 |
| 오에스피 | 3 | 매출채권 / universal_yoy / 2.2414<br>비유동FVOCI금융자산 / universal_yoy / 1.6674<br>현금및현금성자산 / universal_mix_shift / 1.27 | 없음 |
| 프리엠스 | 8 | 비유동FVOCI금융자산 / universal_yoy / 6.0602<br>기타자본잉여금 / universal_yoy / 2.6432<br>현금및현금성자산 / single_account_yoy / 1.9232<br>당기순이익 / growth_divergence / 1.876<br>기타유동금융자산 / universal_mix_shift / 1.492 | 없음 |
| 퀄리타스반도체 | 0 |  | 없음 |
| 예스티 | 10 | 이자비용 / single_account_yoy / 10.0<br>당기순이익 / growth_divergence / 10.0<br>지배기업귀속순이익 / single_account_yoy / 10.0<br>매출채권 / growth_divergence / 9.1567<br>현금및현금성자산 / single_account_yoy / 6.5112 | 당기순이익 divergence -317.6pp |
| 환인제약 | 6 | 유형자산 / single_account_yoy / 2.8622<br>당기순이익 / growth_divergence / 2.7993<br>재고자산 / growth_divergence / 2.004<br>단기금융상품 / single_account_yoy / 1.8456<br>FVPL금융자산 / universal_yoy / 1.5862 | 없음 |
| 나노신소재 | 10 | 당기순이익 / growth_divergence / 10.0<br>장기매입채무 및 기타비유동채무 / universal_yoy / 10.0<br>장기차입금 / growth_divergence / 8.8327<br>지배기업귀속순이익 / single_account_yoy / 7.008<br>영업이익 / single_account_yoy / 5.8174 | 당기순이익 divergence -329.14pp<br>장기매입채무 및 기타비유동채무 YoY 5084.1 |
| 티에스넥스젠 | 10 | 기타자본 / universal_yoy / 9.8024<br>장기차입금 / growth_divergence / 9.5907<br>매출채권 / growth_divergence / 6.9387<br>당기순이익 / growth_divergence / 6.598<br>재고자산 / growth_divergence / 5.6127 | 없음 |
| 대원미디어 | 10 | 당기순이익 / growth_divergence / 7.9027<br>재고자산 / growth_divergence / 3.1013<br>유동FVOCI금융자산 / universal_yoy / 3.07<br>기타비유동자산 / universal_yoy / 2.8916<br>장기금융상품 / universal_yoy / 2.645 | 없음 |
| 토니모리 | 10 | 기타비용 / single_account_yoy / 5.5376<br>무형자산 / single_account_yoy / 2.2992<br>장기차입금 / single_account_yoy / 2.113<br>당기순이익 / growth_divergence / 1.9793<br>지배기업귀속순이익 / single_account_yoy / 1.9764 | 없음 |
| 아바텍 | 4 | 현금및현금성자산 / universal_yoy / 4.9906<br>매출채권및기타유동채권 / universal_yoy / 2.1412<br>재고자산 / universal_yoy / 1.3554<br>기타포괄손익누계액 / universal_yoy / 1.2238 | 없음 |
| 삼보산업 | 10 | 장기차입금 / growth_divergence / 10.0<br>기타포괄손익누계액 / universal_yoy / 2.608<br>재고자산 / growth_divergence / 2.2847<br>지배기업귀속순이익 / single_account_yoy / 1.868<br>금융수익 / single_account_yoy / 1.8152 | 없음 |
| 대한방직 | 10 | 당기순이익 / growth_divergence / 10.0<br>기타수익 / single_account_yoy / 2.6412<br>기타비용 / single_account_yoy / 1.7882<br>단기금융상품 / single_account_yoy / 1.733<br>기타 유동부채 / universal_yoy / 1.215 | 없음 |
| 한프 | 10 | 기타유동금융자산 / universal_yoy / 10.0<br>단기대여금 / universal_yoy / 5.8522<br>감자차익 / universal_yoy / 5.6946<br>지배기업소유주지분 / single_account_yoy / 5.1514<br>재고자산 / growth_divergence / 4.0933 | 기타유동금융자산 YoY 9080.28 |
| 에스디시스템 | 4 | 계약부채 / universal_yoy / 10.0<br>매출채권및기타유동채권 / universal_yoy / 3.6934<br>매입채무및기타유동채무 / universal_yoy / 1.1208<br>현금및현금성자산 / universal_yoy / 1.0118 | 없음 |
| 라파스 | 10 | 이자비용 / single_account_yoy / 10.0<br>장기차입금 / growth_divergence / 6.3787<br>무형자산 / universal_yoy / 6.3326<br>영업이익 / single_account_yoy / 4.3974<br>당기순이익 / growth_divergence / 3.83 | 없음 |
| 팜젠사이언스 | 10 | 당기순이익 / growth_divergence / 7.598<br>법인세비용차감전순이익 / single_account_yoy / 5.4848<br>이연법인세부채 / universal_yoy / 5.2558<br>지배기업귀속순이익 / single_account_yoy / 5.0408<br>이익잉여금 / universal_yoy / 3.2234 | 없음 |
| SK리츠 | 4 | 현금및현금성자산 / universal_yoy / 2.4836<br>장기임대보증금 / universal_yoy / 2.078<br>투자부동산 / universal_yoy / 1.2678<br>장기차입금 / universal_mix_shift / 1.192 | 없음 |
| 아이앤씨 | 10 | 현금및현금성자산 / single_account_yoy / 10.0<br>재고자산 / growth_divergence / 7.856<br>당기순이익 / growth_divergence / 3.5987<br>매출채권및기타유동채권 / universal_yoy / 2.3644<br>매입채무및기타유동채무 / universal_yoy / 2.1324 | 없음 |
| 서플러스글로벌 | 10 | 기타유동부채 / universal_yoy / 10.0<br>유동성장기차입금 / universal_yoy / 8.2948<br>기타유동자산 / single_account_yoy / 6.6108<br>매출채권 / growth_divergence / 5.246<br>공정가치측정금융자산 / universal_yoy / 3.5056 | 없음 |
| 영흥 | 10 | 장기차입금 / growth_divergence / 9.1707<br>무형자산 / single_account_yoy / 5.525<br>유동성전환사채 / universal_yoy / 3.9436<br>매입채무 / single_account_yoy / 3.1016<br>매출채권 / single_account_yoy / 2.1098 | 없음 |
| 화신 | 10 | 당기순이익 / growth_divergence / 5.4527<br>영업이익 / single_account_yoy / 5.2328<br>지배기업귀속순이익 / single_account_yoy / 4.0874<br>기타비유동자산 / universal_yoy / 4.075<br>법인세비용차감전순이익 / single_account_yoy / 4.0328 | 없음 |
| 아미코젠 | 10 | 장기차입금 / growth_divergence / 10.0<br>관계기업투자 / universal_yoy / 10.0<br>당기순이익 / growth_divergence / 5.092<br>이자비용 / single_account_yoy / 4.292<br>자본금 / single_account_yoy / 3.5386 | 장기차입금 divergence 2778.19pp<br>관계기업투자 YoY 3126.77 |
| 엠에프엠코리아 | 10 | 사용권자산 / universal_yoy / 10.0<br>매출총이익 / single_account_yoy / 9.7284<br>이익잉여금 / universal_yoy / 3.2256<br>유동성파생상품부채 / universal_yoy / 2.9954<br>장기차입금 / growth_divergence / 2.7267 | 없음 |
| AP시스템 | 10 | 당기순이익 / growth_divergence / 8.6447<br>재고자산 / growth_divergence / 8.4053<br>계약자산 / growth_divergence / 2.872<br>현금및현금성자산 / single_account_yoy / 2.6466<br>지배기업귀속순이익 / single_account_yoy / 2.5822 | 없음 |
| 마니커에프앤지 | 6 | 단기차입금 / universal_yoy / 3.19<br>자본잉여금 / universal_yoy / 2.3576<br>단기금융상품 / universal_yoy / 2.3508<br>현금및현금성자산 / universal_yoy / 1.3798<br>재고자산 / universal_yoy / 1.362 | 없음 |
| 대동기어 | 4 | 장기차입금 / universal_yoy / 1.7182<br>단기차입금 / universal_yoy / 1.5586<br>기타자본구성요소 / universal_yoy / 1.0682<br>매출채권및기타유동채권 / universal_yoy / 1.0574 | 없음 |
| 졸스 | 10 | 금융수익 / single_account_yoy / 10.0<br>기타유동부채 / universal_yoy / 9.7974<br>이자비용 / single_account_yoy / 9.683<br>현금및현금성자산 / single_account_yoy / 7.576<br>기타비유동자산 / universal_yoy / 7.566 | 금융수익 YoY 3756.43 |
| 뷰웍스 | 10 | 당기순이익 / growth_divergence / 7.4153<br>이자비용 / single_account_yoy / 5.8004<br>매입채무 / single_account_yoy / 3.515<br>단기차입금 / single_account_yoy / 3.2608<br>당기법인세부채 / universal_yoy / 2.614 | 없음 |
| 성도이엔지 | 10 | 재고자산 / growth_divergence / 6.906<br>매출채권 / growth_divergence / 5.8727<br>기타유동금융자산 / universal_yoy / 5.0446<br>단기차입금 / single_account_yoy / 4.677<br>당기순이익 / growth_divergence / 4.3287 | 없음 |
| 한국경제TV | 10 | 현금및현금성자산 / single_account_yoy / 5.2388<br>당기순이익 / growth_divergence / 3.6753<br>매입채무및기타유동채무 / universal_yoy / 1.8946<br>유형자산 / single_account_yoy / 1.7308<br>비유동FVOCI금융자산 / universal_yoy / 1.5968 | 없음 |
| 에스엠 | 10 | 사용권자산 / universal_yoy / 9.5166<br>당기순이익 / growth_divergence / 4.8813<br>매출채권 / growth_divergence / 3.3107<br>관계기업투자 / single_account_yoy / 2.9568<br>이익잉여금 / universal_yoy / 2.9462 | 없음 |
| 비트플래닛 | 10 | 유형자산 / universal_yoy / 9.7698<br>비유동 당기손익-공정가치 의무 측정 금융자산 / universal_yoy / 9.0666<br>장기매출채권 및 기타비유동채권 / universal_yoy / 5.877<br>무형자산 / universal_yoy / 4.2598<br>기타유동부채 / universal_yoy / 2.6936 | 없음 |
| 웰크론 | 10 | 이자비용 / single_account_yoy / 3.6352<br>금융수익 / single_account_yoy / 3.453<br>재고자산 / growth_divergence / 3.4473<br>기타유동부채 / universal_yoy / 2.547<br>이익잉여금 / universal_yoy / 2.4982 | 없음 |
| 보라티알 | 10 | 당기순이익 / growth_divergence / 10.0<br>당기법인세부채 / universal_yoy / 8.0918<br>지배기업귀속순이익 / single_account_yoy / 6.231<br>법인세비용차감전순이익 / single_account_yoy / 5.8318<br>단기금융상품 / single_account_yoy / 5.1262 | 없음 |
| 전방 | 10 | 당기순이익 / growth_divergence / 10.0<br>기타수익 / single_account_yoy / 10.0<br>기타비용 / single_account_yoy / 10.0<br>법인세비용차감전순이익 / single_account_yoy / 10.0<br>이익잉여금 / universal_yoy / 10.0 | 기타수익 YoY 3386.71<br>기타비용 YoY 1414.69<br>법인세비용차감전순이익 YoY 3121.63<br>이익잉여금 YoY 2148.91 |
| 우진비앤지 | 10 | 당기순이익 / growth_divergence / 5.4507<br>이자비용 / single_account_yoy / 4.0646<br>매입채무 / single_account_yoy / 4.0364<br>기타수익 / single_account_yoy / 3.2218<br>장기차입금 / growth_divergence / 3.1573 | 없음 |
| 에스티큐브 | 10 | 단기금융상품 / single_account_yoy / 10.0<br>대여금및수취채권 / universal_yoy / 10.0<br>지배기업소유주지분 / single_account_yoy / 4.3374<br>기타유동자산 / single_account_yoy / 3.0038<br>매입채무및기타유동채무 / universal_yoy / 2.9826 | 없음 |
| 대모 | 10 | 장기차입금 / growth_divergence / 6.028<br>유동성장기차입금 / universal_yoy / 2.5206<br>기타수익 / single_account_yoy / 1.966<br>단기차입금 / single_account_yoy / 1.5576<br>당기순이익 / single_account_yoy / 1.4404 | 없음 |
| 한일시멘트 | 10 | 현금및현금성자산 / single_account_yoy / 4.8828<br>재고자산 / growth_divergence / 2.444<br>영업이익 / single_account_yoy / 2.1788<br>당기순이익 / single_account_yoy / 2.0566<br>매출채권 / growth_divergence / 2.0133 | 없음 |
| 테라사이언스 | 10 | 당기순이익 / growth_divergence / 10.0<br>현금및현금성자산 / single_account_yoy / 8.4572<br>재고자산 / growth_divergence / 8.1893<br>금융수익 / single_account_yoy / 6.1652<br>파생상품부채 / universal_yoy / 5.7218 | 없음 |
| 한국화장품제조 | 6 | 단기금융자산 / universal_yoy / 3.0<br>이연법인세자산 / universal_yoy / 2.4802<br>매입채무및기타유동채무 / universal_yoy / 1.9778<br>현금및현금성자산 / universal_yoy / 1.7496<br>매출채권 / universal_mix_shift / 1.428 | 없음 |
| SK증권 | 0 |  | 없음 |
| 이구산업 | 9 | 영업이익 / universal_yoy / 10.0<br>매출총이익 / universal_yoy / 5.8914<br>이자비용 / universal_yoy / 3.1144<br>법인세비용차감전순이익 / universal_yoy / 1.6388<br>당기순이익 / universal_yoy / 1.4566 | 없음 |
| 가온그룹 | 9 | 유동성사채 / universal_yoy / 9.053<br>재고자산 / growth_divergence / 5.5793<br>당기순이익 / growth_divergence / 5.1133<br>영업이익 / single_account_yoy / 4.1278<br>금융수익 / single_account_yoy / 2.6446 | 없음 |
| 하나금융20호기업인수목적 | 2 | 단기금융상품 / universal_mix_shift / 2.618<br>자본잉여금 / universal_mix_shift / 2.356 | 없음 |
| 온타이드 | 9 | 재고자산 / growth_divergence / 7.282<br>현금및현금성자산 / universal_mix_shift / 2.586<br>기타포괄손익누계액 / universal_yoy / 2.4822<br>매출총이익 / single_account_yoy / 1.7656<br>법인세비용 / single_account_yoy / 1.7044 | 없음 |
| 나래나노텍 | 10 | 장기차입금 / growth_divergence / 10.0<br>재고자산 / growth_divergence / 9.0447<br>계약자산 / growth_divergence / 7.546<br>이연법인세자산 / universal_yoy / 3.026<br>자본잉여금 / universal_yoy / 2.9436 | 장기차입금 divergence -309.28pp |
| 한국큐빅 | 9 | 장기차입금 / growth_divergence / 10.0<br>당기순이익 / growth_divergence / 10.0<br>유동성장기차입금 / universal_yoy / 3.1586<br>기타비용 / single_account_yoy / 2.3876<br>기타유동자산 / single_account_yoy / 1.9814 | 장기차입금 divergence -376.61pp<br>당기순이익 divergence 461.43pp |
| KB스타리츠 | 0 |  | 없음 |

## 한계
- LLM·외부검색 없이 L0~L2 숫자 신호만 본다.
- 새 임계값을 만들지 않고 기존 red_flags/universal 신호만 채점했다.
- cfs_ofs_gap은 자회사 구조가 있으면 넓게 발생하므로 발굴·strict 판정에서 제외했다.
- 중과실·연결특화·다년분식·단일연도 데이터는 Stage1 숫자 신호만으로 한계가 있다.
