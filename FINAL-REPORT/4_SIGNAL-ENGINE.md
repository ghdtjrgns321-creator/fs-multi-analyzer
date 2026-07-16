# 4. L2 신호엔진 (결정론)

> **위치**: L1 정규화 → `[L2 신호엔진]` → L3 5관점. 이 프로젝트의 성패가 여기 달려 있으므로 두껍게 잡는다. **LLM 이전 단계, 코드/SQL만 사용한다.** 목표는 단순 이상치 탐지를 넘어 "감사적" 신호를 생성하는 것이다(PLAN §6).

## 4.1 내부 흐름

```
정규화 frame (5종 전 계정: BS·IS·CIS·CF·SCE, CFS+OFS)
   │
   ├─ series_normalize  재표시 전기값 권위로 부호 정규화·재표시 후보 표면화
   │
   ├─ universal.scan_*  관계사슬 밖 전 계정 YoY·mix·z·CFS↔OFS gap (임계 초과 → RedFlagSignal)
   ├─ profiler          self 4축(delta·trend·volatility·mix) → 분위 정규화 → OR 플래그
   ├─ metrics_panel     전 계정 계산값 전량 부착 + occurrence_state (선택·랭킹 없음)
   ├─ ratios            15개 재무비율 (계정 결측이면 not_computed)
   ├─ decomposition     4개 브리지로 소계 변동을 구성 기여로 분해 (잔차 정직 표시)
   ├─ mvp1 + red_flags  관계사슬 계산 + config 임계 적용
   │
   └─ coverage.build_coverage_ledger  모집단 = 분석 + 제외 + 미설명 (음의공간 대조)
```

두 계열이 공존한다. **(구)** 임계 초과 `RedFlagSignal`(백테스트 채점용)과 **(신)** 임계·선택 없이 전 계정 계산값을 전량 부착하는 `metrics_panel`/`profiler`. 후자에서 percentile은 서술통계일 뿐 판단이 아니다 — 무엇이 이상한지는 관점 LLM의 몫이다.

## 4.2 구조

| 구성요소                | 개수·값                                                   | 출처                                        |
| ----------------------- | --------------------------------------------------------- | ------------------------------------------- |
| 신호엔진 모듈           | 11                                                        | `src/signals/`                              |
| 다축 프로파일러 축      | 4 (delta·trend·volatility·mix)                            | `profiler.py:138`                           |
| 분포 꼬리 임계          | tail = **0.8**                                            | `profiler.py:139`                           |
| 관계 사슬               | 9                                                         | `config/playbooks/relationship_chains.yaml` |
| 재무비율                | 15 (4카테고리)                                            | `config/playbooks/financial_ratios.yaml`    |
| 변동분해 브리지         | 4 (GP·OP·세전·순이익)                                     | `config/decomposition.yaml`                 |
| 스캔 임계 (전부 config) | yoy 50·mix_shift 5·z 2·cfs_ofs_gap 30%·floor 1억·z cap 10 | `relationship_chains.yaml` l2_mvp1          |

## 4.3 다축 프로파일러 — 룰 열거에서 분포 꼬리로

과거 신호엔진은 "룰 열거 패러다임"이었다 — 사람이 변화율 룰과 임계 리터럴을 열거하니, 열거하지 않은 이상은 영원히 사각이었다. 대주산업 E2E에서 capex +177%·관계기업 추세감소를 신호엔진이 강조 못해 당시 6개 관점 전부 놓친 것이 계기였다(HANDOFF_SIGNAL_REDESIGN).

`profiler.py`는 전 계정에 **self 기준선 4축** 원점수를 계산한다(`profiler.py:17-58`):

| 축                     | 계산                                                       | 무엇을 잡나                                |
| ---------------------- | ---------------------------------------------------------- | ------------------------------------------ |
| **delta**(변화금액)    | `\|당기−전기\| / 자산총계`                                 | 전기 크기에 의존 안 함(소액기저 폭발 없음) |
| **trend**(추세)        | `단조성 × \|당기−최초\|/자산` (단조성=max(pos,neg)/차분수) | 다년 단조 드리프트                         |
| **volatility**(변동성) | `표준편차/\|평균\|` (변동계수)                             | 출렁임                                     |
| **mix**(구성비)        | 표 내 비중(0~1)의 전기 대비 절대변화                       | 포트폴리오 이동                            |

분모 격리가 핵심이다 — `statement_totals`를 `(fs_div, sj_div, year)` 키로 두어 연결(CFS)·별도(OFS)의 같은 sj_div가 한 분모로 섞이지 않게 한다. 정규화는 임계 리터럴 없이 **mid-rank 분위[0,1]**(`_midrank_quantiles`)로, 분포가 위치를 정한다. 통합강도(`compute_strength`)는 **OR 플래그**(어느 축이든 분위≥tail 0.8이면 flagged) + 가중합 strength다.

이 4축이 capex/관계기업을 잡으려 발명한 것이 아니라 감사기준서 도출임이 1:1로 증명됐다(PHASE1_AXIS_AUDIT_MAPPING): delta→ISA320, trend→ISA520+710, volatility→520+240, mix→520. fitting 방지 가드 4개(임계는 분포 분위·독립 회귀 recall 5/6·상위 강제 금지·도메인 선행 증명)로 과적합을 막는다.

## 4.4 전수 패널 — 코드는 순위를 매기지 않는다

`metrics_panel.account_metrics_panel`은 전 계정에 결정론 계산값을 **하나도 고르지 않고 전부** 부착한다. `DECISION_FIELDS=(flagged, strength, tail_axes, rank)`는 패널에 있으면 안 되는 필드다 — 코드가 중요도/선택을 정하면 "발견은 LLM" 원칙 위반이기 때문에 가드로 막는다.

**occurrence_state**(신규/소멸 신호)가 5원칙 중 "변화" 축의 실현이다(`metrics_panel.py:32-49`):

| 상태         | 조건                                           |
| ------------ | ---------------------------------------------- |
| present      | 당기·전기 모두 잔액 존재(정상 변화 대상)       |
| **appeared** | 당기 존재, 윈도우 내 과거 전무(올해 신규 발생) |
| resumed      | 당기 존재, 직전기 없음, 더 과거엔 존재(재개)   |
| disappeared  | 당기 없음, 과거 존재(소멸)                     |

이는 delta_score와 별개 신호다 — 변화율 0/None이 죽이던 신규·소멸을 별도 칸으로 표시한다. SCE로도 확장돼(`sce_occurrence_states`) 자기주식취득이 올해만 나타나면 appeared로 판정한다. `disclosed_label`(공시 원문 계정명)을 계정명 권위로 실어, 정준명 오라벨이 서사를 관통하는 것을 차단한다(설계3).

## 4.5 전수 스캔과 관계 사슬

`universal.scan_universal_signals`는 관계사슬 밖 전 계정을 단일 일관 statement 기준(`preferred_fs_div`, 혼용 금지)으로 스캔한다. `UNIVERSAL_STATEMENTS=(BS,IS,CIS,CF)` — SCE(2D 격자표)는 평면 스캔에서 제외해 합계·member 셀 오비교로 인한 거짓 신호를 막는다. `_valid_yoy_base`(abs(prior)≥floor & 동부호)로 소액기저·부호반전을 걸러내고, z-score는 [−10,10]로 클립한다. **채점/quota를 제거**해 materiality순 전량 반환한다(top-N 없음). unmapped 계정도 YoY 스캔해 "기타 중요 계정"으로 표면화한다.

관계 사슬 9개(`relationship_chains.yaml`)는 pairwise를 넘어 "사슬 추적"으로 정합성을 본다:
```
매출 → 매출채권 → 대손충당금 → 영업CF          (수익의 질·회수가능성)
재고 → 매출원가 → 재고평가손실                  (재고 진부화·원가)
차입금 → 이자비용 → 재무활동CF → 만기 주석      (유동성·계속기업)
당기순이익 → 영업CF → 운전자본 변동             (이익의 질)
… (총 9개)
```

sanity 게이트(`sanity.py`)가 스캔 전 데이터를 검문한다 — `exclude_foreign_currency_years`(두산밥캣 KRW→USD 1,300배 점프 차단)와 `exclude_asset_sanity_years`(자산총계 100배 점프 제외).

## 4.6 변동분해 — 카드의 "왜"를 코드가 계산

카드가 "영업이익 −62.8% 급감"까지 찾아도 **왜**(매출·원가·판관비 중 무엇의 기여)가 없으면 사람이 검증할 수 없다. 분해는 계산이므로 코드가 한다(원칙 §3.1).

`decomposition.yaml`은 K-IFRS 표준 소계 브리지 **4개**만 둔다(계정 트리 전수 정의 아님) — 유한·닫힌 집합이다. 2026-07 코퍼스 전수 실측(4,782 corp-year): GP 잔차≤1% **99.98%**, OP 표준형 **92.1%**, 세전 변형선택 **63.3%**, 순이익 **85.7%**. 회사별로 변형 중 **|잔차| 최소를 데이터로 선택**한다(손 정의 없음). `decompose_change`는 `sum(row.delta) + residual == delta` 항등을 보장하고, 구성 합이 부모 변동과 다르면 "미설명 잔차 X원(Y%)" 행으로 정직하게 노출한다. 구성 라벨에 자기 브리지가 있으면 재귀로 하위 분해를 첨부한다(GP→매출/원가 다단, 순환 가드).

## 4.7 커버리지 원장 — 조용한 드롭을 구조적으로 차단

이 도구의 무결성 철학을 상징하는 것이 커버리지 원장(`coverage.py`)이다. 분석 명단을 "기본 슬라이스(올해·연결·본문)에서 골라 담기(positive selection)"하면 슬라이스 밖은 조용히 드롭된다. 원장은 이를 **구조적 불변식**으로 전환한다:

```
population_n == analyzed_n + len(excluded) + len(unaccounted)   → reconciled
```

모집단은 frame 본문 셀(CFS/OFS, 윈도우 연도, 잔액>0) 전량이다. 미설명(unaccounted)이 1건이라도 있으면 "⚠ 미분석 N건"으로 표면화한다. 이 원장은 실제로 작동을 입증했다 — 1차 실행에서 대주 미설명 24건(NaN placeholder 거짓 드롭)을 자동 포착해 `_real_amount` 필터를 수정하게 했다. 파생층(비율)까지 확장돼(`build_fs_div_coverage`) fs_div-고정 누락을 전수 포착하는 영구 가드다.

## 4.8 실증 예시 — 삼성전자 2025 자기주식취득이 "신규 발생"으로 표면화

과거 파이프라인은 계정층에만 occurrence_state가 있고 SCE에는 없어, 자기주식 신규 취득(1.8조)이 raw로만 흐르고 변화 축에서 사라졌다(delta_score의 prior=None → 0 = 변화 축 사망). 이것이 삼성 E2E 3대 사각 중 하나였다(HANDOFF_ROOT_REDESIGN).

`metrics_panel.sce_occurrence_states`는 `(fs_div, change_canonical)` 층위(D18 정체성 — leaf 불안정 회피)로 구성요소 abs 금액을 연도 합산해 occurrence를 판정한다. 삼성 자기주식취득은 분석 창 내에서 처음 나타나므로 **appeared**로 판정되고, 소멸(disappeared) 변동종류는 synthetic 셀로 표면화된다(silent drop 금지). 이제 trend 관점이 이 신규 자본거래를 우선 검토하도록 프롬프트(sce_role)가 유도한다. 실측에서 삼성 자기주식취득 appeared가 확인됐다(STATE). "숫자가 0/None이라 죽던 신규·소멸을 별도 신호로 살린다" — 5원칙 중 ⑤(수준+변화)의 구체적 실현이다.
