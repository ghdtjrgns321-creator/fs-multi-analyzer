# STATE — 현재 작업 상태

> 새 세션·다른 프롬프트는 **이 파일부터** 읽는다. "지금 어디까지 됐고 다음은 무엇인가."
> 작업 종료 시 반드시 갱신한다. 전체 흐름은 [OVERVIEW.md](OVERVIEW.md), 상세 설계는
> [PLAN.md](PLAN.md), 할 일 전체는 [ROADMAP.md](ROADMAP.md).

## 현재 위치

- 단계: 설계 확정 → 프로젝트 뼈대 구축 → L0 수집 → L1 정규화 → L2 신호엔진 →
  **S1 전기/전전기 금액 보존 + S2 소급재작성 신호 + S3 재무제표 5종 신호 완료**
- 최근 작업 (2026-06-03): BS 34개, IS 17개, CF 18개 canonical을 raw account_id 기반으로
  등록하고 L1 정규화를 재실행했다. `src/signals/universal.py`를 추가해 BS·IS·CF 모든
  account_id에 YoY, z-score, 구성비 급변, CFS/OFS 괴리 신호를 적용했다. relationship chain에는
  영업이익→순이익, 차입금→재무활동CF→투자활동CF/CAPEX, 순이익→영업CF→운전자본변동,
  연결 구조·비지배지분 사슬을 추가했다. L4 6관점 live에서 사업결합순현금유출,
  장기차입금차입, 운전자본변동, 기타수익 z-score, 장기금융상품 취득, 기타자본항목 CFS/OFS
  괴리가 queue 상위로 올라왔고, 교차 결과는 사업결합순현금유출 conflict로 나왔다.

## 완료

- 설계 단일 출처 [PLAN.md](PLAN.md) — 아키텍처 L0~L6, 원칙 5개, MVP 1~3
- 결정 D1~D4 ([DECISION.md](DECISION.md))
- 스킬 2종(`disclosure-review`/`disclosure-testing`) + skill-rules.json
- CLAUDE.md, pyproject.toml, config/playbooks, src/ 스캐폴딩, `src/schemas/findings.py`
- Codex/비-Claude 진입점 [../../AGENTS.md](../../AGENTS.md) + [CODEX.md](CODEX.md)
- L0 수집 모듈 [../../src/collect](../../src/collect)
- L0 raw 데이터 `data/companies/00126380/{2022,2023,2024,2025}/raw/`
- Raw 데이터 계약 [DATA_CONTRACT.md](DATA_CONTRACT.md)
- L1 정규화 모듈 [../../src/normalize](../../src/normalize)
- L1 canonical config [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- L1 정규화 결과 `data/companies/00126380/{2022,2023,2024,2025}/analysis.duckdb`
- L1 측정 보고서 [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md)
- 결정 D5 ([DECISION.md](DECISION.md))
- L2 tool DSL [../../src/analysis_tools](../../src/analysis_tools)
- L2 MVP1 관계 사슬 계산 [../../src/signals](../../src/signals)
- L2 계산 보고서 [SIGNAL_REPORT.md](SIGNAL_REPORT.md)
- L2 threshold 빨간불 추출 [../../src/signals/red_flags.py](../../src/signals/red_flags.py)
- 수치 분석가 1명 [../../src/agents/numeric_analyst.py](../../src/agents/numeric_analyst.py)
- D82242 주석 인덱서 [../../src/notes/indexer.py](../../src/notes/indexer.py)
- 매출채권 주석 분석가 [../../src/agents/note_analyst.py](../../src/agents/note_analyst.py)
- 매출채권 주석 매핑 [../../config/playbooks/note_mappings.yaml](../../config/playbooks/note_mappings.yaml)
- 외부 맥락 스키마 [../../src/schemas/context.py](../../src/schemas/context.py)
- Google Search grounding ContextBrief [../../src/agents/context_brief.py](../../src/agents/context_brief.py)
- 범용 계정 Finding 파이프라인 [../../src/agents/account_finding.py](../../src/agents/account_finding.py)
- 재고 Finding 실행점 [../../src/agents/first_inventory_finding.py](../../src/agents/first_inventory_finding.py)
- 첫 Finding 실행 기록 [FINDING_REPORT.md](FINDING_REPORT.md)
- Gemini 일시 오류 재시도 테스트 [../../tests/test_red_flags_and_agent.py](../../tests/test_red_flags_and_agent.py)
- 주석 파싱/주석 분석가 mock 테스트 [../../tests/test_notes_and_note_agent.py](../../tests/test_notes_and_note_agent.py)
- 외부 맥락 출처/비오염 테스트 [../../tests/test_context_brief.py](../../tests/test_context_brief.py)
- 재고 계정 파이프라인 mock 테스트 [../../tests/test_account_finding_pipeline.py](../../tests/test_account_finding_pipeline.py)
- 결정 D6 ([DECISION.md](DECISION.md))
- 결정 D8 ([DECISION.md](DECISION.md))
- 감사기준·K-IFRS 근거 평가 [AUDIT_BASIS.md](AUDIT_BASIS.md)
- 관계 사슬별 audit_basis 매핑 [../../config/playbooks/relationship_chains.yaml](../../config/playbooks/relationship_chains.yaml)
- 실무 재무지표 플레이북 [../../config/playbooks/financial_ratios.yaml](../../config/playbooks/financial_ratios.yaml)
- 2단계 기준 선정 방법론 [../user/METHODOLOGY.md](../user/METHODOLOGY.md)
- 기본 합계 계정 7개 추가 [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- 실무 재무지표 계산기 [../../src/signals/ratios.py](../../src/signals/ratios.py)
- 삼성 3개년 실무 재무지표 보고서 [RATIO_REPORT.md](RATIO_REPORT.md)
- L4 통합 리포트 조립기 [../../src/report](../../src/report)
- 삼성 L4 통합 리포트 [INTEGRATED_REPORT.md](INTEGRATED_REPORT.md)
- 통합 리포트 결정론/LLM mock 테스트 [../../tests/test_integrated_report.py](../../tests/test_integrated_report.py)
- 결정 D9 ([DECISION.md](DECISION.md))
- 결정 D10 ([DECISION.md](DECISION.md))
- 결정 D11 ([DECISION.md](DECISION.md))
- 결정 D13 ([DECISION.md](DECISION.md))
- 결정 D14 ([DECISION.md](DECISION.md))
- 결정 D15 ([DECISION.md](DECISION.md))
- L4 6관점 live 통합 리포트 [INTEGRATED_REPORT.md](INTEGRATED_REPORT.md)
- 동종업계 피어 config [../../config/industry_peers.yaml](../../config/industry_peers.yaml)
- 피어 지표 baseline [../../src/peers](../../src/peers)
- 남은 주석 카테고리 매핑 [../../config/playbooks/note_mappings.yaml](../../config/playbooks/note_mappings.yaml)
- 장기차입금·사채·충당부채 canonical 보강 [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- BS·IS·CF 주요 canonical 확장 [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- IS·CF 흐름 관계 사슬 보강 [../../config/playbooks/relationship_chains.yaml](../../config/playbooks/relationship_chains.yaml)
- 전 계정 보편 스캔 [../../src/signals/universal.py](../../src/signals/universal.py)
- 2025 포함 raw contract [DATA_CONTRACT.md](DATA_CONTRACT.md)

## 백테스트 (검증 — 진행 중, 2026-06-03)

> "토이 같다"는 인식의 근본 원인 = 검증 증거 부재(건강한 회사 1곳만 분석). 실제 분식 사건에
> 도구를 돌려 탐지율을 정량 측정한다.

- **익명 사례집 → 검색 특정은 폐기.** 금감원 감리지적사례(HWP146+PDF84, Codex 파싱 542사례)는
  일부러 익명화·금액 마스킹돼 있어, 가장 구별력 높은 단서조차 웹검색으로 회사 특정 불가.
  업종+연도만으론 후보가 너무 많아 오특정(정답지 오염) 위험. 파싱 산출(분식유형 분포)은 참고로만.
- **방향 전환 = 실명 공개 확정사건으로 정답지 구성**(옵션1 유명사건 + 옵션2 증선위 의결 실명).
  `data/backtest/known_cases.json`(내 검증) → `src/backtest/build_labels.py` → `data/backtest/labels.csv`.
- **실행 가능 8건 확정**(OpenDART 2015~ 가용·상장): positive 6(두산에너빌리티·아스트·디아이동일·
  모델솔루션·셀트리온·세토피아) + clean 1(삼성전자) + negative 1(KAI, 법원 무죄·과징금취소).
  럭슬은 출처 1개뿐이라 제외. reference 7건(대우조선·대우건설·효성·경남기업·STX·모뉴엘·중국고섬)은
  pre-2015/비상장이라 실행불가, 패턴 참고용.
- 정답지·검증방법·각 사건 한계는 사람용 문서 [../user/BACKTEST.md](../user/BACKTEST.md)에 문서화.
  각 사건 한계: 중과실(두산·셀트리온), 연결특화(디아이동일), 상장시점(모델솔루션), 손익영향 제한(세토피아).
- **Stage1 백테스트가 핵심 엔진 버그를 발견**: 전수 스캔 `universal_min_abs_amount: 1조원`(절대값)이
  삼성 같은 거대사에만 맞아, 중소형 분식사(아스트 0.58조·세토피아 0.06조)는 전 계정이 규모 미달로
  스캔 0건이 된다. "계정매핑실패"는 오해 라벨이고 실제론 매핑 정상·규모 필터 탈락. 수정 방향:
  규모 임계를 자산총계 대비 비율(%)로 상대화(`universal_min_pct_of_assets`) + 절대 하한 1억.
  miss_reason도 정직하게(계정부재/규모미달/변동미미/상위10밖) 재정의.

## 백테스트 Stage1 결과 + 해부 (2026-06-03)

- Stage1 결정론 백테스트 실행·재채점 완료. recall: 분식계정 신호 발화 5/6(세토피아만 단일연도),
  상위10 엄격 hit 2/6(두산 미청구공사 z=-16·모델솔루션 당기순이익). 정상 삼성은 채점대상 79개 →
  결정론 단독은 발굴기지 판별기가 아님을 실증(멀티에이전트 층 정당화).
- 사건별 해부 → [../user/BACKTEST_ANALYSIS.md](../user/BACKTEST_ANALYSIS.md). "잡을 수 있었는데
  못 잡음(도구 약점)" 3가지 식별:
  1. 노이즈 매몰(단일 계정 신호 과다 → 분식계정 중위권 매몰, 아스트 재고 68위).
  2. account_id 변경 시 시계열 단절(연결 편입으로 디아이동일 수익 +4088% 점프가 신호 누락).
  3. CFS-only 처리로 OFS-only 연도 누락(세토피아 2017·2018 별도 존재하는데 "데이터부족" 오판).
- 결정론 본질적 한계(→LLM/주석/동종업계): 점진적 분식(셀트리온 개발비 매년 +3~14% 자본화),
  관계로만 드러나는 분식(아스트 재고↑ vs 매출원가 flat), 움직임 포착 후 분식 여부 판단.

## 백테스트 Stage1 수정 ②·③ (2026-06-04)

- `src/signals/universal.py`: 전수 보편 스캔 시계열 키를 `account_id|label`에서
  canonical 우선, 미매핑 정규화 label 기준으로 변경했다. account_id는 evidence locator로
  보존한다. mapped canonical 중복은 연도별 합산하고, 미매핑 label 중복은 금액이 큰 대표 행을
  사용해 유동/비유동 등 우연한 label 중복 이중계상을 피한다.
- `src/signals/universal.py`: CFS 연속 시계열이 불완전하면 OFS 기준을 선택하고, 한 신호
  계산 안에서 CFS/OFS를 섞지 않는다. `src/normalize/pipeline.py`와
  `src/backtest/run_backtest.py`도 CFS/OFS 둘 중 하나만 있어도 해당 연도를 정규화·평가하도록
  바꿨다.
- 검증 결과: 세토피아는 available `[2017, 2018, 2019]`로 데이터부족이 해소되고
  `금융부채`가 상위10밖(14위)으로 재분류됐다. 디아이동일은 `수익` 상위10밖(35위)으로
  신호는 유지되나 hit는 아니다. 삼성전자는 clean 유지, 모델솔루션은 hit 유지. 두산에너빌리티는
  `미청구공사` z-score가 생성됐지만 상위10 기준 12위라 hit에서 miss로 남았다. 채점 로직과
  신호 임계값은 변경하지 않았다.

## 백테스트 P7 관계엔진 연도 수정 (2026-06-04)

- `src/signals/mvp1.py`: `build_mvp1_signal_report`가 `relationship_chains.yaml`의
  `l2_mvp1.years` 대신 frame 실제 연도 또는 호출자가 넘긴 years를 분석 윈도우로 사용한다.
  `src/signals/spike.py`와 L4 회사 리포트 호출부도 years를 명시 전달한다. YAML의 `years`는
  분석 윈도우 제어용이 아님을 deprecated 주석으로 표시했다.
- 재실행 결과: 삼성전자 2022~2025는 기존 config 윈도우와 같아 raw fired 125와 top10 구성이
  불변이다. 아스트는 `cogs-vs-inventory` 관계 신호가 2017, 2018, 2019, 2020, 2022년에
  발화했다. 가장 강한 2022 신호는 99.97pp, 정규화강도 6.6647, 전체 채점대상 61위다.
- strict positive recall은 1/6으로 유지됐다. 모델솔루션 hit 유지, 삼성 clean 유지.
  관계 신호 복구로 KAI negative control은 개발비가 10위에서 19위로 밀려 hit가 False가 됐다.
  채점 로직·임계값·상위10 기준은 변경하지 않았다.

## L4 삼성 하드코딩 일반화 (2026-06-04)

- `src/report/company_report.py`: 삼성 전용 `COMPANY_NAMES`/`COMPANY_DOMAINS` map을 제거하고,
  회사명·업종 메타데이터는 OpenDART `DartCollector.company(corp_code)` 프로필에서 채운다.
  API/profile이 없으면 corp_code 기반으로 degrade하되 분석 계산은 계속 인자와 데이터로만 수행한다.
- `src/peers`와 `config/industry_peers.yaml`: 피어 config를 target corp_code별 구조에서
  DART `induty_code`별 구조로 변경했다. 대상 회사의 `induty_code`가 config에 없으면
  `industry` 관점만 `피어 미구성`으로 deferred된다. 기존 264 피어는 264 업종에만 적용된다.
- `src/report/industry.py`: 삼성전자 사업 다각화 문구를 제거하고, 대상 회사 일반 caveat
  ("대상 회사의 사업구조가 피어와 달라 단순 비교에 한계")로 바꿨다. `industry` 관점은 계속
  판단 필드를 바꾸지 않는 참고 관점이다.
- 데모 러너(`first_*`, `ratios.py`)는 corp_code/year CLI 인자를 받도록 정리했다. 기본값은
  데모 편의용이며 분석 함수 본체의 대상 선택을 좌우하지 않는다.
- Stage1 백테스트는 L4 변경 영향 없이 직전 결과와 동일했다. positive recall 1/6, 삼성 clean,
  모델솔루션 hit, KAI negative hit False를 유지했다.

## Stage1 신호 아티팩트 억제 Tier 1+2 (2026-06-04)

- `src/signals/universal.py`: universal YoY/z-score/mix 스캔에서 CF 계정을 제외하고 BS·IS만
  대상으로 삼았다. CF는 기존 관계사슬과 방향 신호가 담당한다. `scan_cfs_ofs_gaps`는 변경하지
  않았다.
- YoY/mix는 전년 금액이 동적 floor 이상이고 전년·당년 부호가 같을 때만 계산하도록 기저
  가드를 추가했다. 0 근처 폭발·부호반전 YoY 아티팩트를 제거한다.
- universal z-score는 `config/playbooks/relationship_chains.yaml`의
  `universal_z_score_cap: 10`으로 캡한다. 기존 `z_score_abs: 2`, `yoy_pct_abs: 50` 등
  신호 임계값은 변경하지 않았다.
- `src/backtest/score.py`: raw fired_signals는 보존하되, strict top10과 account_scores 산정은
  같은 계정명당 최강 신호 1개로 dedupe한다. hit 규칙(분식계정이 고유 계정 top10 안에 있으면 hit)은
  유지했다.
- 재실행 결과: positive strict hit는 1/6 → 3/6으로 상승했다. 모델솔루션 당기순이익 1위 유지,
  셀트리온 재고자산 9위, 세토피아 금융부채 4위가 포착됐다. 아스트 재고자산 16위,
  디아이동일 수익 13위, 두산 미청구공사 12위로 올라왔지만 여전히 strict hit는 아니다.
  삼성 clean은 유지되고 raw fired는 125 → 110으로 줄었다. KAI negative control은 공사진행률/매출
  9위로 다시 hit=True가 됐다.

## Stage1 mvp1 Tier 1 가드 확장 (2026-06-05)

- `src/signals/mvp1.py`: universal에 적용했던 Tier 1 기저 가드를 관계엔진에도 확장했다.
  `single_account_yoy`는 raw `primary_yoy` 테이블에는 CF 계정을 보존하되, red flag 발화에서는
  `sj_div == "CF"`를 제외한다. CF 흐름은 기존 direction/growth 관계 신호가 담당한다.
- `growth_divergence`는 양쪽 계정 모두 전년 금액이 동적 floor
  `max(자산총계 x 1%, 1억)` 이상이고 전년·당년 부호가 같을 때만 growth%와 divergence를
  채운다. 한쪽이라도 0 근처 기저·부호반전이면 해당 연도 divergence는 `None`으로 둔다.
- 채점 hit 규칙·상위10 기준·기존 신호 임계값은 변경하지 않았다. P4 순위 공정성도 이번 범위에서
  건드리지 않았다.
- 재실행 결과: positive strict hit는 3/6 → 6/6으로 상승했다. 두산 미청구공사 2위,
  아스트 재고자산 6위, 디아이동일 수익 7위, 모델솔루션 당기순이익 1위, 셀트리온 재고자산
  3위, 세토피아 금융부채 4위가 포착됐다. 아스트 `cogs-vs-inventory`는 2017 -43.85pp,
  2022 99.97pp 등 material 기저라 유지됐다. 기존 908pp급 장기차입금 0근처 폭발은 사라졌고,
  material 기저에서 나온 장기차입금 관계 신호만 남았다. 삼성 clean은 유지되고 raw fired는
  110 → 87로 줄었다. KAI negative control은 hit False, miss_reason `변동미미`다.

## Stage1 홀드아웃 검증 — 엔진 동결 (2026-06-05)

- `src/backtest/build_labels.py`: 입력/출력 경로 인자를 추가해
  `known_cases_holdout.json` → `labels_holdout.csv`를 생성했다. 기본 `known_cases.json` →
  `labels.csv` 동작은 유지한다.
- `src/backtest/run_backtest.py`: `--labels` 인자를 추가했다. `labels_holdout.csv` 실행 시
  `backtest_results_holdout.jsonl`과 `BACKTEST_REPORT_holdout.md`를 생성한다. 삼성/KAI 전용
  보고 줄은 해당 회사가 있을 때만 출력한다. clean 회사처럼 fraud_year가 없으면 `run_years`로
  윈도우를 잡는다.
- 신호엔진(`src/signals/*`), `score.py`, config 임계값은 변경하지 않았다. 기존 labels 백테스트는
  positive 6/6, 삼성 clean, KAI `변동미미`로 유지됐다.
- 홀드아웃 결과: positive 3/3. 티피씨메카트로닉스 재고자산 2위, 유네코 매출채권 7위,
  본느 재고자산 6위가 top10에 들어 hit다. 정상 5곳(NAVER, KT&G, 오리온, 한미반도체,
  영원무역)은 모두 hit False다.
- 정상군 잔여 아티팩트: NAVER는 당기순이익 divergence -1854.67pp, 관계기업투자 YoY
  1574.99%, 유형자산취득 divergence -458.52pp가 상위5에 남았다. 한미반도체는 기타수익
  YoY 5239.94%가 상위5에 남았다. KT&G, 오리온, 영원무역은 상위5 기준 극단 아티팩트 후보가
  없다. 삼성 baseline raw fired 87과 비교하면 NAVER 88, 영원무역 110은 비슷하거나 더 높아
  Stage1 숫자 신호 단독은 여전히 검토 큐 생성기이지 판별기가 아니다.

## Stage1 single_account_yoy 기저 가드 완성 + 강도 캡 (2026-06-05)

- `src/signals/mvp1.py`: `single_account_yoy`의 전년 기저 판정을 대상 연도 동적 floor 기준으로
  보강했다. 예: 한미반도체 기타수익은 2022 전년 56억이 2023 자산총계 1% floor 72억에
  못 미쳐 `single_account_yoy` red flag에서 제외됐다. `primary_yoy` 테이블에는 값과
  `valid_yoy_base=False`를 보존한다.
- `config/playbooks/relationship_chains.yaml`: 원칙값 `signal_strength_cap: 10`을 추가했다.
  `src/backtest/score.py`는 `%/pp` 기반 신호(`single_account_yoy`, `universal_yoy`,
  `growth_divergence`, `universal_mix_shift`)의 normalized_strength만 10으로 캡한다.
  raw metric_value는 증거로 보존한다. z-score는 기존 raw z cap을 그대로 쓴다.
- 재실행 결과: 튜닝 세트 positive 6/6 유지, 삼성 clean 유지(raw fired 87), KAI negative
  `변동미미` 유지. 홀드아웃 positive 3/3 유지. 본느 재고자산은 6위→5위, 유네코 매출채권
  7위 유지, 티피씨 재고자산 2위 유지.
- 정상군 효과: 한미반도체 기타수익 YoY 5239.94% 신호는 top5에서 사라지고 fired 60→59로
  줄었다. NAVER의 극단 raw 값(당기순이익 divergence -1840.96pp, 관계기업투자 YoY
  1574.99%)은 raw 증거로 남지만 normalized_strength는 10으로 캡되어 123배·31배 강도로
  순위를 지배하지 않는다.

## Stage1 데이터 정리 시도 — 중단 (2026-06-05)

- 요청 범위대로 신호 임계·채점 hit 규칙은 건드리지 않고 정규화 중복행 제거, BS 소계
  `is_subtotal` config 표시, 매출 alias 보강을 적용해 재실행했다.
- 정규화 중복은 16개 실행 회사 모두 `(account_id, label, year, fs_div, sj_div)` 기준 0건으로
  수렴했다. 소계 계정(`자산총계`, `유동자산`, `부채총계`, `자본총계` 등)은 universal/
  single_account_yoy scoring fired_signals에서 0건으로 사라졌다.
- 그러나 튜닝 세트 positive가 6/6 → 2/6으로 깨졌다. 두산과 모델솔루션만 hit 유지,
  아스트 재고자산 16위, 디아이동일 수익 14위, 셀트리온 재고자산 13위, 세토피아 금융부채
  `변동미미`로 내려갔다. 홀드아웃 positive 3/3은 유지됐다.
- 원인 관찰: BS 소계 제거 자체는 정상 작동했지만, 중복행 제거 후 기존에 덜 보이던 확장계정
  YoY 신호(아스트 임차보증금/미수금/유동파생상품부채, 셀트리온 기타수취채권/기타비용 등)가
  top10을 점유했다. 세토피아는 `금융부채`가 score.py의 현재 동치 매핑상 `부채총계`에
  묶여 있어, BS 소계 제외 후 더 이상 hit에 기여하지 않는다.
- 지시대로 여기서 추가 튜닝을 중단한다. 다음 결정 필요: 소계 제외를 유지할지, score의
  `금융부채→부채총계` 동치 매핑을 데이터 매핑으로 대체할지, 확장계정 alias/소계 판별을 더
  정교화할지.

## Stage1 백테스트 지표 재정의 — 발굴 recall 중심 (2026-06-05)

- 데이터 정리(B1/B2/B4)는 유지했다. 중복행 제거, BS 소계 제외, 매출 alias 보강은 되돌리지 않았다.
- `src/backtest/score.py`: 주 지표를 strict top10 hit가 아니라 분식계정 발굴 recall로 분리했다.
  `account_scores.status`가 `포착` 또는 `상위10밖`이면 `discovered=True`다. 기존 top10 기준은
  `hit` 필드와 리포트의 `상위10 strict hit` 보조 지표로 유지한다.
- `score.py`의 소계 crutch 매핑을 제거했다. 특히 `금융부채→부채총계`, `금융자산→기타 중요 계정`,
  `자기자본→자본총계`를 제거했다. 분식계정은 실제 line item 또는 canonical alias로만 잡는다.
- 재실행 결과: 튜닝 세트는 발굴 recall 5/6, 상위10 strict 2/6이다. 두산 미청구공사와
  모델솔루션 당기순이익은 strict hit, 아스트 재고/매출원가, 디아이동일 종속기업투자·수익,
  셀트리온 재고는 발굴됐지만 top10 밖이다. 세토피아 금융자산/금융부채는 `변동미미`로,
  recall로도 잡히지 않는다.
- 홀드아웃은 발굴 recall 3/3, 상위10 strict 3/3이다. 티피씨 재고자산 2위, 유네코 매출채권 8위,
  본느 재고자산 4위가 strict hit다.
- 해석: Stage1 결정론은 분식계정이 후보로 뜨는지 보는 발굴기다. 정상 변동과 분식 후보를
  최종 판별하는 순위/맥락 판단은 다음 층(관계 우선, 주석/LLM, 외부/동종업계 교차)에서 다룬다.

## Stage1 빈 mvp1 테이블 robustness 수정 (2026-06-05)

- `compare_growth`, `account_yoy_table`, `direction_table`, `build_mvp1_signal_report`가 빈 결과에서도
  기대 컬럼을 가진 빈 DataFrame을 반환하도록 보강했다. 단일연도/관계계정 없음 케이스에서
  `growth_divergences`가 `(0,2)`의 `id,name`만 남아 `divergence_pp` KeyError를 내던 문제를 막았다.
- `red_flags.py`는 growth/yoy/direction 입력 테이블이 비어 있거나 필요 컬럼이 없으면 `[]`를
  반환한다. 크래시 대신 빈 신호로 degrade한다.
- 재현 확인: `run_signal_spike('00688996', [2023])` 후 `extract_red_flags(..., 2023)`이 `[]`를
  반환한다. 기존 백테스트 결과는 유지됐다(기본 발굴 5/6·strict 2/6, 홀드아웃 발굴 3/3·strict 3/3).

## 매출채권 조합 라벨 proxy 매핑 (2026-06-05)

- `config/canonical_accounts.yaml`: `매출채권 및 기타유동채권`, `매출채권 및 기타채권`,
  `매출채권및기타채권`을 canonical `매출채권` alias로 추가했다. 조합 수취채권 라벨이므로
  기타채권이 포함되지만 매출채권 사슬 복구용 proxy로 수용한다.
- `장기매출채권 및 기타비유동채권` 등 장기/비유동 조합은 이번 alias에 넣지 않았다.
- 검증 결과: 기존 백테스트 결과는 유지됐다(기본 발굴 5/6·strict 2/6, 홀드아웃 발굴 3/3·strict 3/3).
  빈 mvp1 테이블 재현도 계속 크래시 없이 `[]`를 반환한다.

## 매입채무 조합 라벨 proxy 매핑 (2026-06-05)

- `config/canonical_accounts.yaml`: `매입채무 및 기타유동채무`, `매입채무및기타채무`,
  `매입채무 및 기타채무`를 canonical `매입채무` alias로 추가했다. 매출채권 조합 라벨과 같은
  proxy 원칙이다.
- 투자부동산·전환사채는 case-specific/스코프 확장 위험이 있어 이번 매핑에서 제외했다.
- 검증 결과: 기존 백테스트 결과는 유지됐다(기본 발굴 5/6·strict 2/6, 홀드아웃 발굴 3/3·strict 3/3).

## 백테스트 홀리스틱 리뷰 — Codex 독립 산출 (2026-06-05)

- `data/backtest/review_packets_0_45.txt`, `review_packets_45_90.txt`, `review_packets_90_200.txt`의
  121사 공용 패킷만 사용해 [../../data/backtest/REVIEW_CODEX.md](../../data/backtest/REVIEW_CODEX.md)를
  작성했다. 외부 검색·실명 추정·코드/config 수정은 하지 않았다.
- 사용자의 추가 재검토 지시에 따라 스크리닝식/체크리스트식 리뷰를 폐기하고 심층 감사조서식 리뷰로
  다시 작성했다. 회사별로 핵심 판단, FS 읽기(BS/IS/CF·운전자본·손익-현금 괴리), 엔진 신호 검토,
  데이터·매핑 검토, 다음 검토 포인트를 분리해 121사 전부 기록했다.
- 집계: 항등식 불일치 0사, 핵심 입력 결측 93건, 핵심 미매핑 84건, 극단 신호/아티팩트 145건,
  엔진 신호 없음 12건, positive 중 분식계정 미발굴 1사(세토피아), clean 강한 신호 5개 이상 51사.
- 이 문서는 Claude 독립 리뷰와 교차검증할 Codex 측 회사별 회계 감각 리뷰 산출물이다.

## FIX 1·2·4 — 매핑 완전화·진행률 계정·sanity 가드 (2026-06-05)

- FIX 1: `normalize_label`이 alias 비교 전 후행 `(손실)/(이익)/(손익)`만 제거하도록 보강했다.
  `당기순이익(손실)`은 `당기순이익`으로 매핑되고, `수익(매출액)` 같은 총액 매출 라벨은 보존된다.
  매출 alias는 총액 라벨(`영업수익`, `수익(매출액)`, `재화의 판매로 인한 수익(매출액)`, `방송수익`)
  중심으로 보강하고, `제품매출` 같은 구성요소는 매출로 끌지 않는다.
- FIX 2: `계약자산`, `계약부채`, `공사손실충당부채` canonical과 `매출 vs 계약자산 증가율 괴리`
  관계사슬을 추가했다. 정규화는 mapped canonical에 대해 회사·연도·fs_div당 대표 1라인만 남기며,
  canonical statement(BS/IS/CF)를 우선해 SCE/CF 중복 라벨이 IS/BS 대표행을 밀어내지 않게 했다.
  새 canonical과 충돌하던 score의 `공사손실충당부채→충당부채` 우회매핑도 제거했다.
- FIX 4: `src/signals/sanity.py`를 추가해 자산총계가 인접/중앙값 대비 100배 이상 튀는 연도를 신호 계산에서
  제외한다. 소프트센(00204226) 2022년이 `suspicious_asset_years == [2022]`로 검출되고 신호 입력에서
  제외됨을 확인했다.
- 안전선 확인: 기본+홀드아웃 재정규화 후 `매출/매출채권/매입채무/자산총계/계약자산/계약부채/당기순이익`
  canonical의 회사·연도·fs_div 중복은 0건이다. 백테스트 결과는 기본 발굴 5/6·strict 2/6,
  홀드아웃 발굴 3/3·strict 3/3이다.
- FIX 3: 신호를 제거하거나 raw 값을 감쇠하지 않고, 대상 계정 당해연도 금액/자산총계 비율로
  트랙 A(규모 계정)와 트랙 B(소액 급변)를 분리 게시한다. 설정은
  `track_split_pct_of_assets: 5.0`, `track_a_quota: 6`, `track_b_quota: 6`이다.
  결과 JSON과 리포트는 기존 단일 top10 strict와 새 track quota hit를 병기한다.
  mega(126사: positive 16, clean 110) 재실행 결과는 발굴 15/16, legacy strict 14/16,
  track hit 13/16이다. 아스트 재고자산은 트랙 A 6위, 셀트리온 재고자산은 트랙 B 2위로
  정원 내 게시된다. 정상 110사의 강도 10 신호는 legacy top10 기준 111개, track A 기준 75개다.
- Stage2 LLM 강화: L4 내부 분석·판정 관점과 synthesis를 GPT-5.4로 전환했다. 외부 검색 관점은
  Gemini 3.1 Pro preview + Google Search grounding을 유지한다. `material_board`는 더 이상
  review_queue 중심이 아니라 핵심 계정 수준 시계열과 전체 지표 시계열을 포함한다. 아스트
  2015~2019 live에서 numeric/flow/change 관점이 review_queue 밖 재고자산을 DIO 432.95,
  재고회전율 0.84, 재고자산 증가 근거로 직접 제기했다.
- 피어 DB 구축: `industry` 관점 매칭을 DART `induty_code` 앞 3자리 중분류로 바꿨고,
  `known_cases_mega.json` + `known_cases_gap.json` 표본의 73개 중분류를 대상으로
  `config/industry_peers.yaml`에 72개 중분류/601개 피어를 등록했다. 표본/known case 회사와
  피어 overlap은 0건이다. 10개 미만 업종은 26개이며, `266`은 피어 후보가 없어 미등록이다.
  아스트 `31322`는 `313`으로 매칭되고, industry baseline은 DIO 432.95 vs 피어 중앙값 46.8,
  재고회전율 0.84 vs 피어 중앙값 7.8을 산출했다. L4 live에서 `industry / completed / High`를
  확인했다.

## Stage1 마무리 — floor 버그·커버리지 갭·트랙 채점 확정 (2026-06-06)

- **floor 버그 발견·수정**: universal 스캔 materiality 하한이 `_exclude_subtotal_rows`로 자산총계를
  잃어 자산×1% 상대하한이 0→1억으로 추락하던 버그. 소계 제외 *전* frame으로 floor를 계산해 자산1%
  복원(현대건설 2023 floor 2,371억=자산1%). 정상 110사 강도10 노이즈 309→109개, 아스트 재고
  16→6위·셀트리온 재고 13→3위로 단일 잣대에서도 상승. ([../user/TROUBLESHOOT.md](../user/TROUBLESHOOT.md) 2026-06-06)
- **커버리지 갭 보강**: 제조 편중 표본에 빠진 업종(건설·통신·전기/가스·게임/SW·항공·물류·리테일·교육)
  대표 17사 추가 → 138사. 건설 4사로 FIX 2(계약자산/계약부채) 실증, DL이앤씨 유동계약자산/유동계약부채
  alias 누락 보강. 새 발견 유형 0(5가지 수렴 유지). ([../user/VERIFICATION.md](../user/VERIFICATION.md) 커버리지)
- **신규분식 5사 복원**: `known_cases_mega.json`의 신규분식(웰바이오텍·에스엘·이렘·더테크놀로지·한창)
  run_years가 비어 dart_ok=False로 빠져있던 stale 수정 → mega **16사 완전체**. 신규 5사 전부 발굴.
- **트랙 채점 확정**: FIX 3 두 트랙을 채점 잣대로 채택(track strict 13/16). 단일 top10(legacy 14/16)
  병기. 트랙 13<legacy 14는 유네코 매출채권이 A 정원 6 밖(7위)으로 잘린 것 — 정원은 오버피팅 회피로
  안 만진다. 트랙 고유 가치는 점수가 아니라 소액 부정 별도 노출(세토피아 B 1위).
- **핵심 통찰**: 노이즈 309개의 진짜 원인은 트랙(FIX 3)이 아니라 floor 버그였다. floor 수정만으로
  분식계정이 단일 잣대에서도 top10 진입. 트랙은 점수론 -1, 가치는 가독성.
- 7개 논리 커밋(develop). pytest 89·ruff 통과. 항등식 0/458.
- **Stage1(결정론 백테스트 검증) 종료.** 결정론은 발굴기(15/16), 정상과의 최종 판별은 Stage2 LLM 층.

## DART 데이터 커버리지 전수 감사 (2026-06-07)

- 사용자 요청에 따라 [../../data/backtest/COVERAGE_AUDIT2.md](../../data/backtest/COVERAGE_AUDIT2.md)를
  전수 기준으로 재작성했다. 표본은 positive 16사 + 정상 다양 10사 + 삼성전자 1사, 총 27사다.
- 회사-연도 모집단 119개에 대해 CFS/OFS 양쪽 raw `finstate_all` 계정 운명 39,612행을
  L0→L1→L2 단계로 추적했다. sidecar CSV는
  `data/backtest/coverage_audit_cache/account_fate_full.csv`다.
- DART API 커버리지는 report code 4종 × fs_div 2(952 레코드), 사업보고서 report API 28종
  (3,332 레코드), event/regstate/share/list(1,296 레코드)를 상태·행수 기준으로 확인했다.
  원문 payload는 출력하지 않았다.
- 주요 정량: BS/IS floor 미달 4,146/11,610(35.7%), L2 미스캔 SCE 11,317행·CF 10,503행·
  CIS 4,321행, `frmtrm_amount` 대조 가능 19,077 pair 중 3,744 불일치(현재 L1/L2 미사용).
- 재확인 결론: `reprt_code=11011`만 수집, CF/CIS/SCE 전수 스캔 누락, KAM/감사의견·정정공시·
  원문 주석 미수집, 주석 매핑 8/70 수준, `ord`/`currency`/전기·전전기 금액 미보존이 확인됐다.
  전기·전전기 금액 미보존은 아래 S1에서 해소했다.

## S1 전기/전전기 금액 정규화 보존 (2026-06-07)

- `src/normalize/pipeline.py`: `finstate_all`의 `frmtrm_amount`, `bfefrmtrm_amount`를 각각
  `prior_amount`, `prior2_amount`로 정규화 출력에 보존한다. `parse_amount`와
  `settings.amount_round_digits` 정책은 기존 `amount`와 동일하다. 비교표시 컬럼이 없는 raw도
  결측으로 degrade한다.
- `OUTPUT_COLUMNS`와 `src.analysis_tools.data.TOOL_COLUMNS`를 확장했다. DuckDB
  `normalized_financials`는 재정규화 시 새 스키마로 생성된다. 오래된 DB는 로더가 누락 컬럼을
  결측으로 채우지만, S2 검증에는 재정규화 DB를 사용해야 한다.
- dedupe 키·대표행 선정 로직은 변경하지 않았다. `_dedupe_statement_rows`는 계속
  `(account_id, label, year, fs_div, sj_div)`, `_dedupe_canonical_rows`는 계속
  `(canonical, year, fs_div)` 기준이며, 정렬 기준도 기존 `amount` 기반이다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 92개 통과. 기본 labels 백테스트는 발굴 5/6,
  legacy strict 5/6, track 5/6으로 유지됐다. mega 백테스트는 발굴 15/16, legacy strict 14/16,
  track 13/16으로 유지됐다.
- 16개 positive 회사 재정규화 결과: 총 19,101행, `prior_amount` 비결측 16,999행(89.00%),
  `prior2_amount` 비결측 16,676행(87.30%).
- 아스트 재고 대조 앵커: 2020 보고서 OFS 재고 `prior_amount` 41,854,541,192원(약 419억),
  2019 보고서 OFS 재고 `amount` 110,270,586,075원(약 1,103억)을 재현했다. 이는 S2의
  N년 전기 표시 vs N-1년 당기 대조 입력이다.

## S2 소급재작성 신호 (2026-06-07)

- `src/signals/restatement.py`: 정규화 frame에서 N년 보고서 `prior_amount`와 N-1년 보고서
  `amount`를 같은 line item 기준으로 대조하는 `scan_restatement_signals`를 추가했다.
  임계값은 `relationship_chains.yaml`의 `restatement_abs_amount: 100000000`,
  `restatement_rel_pct: 1.0`이다.
- restatement용 `scan_key`는 canonical 집계가 아니라 `account_id + normalized label` 기준이다.
  `-표준계정코드 미사용-`은 normalized label 기준으로 비교한다. canonical만 쓰면 서로 다른
  CIS/CF 세목이 같은 canonical으로 섞일 수 있어 line item 기준으로 좁혔다.
- `RedFlagSignal.signal_type == "restatement"`를 생성한다. `metric_value`는
  `prior_amount[N] - amount[N-1]` 원시 괴리 금액이고, evidence에는 N년 비교표시 값과
  N-1년 원래 공시 값을 각각 넣는다.
- 최초 S2 구현에서는 L4 `build_company_report`가 restatement 신호를 review queue와
  `latest_signal_snapshot["restatements"]`에 함께 포함했다. 아래 S2 마무리에서 review queue
  합산은 제거했고, `change_material`의 `restatement_signals` 단서만 유지한다.
- 검증: 신규 테스트 포함 `.venv\\Scripts\\python.exe -m pytest -q` 95개 통과. 기본 labels
  백테스트는 발굴 5/6, legacy strict 5/6, track 5/6으로 유지됐다.
- 16개 positive 회사 전수: 전 `sj_div` 기준 15/16사 394개 신호. 기존 감사 baseline과 같은
  BS line item 기준은 12/16사이며 모델솔루션·본느·이트론·에스엘의 BS 신호는 0이다.
  본느·이트론·에스엘은 전 `sj_div` 확장 시 CIS/CF/SCE 재분류·부호표시 변화가 추가로 잡힌다.
- 분식 직격 앵커: 셀트리온 2016 CFS 무형자산 −108,537,593,133원, 아스트 2020 CFS
  자산총계 −99,677,813,878원, 이렘 2020 CFS 매입채무 −62,726,226,951원이
  restatement 신호로 발생했다.
- 정상 10사 측정: 전 `sj_div` 기준 4/10사 19개 신호, BS 기준 0개다. 정상에서도 CF/SCE
  표시·재분류 신호가 있을 수 있으므로 L4 change 관점은 `sj_div`와 evidence를 함께 봐야 한다.

## S2 보완 — 소급재작성 거짓양성 억제 (2026-06-07)

- 생산 코드 변경은 `src/signals/restatement.py`에 한정했다. 소계 계정은 restatement 신호 후보에서
  제외하되, 자산총계는 자산 대비 floor 계산에는 계속 사용한다.
- 억제 가드: `subtotal_account_names` 기반 소계 제외, `rel_pct >= 1000%` 또는
  `prior_amount`/전년 `amount` 스케일 100배 이상 단위혼입 제외, `max(1억원, 자산총계 x 1%)`
  floor, `(account, fs_div, year, diff)` 중복 제거.
- 임계값은 `load_l2_config()["signal_thresholds"]`에서 읽고, YAML에 없는 값은
  `restatement_rel_pct_max=1000`, `restatement_scale_multiple_max=100`,
  `restatement_min_pct_of_assets=universal_min_pct_of_assets` fallback을 사용한다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 99개 통과, `.venv\\Scripts\\python.exe -m ruff check .`
  통과. 기본 labels 백테스트는 발굴 5/6, legacy strict 5/6, track 5/6 유지.
- 정상 10사 억제 후: 전 `sj_div` 기준 2/10사 2개, BS 기준 0/10사 0개. 이전 S2 측정
  4/10사 19개 대비 감소했다.
- 16개 positive 억제 후: 전 `sj_div` 기준 15/16사 157개, BS 기준 9/16사 33개. 이전 S2
  15/16사 394개, BS 12/16사 대비 신호 수가 줄었다. BS에서 빠진 두산에너빌리티,
  디아이동일, 웰바이오텍은 자산 1% floor 미달 소액 재분류 성격이다.
- 분식 앵커 유지: 셀트리온 2016 CFS 무형자산 −108,537,593,133원, 이렘 2020 CFS
  매입채무 −62,726,226,951원 유지. 아스트 2020 CFS 자산총계 −99,677,813,878원은 소계 제외로
  빠지고, 구성요소 재고자산 −80,511,480,581원이 유지된다.

## S2 마무리 — restatement 큐 제외·change 단서 격하 (2026-06-07)

- `src/report/company_report.py`: `restatement_signals`를 `all_signals` 합산에서 제거했다.
  따라서 review queue와 결정론 점수 산정에는 restatement가 들어가지 않는다.
- `latest_signal_snapshot["restatements"]`와 `change_material()["restatement_signals"]`는 유지한다.
  restatement는 결정론 큐가 아니라 change 관점 LLM의 맥락 단서다.
- `src/report/perspectives.py`: change 관점 rules에 소급재작성 해석 가이드를 추가했다. 회계정책 변경,
  중단영업 재분류, EPS 소급재계산, 오류수정, 사업결합 잠정조정, 연결범위 변동 등 정상 사유를
  위험으로 보지 말고, 이익·자산 과대계상 후 하향 재작성 패턴만 검토 후보로 제기하도록 했다.
  restatement 단독으로 High를 주지 말고, 금융자산·차입금·현금의 광범위 재분류/연결범위 변동은
  정상 소급 후보로 낮춰 보라는 가드도 추가했다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 101개 통과, `.venv\\Scripts\\python.exe -m ruff check .`
  통과. 기본 labels 백테스트는 발굴 5/6, legacy strict 5/6, track 5/6 유지.
- 정상 10사 실제 company report 확인: review_queue의 restatement 0건. change material에는
  target year에 남은 restatement 단서만 들어간다.
- change material 앵커 확인: 셀트리온 2016 무형자산 −108,537,593,133원, 아스트 2020
  재고자산 −80,511,480,581원 및 OFS 재고 −68,416,044,883원, 이렘 2020 매입채무
  −62,726,226,951원이 실린다.
- LLM 표본: 셀트리온 2016 change 관점은 무형자산 하향 재작성과 이익/자산 과대계상 후 하향
  가능성을 검토 후보로 제기했다. 다우기술 2023 change 관점은 restatement 단서 6개를 받았지만
  광범위 금융자산·차입금·현금 재분류와 연결범위 변동 가능성을 들어 Medium으로 낮춰 보고,
  분식 단정 대신 재작성 사유와 금융부채 재분류 맵핑 확인을 제안했다.

## S3 재무제표 5종 전수 신호 (2026-06-07)

- `config/canonical_accounts.yaml`: CIS canonical 10개(총포괄손익, 기타포괄손익,
  FVOCI/매도가능 평가손익, 해외사업환산, 현금흐름위험회피, 확정급여재측정 등)와 SCE canonical
  7개(기초자본, 배당변동, 자본금변동, 자본잉여금변동, 이익잉여금변동, 자기주식변동,
  기타자본변동)를 추가했다. `기초자본`은 roll-forward 시작 잔액이라 `is_subtotal`로 표시해
  universal 신호에서는 제외한다.
- `src/signals/universal.py`: 보편 스캔 대상 `sj_div`를 BS·IS에서 BS·IS·CIS·CF·SCE 5종으로
  확장했다. `scan_cfs_ofs_gaps`는 기존 BS·IS·CF 범위를 유지해 SCE/CIS CFS-OFS 괴리 신호가
  새로 섞이지 않게 했다.
- 노이즈 억제는 새 임계 없이 기존 장치를 재사용했다. 기존 floor/base/sanity/subtotal 제외를
  유지하고, mapped canonical은 `canonical_accounts.yaml`의 `statement`와 실제 `sj_div`가 맞을
  때만 universal 스캔한다. 예: CIS/SCE 표에 반복 표시된 `당기순이익`은 IS canonical이므로
  중복 신호에서 제외된다. 미매핑 확장계정은 전수 스캔 대상이라 그대로 둔다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 102개 통과,
  `.venv\\Scripts\\python.exe -m ruff check .` 통과. 기본 labels 백테스트는 positive 발굴
  5/6 유지(세토피아 `변동미미`). KAI negative control은 CF 확장 후 `무형자산취득` 등이
  top10에 들어 strict=True가 되어, CF 세목 신호는 정상/음성 통제에서 잔여 노이즈가 있음을
  확인했다.
- 삼성전자+16개 positive 재정규화/스캔 결과: 삼성은 funnel BS 177, IS 70, CIS 44, CF 158,
  SCE 19행, universal 신호 BS 6, IS 11, CIS 11, CF 13, SCE 1개다. 16개 positive는 funnel
  BS 2,156, IS 437, CIS 871, CF 2,892, SCE 449행, universal 신호 BS 254, IS 32, CIS 102,
  CF 336, SCE 52개다. 16/16사 모두 CIS/CF/SCE 신호가 발생했다.
- 정상 다양 10사(SK하이닉스, LG화학, 한국단자공업, 아진산업, 강원에너지, 계룡건설산업,
  하림지주, 롯데쇼핑, HMM, 다우기술)는 funnel BS 1,545, IS 150, CIS 483, CF 1,990,
  SCE 270행, universal 신호 BS 101, IS 20, CIS 53, CF 202, SCE 23개다. 10/10사에서
  CIS/CF/SCE 신호가 발생했다. 원인은 정상 영업·투자·재무 현금흐름 세목과 총포괄손익의 큰
  변동이 자산 1% floor를 넘는 경우가 많기 때문이다. S3는 사각 제거 단계이며, CF/CIS/SCE
  신호는 L4 material에서 맥락 판단이 필요하다.
- 표본 내 직접 사례: 세토피아 2019 CF `전환사채의 발행` YoY 1371.55%와 SCE `자본금변동`
  mix shift -31.88pp, 유네코 2018 CIS `총포괄손익` YoY -2169.04%, 셀트리온 2017 CIS
  `지배기업귀속총포괄손익` YoY 136.01% 등이 새 5종 스캔에서 생성된다. 표본 라벨에는
  순수 OCI 은닉으로 확정된 사건이 없어 OCI 신호는 검토 후보로만 기록한다.

## S3 보완 — CF/CIS/SCE 결정론 큐·strict 제외 (2026-06-07)

- universal 5종 신호 생성은 유지하되, `RedFlagSignal`에 선택적 `sj_div`를 붙여
  결정론 큐와 백테스트 scoring에서 statement를 구분한다. `src.signals.universal`의 universal
  신호와 CFS/OFS gap은 실제 `sj_div`를 채운다.
- `src.signals.red_flags`: mvp1 관계 신호는 raw 반복표 `sj_div`가 아니라
  `canonical_accounts.yaml`의 canonical statement를 기준으로 `sj_div`를 채운다. 예를 들어
  SCE에 반복 표시된 `당기순이익`도 canonical statement는 IS이므로 기존 BS/IS 채점에서
  빠지지 않는다.
- `src.report.integrated`: review queue에 들어가는 `RedFlagSignal`은 `sj_div is None` 또는
  `sj_div in {BS, IS}`만 허용한다. `sj_div`가 있는 미매핑 중요계정도 BS/IS만 큐에 넣고,
  원본 `unmapped_material_accounts` material은 5종을 유지한다.
- `src.backtest.score`: `fired_signals`에는 CF/CIS/SCE 신호를 보존하되
  `excluded_from_scoring=True`로 표시해 strict/track 채점에서 제외한다.
- `src.report.company_report`: `latest_signal_snapshot["universal_scan"]`에는 `sj_div`를 포함하고,
  `account_level_series`는 BS·IS·CIS·CF·SCE 5종을 유지한다. 따라서 LLM 관점 material은
  5종 시계열과 단서를 계속 받는다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 104개 통과,
  `.venv\\Scripts\\python.exe -m ruff check .` 통과. 기본 labels 백테스트는 positive 발굴
  5/6 유지, 삼성 clean False, KAI negative control strict=False/track=False(`변동미미`)로
  복귀했다.
- 정상 다양 10사 검증: target 2023 기준 생성 단계에는 CF 108, CIS 15, SCE 10개 비-BS/IS
  신호가 있었지만 deterministic queue 필터 뒤 CF/CIS/SCE 신호 누수는 0건이다. 같은 회사들의
  material에는 `account_level_series` 기준 BS 1,498, IS 89, CIS 464, CF 1,838, SCE 282행과
  universal snapshot 기준 CF 47, CIS 15, SCE 10개가 남아 LLM 관점이 5종을 계속 볼 수 있다.

## S4 미매핑 핵심계정 canonical 보강 (2026-06-07)

- `config/canonical_accounts.yaml`: IFRS16 사용권자산·유동리스부채·비유동리스부채·리스부채,
  투자부동산, 관계기업투자 표준 ID/alias, FVPL/FVOCI/상각후원가 금융자산(유동/비유동 포함),
  순확정급여부채·확정급여부채, 유동성장기차입금을 추가했다. 리스부채는 유동/비유동 구분을
  유지하고, 일반 `리스부채`는 별도 generic canonical로 둔다.
- 관계기업투자는 기존 alias 중복/누락을 정리하고 `ifrs-full_InvestmentsInAssociates`,
  `ifrs-full_InvestmentsInSubsidiaries`를 추가했다. 이트론 raw의 `관계기업에 대한 투자자산`
  (`ifrs-full_InvestmentsInAssociates`)이 `관계기업투자`로 매핑된다.
- 검증: `.venv\\Scripts\\python.exe -m pytest -q` 106개 통과,
  `.venv\\Scripts\\python.exe -m ruff check .` 통과. 기본 labels 백테스트는 positive 발굴
  5/6 유지, 삼성 clean False, KAI negative strict=False/track=False 유지.
- 표본 27사(positive 16 + 정상 다양 10 + 삼성) raw BS 9,536행 재측정 결과:
  미매핑 3,708행, 행 기준 38.88%다. 기존 감사 baseline 48% 대비 9.12%p 하락했다.
  금액 기준 미매핑률은 3.79%다.
- 조 단위 핵심계정 canonical 탈출 확인: 사용권자산 15사 최대 5.16조, 비유동리스부채 18사
  최대 5.62조, 리스부채 5사 최대 5.40조, 투자부동산 19사 최대 2.30조, 유동성장기차입금
  16사 최대 22.26조, FVPL금융자산 8사 최대 29.31조, FVOCI금융자산 5사 최대 16.30조,
  상각후원가금융자산 4사 최대 10.71조, 관계기업투자 26사 최대 59.50조가 canonical로
  매핑된다.
- 16개 positive 회사 관계기업투자는 16/16사에서 매핑된다. 이렘은 2016 CFS 142억,
  2019 CFS 255억/OFS 421억, 2020 CFS 155억 등 `관계기업투자` canonical 행이 확인됐다.
- 과병합/이중계상 안전선: 매출, 매출채권, 매입채무, 자산총계, 계약자산, 당기순이익,
  관계기업투자, 사용권자산, 유동리스부채, 비유동리스부채, 투자부동산의
  `(company, year, fs_div, canonical)` 중복은 0건이다.

## S4 후속: 종속기업투자 canonical 분리 (2026-06-07)

- S4 검증 중 별도재무제표(OFS)에서 종속기업투자와 관계기업투자가 같은 canonical로 합쳐져,
  `_dedupe_canonical_rows`(합산 안 함, 점수·금액 1행만 keep)에서 한 계정이 통째로 버려지는
  데이터 소실을 발견했다(하림지주 OFS: 종속 2.5조 vs 관계 30억 → 관계 소실).
- `ifrs-full_InvestmentsInSubsidiaries`와 종속 단독 alias 6종을 신설 canonical `종속기업투자`로
  분리했다. 종속+관계 통합ID(`...InSubsidiariesJointVenturesAndAssociates`)·통합 alias는 분리
  불가하므로 관계기업투자(대표)에 유지하고 배치 이유를 yaml 인라인 주석으로 남겼다.
- 검증(직접 재현): 하림지주·웰바이오텍·아진산업 OFS에서 종속·관계가 각각 별도 canonical 1행
  → dedupe 소실 0. 미매핑률 38.56%→38.43%(개선). 관계+종속 합쳐 분식 16/16 누락 0. pytest
  107 통과, 백테 positive 5/6·삼성 clean·KAI strict=False 회귀 0.
- 미결(별도 결정): `relationship_chains.yaml` consolidation-structure 체인에 종속기업투자
  포함 여부는 흐름신호 설계 사항으로 보류.

## 다음 할 일 (우선순위)

1. **S5 절대 수준 이상 신호(DIO 등)**: 변동률이 작아도 절대 수준이 비정상적인 재고·운전자본·
   현금흐름 지표를 후보화한다. S4로 핵심 BS 계정 coverage가 넓어졌으므로 수준 신호 입력이
   더 안정적이다.
2. **Stage2 LLM 시연**: 결정론이 발굴한 트랙 A/B 후보를 6관점 L4가 어떻게 설명·교차검증하는지
   확인한다. 특히 세토피아처럼 소액 부정이 숫자 임계로는 변동미미인 사례는 과장하지 않고
   도구 한계로 남긴다.
3. **Stage2 LLM 시연**: 본질적 한계 사례(셀트리온 개발비, 아스트 재고-매출원가 관계)에 6관점 live
   실행해 결정론이 못 한 분별을 LLM이 하는지 확인. (대상 회사 주석 수집 필요)
4. 공시 변동 고도화: D82757 등 주석 전기/당기 텍스트 diff로 우발부채 문구 변화를 수치 변동과 교차.
5. CF 흐름 리포트 보강: 사업결합순현금유출·장기차입금차입·자기주식취득·운전자본변동 원천/사용처 표 분리.

## 열린 이슈 / 주의

- `finstate_all` 응답에는 `fs_div` 컬럼이 없다. 수집 context에서 CFS/OFS를 주입해야 한다.
- `account_id == "-표준계정코드 미사용-"` 행이 존재한다. MVP1/합계 계정에서는 `매입채무`,
  `이자비용`, `당기순이익` 일부 과거 행과 `단기차입금`(2023~2025)이 label alias 보조를
  필요로 했다.
- 전체 raw 행 기준 미매핑 행은 여전히 존재한다. 이제 L4 review queue는 target year CFS의
  금액 큰 미등록 계정을 `unmapped_material_account`로 Low risk 노출하고, 전수 보편 스캔은
  미등록 BS·IS·CIS·CF·SCE account_id도 label/account_id로 신호화한다.
- 연결 특유 이슈는 별도 에이전트가 아니라 CFS/OFS 괴리와 연결 구조 사슬로 흡수한다. 영업권은
  raw에서 단독 계정이 아니라 `ifrs-full_IntangibleAssetsAndGoodwill`에 포함되어 무형자산으로
  다룬다.
- 주석은 표와 텍스트가 섞인 HTML이다. 단순 TXT만으로는 행/열 구조가 손실된다.
- 현재 주석 인덱서는 8개 카테고리 모두 섹션 단위 텍스트로 보존한다. 행/열 정밀 복원은
  아직 하지 않았다.
- 충당부채는 2025 threshold 기준 수치 red flag가 없어 계정 Finding은 생성되지 않았다.
  대신 D82757 섹션은 L4 주석 관점에서 우발부채 공시 검토 후보로 반영된다.
- ROI는 공시 재무제표 기본 합계 계정에 투자원가가 없어 계산하지 않는다.
- 수치 분석가 prompt는 외부 사실을 쓰지 않는다. 정상 설명은 일반적 가능성으로만 작성해야 한다.
- 외부 업황·뉴스 맥락은 L4 `external` 관점으로 교차에 참여한다. 쿼리 생성과 외부 평가는
  `gemini_external_model == "gemini-3.1-pro-preview"`를 사용하고, 내부 분석·판정 관점
  `numeric/note/flow/change/industry`와 종합 문단은 `openai_model == "gpt-5.4"`를 사용한다.
  쿼리 생성은 내부 데이터 기반으로 하되,
  외부 평가는 검색 결과와 출처만 입력받는다. 출처 없는 외부 주장은 버리고 Finding 판단
  필드는 변경하지 않는다. 외부 맥락은 설명용이며 면죄부가 아니다.
- 동종업계 비교는 L4 `industry` 관점으로 교차에 참여한다. 피어는 대상 회사 DART
  `induty_code` 앞 3자리 중분류 config 피어의 재무지표 baseline만 계산하며, 주석·외부·5축
  분석을 피어에 적용하지 않는다. 해당 중분류 피어가 없으면 `industry` 관점만 deferred한다.
- L4 종합 문단은 결정론 큐, 지표 요약, 계정·지표 시계열, 관점별 평가, 교차 결과에 grounding한다.
  live 호출 실패 시 문단만 보류하고 결정론 큐는 유지한다.
- L4 관점 LLM은 독립 입력을 받는다. 수치 관점은 review_queue 참고 후보와 계정·지표 시계열,
  주석 관점은
  `note_mappings.yaml`의 8개 카테고리 note section material, 흐름 관점은
  BS-IS-CF/활동성·이익의 질 material과 계정 시계열, 변동 관점은
  전기 대비 변동 material과 수준·추세 시계열을 받는다. review_queue는 정답이 아니라 참고
  후보이며, 큐 밖 항목도 제공 material에 근거하면 검토 후보로 제기할 수 있다.
  외부 관점은 내부 데이터로 검색어만 생성하고, 평가는
  Google Search grounded ContextBrief만 받는다. 서로의 결론은 입력으로 받지 않는다.
- 감사기준·K-IFRS 근거는 검토 관점의 출처다. Finding은 부정·분식 확정 표현으로 쓰지 않는다.
- 실무 재무지표도 검토 관점이다. 출처 없는 계산식은 플레이북에 넣지 않고, 계정 부족 지표는
  `mvp1_status: account_missing`으로 표시한다. 현재 ROI만 계정 부족으로 남아 있다.
- 공개 KSA 원문별 링크는 확인하지 못한 항목이 있어 [AUDIT_BASIS.md](AUDIT_BASIS.md)에
  “KSA 원문 미검증”으로 표시했다. ISA/IFRS 제목과 요지는 공식 IAASB/IFRS 출처로 확인했다.
- L3 Gemini 모델 기본값은 `config.settings.gemini_model == "gemini-2.5-flash"`다.
  L4 내부 분석 모델은 `config.settings.openai_model == "gpt-5.4"`이고, 외부 관점 query/eval
  모델은 `config.settings.gemini_external_model == "gemini-3.1-pro-preview"`다.
  Gemini fallback은 `gemini_fallback_model` 설정이 비어 있으면 비활성이다.
- 2025 CFS는 IS·CF 계정 확장 후 Medium 관계 red flag가 여럿 있다. 대표 신호는
  사업결합순현금유출 YoY 2102.89%, 장기차입금차입 YoY 593.17%, 자기주식취득 YoY 552.00%,
  운전자본변동 YoY -513.31%, 재무활동CF vs 장기차입금 괴리 -137.49pp다.

## 진입 포인트

- 전체 흐름 → [OVERVIEW.md](OVERVIEW.md) → 상세 [PLAN.md](PLAN.md)
- Codex 작업 지침 → [../../AGENTS.md](../../AGENTS.md) → [CODEX.md](CODEX.md)
- 할 일 → [ROADMAP.md](ROADMAP.md) · 결정·이유 → [DECISION.md](DECISION.md)
- L1 측정 → [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md)
- L2 계산 → [SIGNAL_REPORT.md](SIGNAL_REPORT.md)
- 첫 Finding → [FINDING_REPORT.md](FINDING_REPORT.md)
- 문제 기록(사람용) → [../user/TROUBLESHOOT.md](../user/TROUBLESHOOT.md)
