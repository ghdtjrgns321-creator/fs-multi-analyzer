# HANDOFF — 신호엔진 다축 프로파일러 재설계 (일시중단·이관)

> 이 문서 하나 + [PHASE1_SIGNAL_REDESIGN.md](PHASE1_SIGNAL_REDESIGN.md)만 읽으면 이어서 진행할 수
> 있도록 작성. 2026-06-21 작성. **현재 상태: S1~S3 구현 완료, fitting 점검에서 갭 3개 발견,
> 사용자가 "스코프 과대"로 판단해 일시중단. 재개 전 §9(규모 재평가)를 먼저 읽을 것.**

## ① 배경 — 왜 시작됐나

전과정 파이프라인 측정 #1(대주산업 00112457/2024, `data/backtest/_E2E_MEASURE_*.md`)에서
독립 회계분석 vs 프로젝트 산출물 대조(`_E2E_EVAL_00112457_2024.md`) 결과, **Phase1 신호엔진이
2개 계정을 놓침**:
- **유형자산취득(capex)**: 144→94→1,027→2,849백만(YoY +177%) — 급증인데 신호 미강조.
- **관계기업투자**: 5,204→4,772→4,281백만(3년 단조감소) — 완만추세인데 신호 미강조.

둘 다 Phase2 관점(numeric·change) 입력(account_level_series)에는 있었으나, **신호엔진이
review_queue로 강조 안 해 6관점 LLM 전부 미선택**(LLM은 525행에서 YoY를 스스로 계산 안 함).

## ② 문제 진단 — 룰 열거 패러다임

신호 생성이 전부 "config 룰 + 임계 리터럴"(red_flags=관계사슬, universal=전계정 YoY/mix/z,
ratios=비율). **사람이 "무엇이 이상인지" 룰로 열거하는 한 열거 안 한 이상은 영원히 사각.**
- capex: YoY +177%인데 `_valid_yoy_base`(전기 1,027 < floor 1,113)가 차단 = floor 경계 절벽.
- 관계기업: YoY -10% < 50% 임계 미달 + "다년 추세"를 볼 축 자체가 없음.

핵심: 변화 탐지는 §3("계산은 코드, 발견은 LLM") 철학상 코드 책임인데, 룰 집합이 좁다.

## ③ 해결 방향 — 다축 이상 프로파일러

전 계정에 self(자기 시계열)+peer(동종 분포) 기준 5축 이상점수를 전수 계산 → 분포 꼬리를 후보.
임계 리터럴/floor 이진컷 폐기. 룰 추가(땜빵) 대신 축 기반이라 새 패턴도 분포가 잡음.
- 5축: ①수준(peer) ②변화금액(=A) ③추세(=B) ④변동성 ⑤구성비. capex=②③, 관계기업=③.

## ④ 확정 결정 (grill)

- 기준선: **self + peer 둘 다**
- D1 통합: **OR플래그(어느 축이든 분위≥tail이면 후보) + 가중합 strength 정렬**
- D2 기존신호: **하이브리드** — universal yoy/mix/z만 다축 흡수·폐기, 관계사슬·비율·정정 유지
- D3 임계: **분포 상위 분위(개수상한 없음)** + 절대 노이즈 가드. tail 기본 0.8

## ⑤ 완료물 (S1~S3)

`src/signals/profiler.py` (순수함수, LLM·DB 없음):
- **S1**: `delta_score`(|당기-전기|/자산)·`trend_score`(단조성×|당기-최초|/자산)·`volatility_score`(CV)·
  `mix_score`(비중변화) + `account_series_map`·`statement_totals`·`compute_self_axes`.
- **S2**: `normalize_axes`(축별 mid-rank 분위 [0,1])·`compute_strength`(OR플래그+가중합+tail_axes+정렬).
- **S3**: `build_account_profile(report)`(subtotal 제외·자산총계 자동추출 → self 프로파일).
- 테스트 `tests/test_signal_profiler.py` **20개 GREEN**. 전체 **347 passed·1 xfailed**(회귀 0).
- peer 수준축(①)은 미구현(S4 benchmark 연동 예정).

## ⑥ 회귀 baseline (재설계 후 악화 0 필수)

`data/backtest/_REDESIGN_BASELINE.txt`:
- 백테스트 분식 발굴 **recall 5/6**(세토피아만 미발굴=기존). 삼성(clean) FP 14. KAI 미발굴.
- 핵심분식 강도: 두산 미청구공사 3.21·아스트 재고 10.0·모델 당기순이익 10.0·셀트리온 무형 2.34 등.
- 재현: `PYTHONPATH=. uv run python -m src.backtest.run_backtest` → `BACKTEST_REPORT.md`.

## ⑦ fitting 점검 발견 (`data/backtest/_e2e_fitting_check.py`)

분식 6사+정상 2사에 build_account_profile 적용. **fitting 아님 확증**(코드에 corp/계정 리터럴 0,
분식계정도 일반 포착 4/6사, flagged% 25~50% 안정). **그러나 더 중요한 3 갭**:
- **G1 OR플래그 구멍**: strength 높은데(두산 충당부채 0.63·디아이 수익 0.56) 단일 축이 tail 미달이면
  flagged 안 됨. → D1 보강: **OR(단일축 tail) ∪ (strength 상위 분위)** 병행.
- **G2 분식 미포착**: 디아이동일 0/4·세토피아 0/2(둘 다 기존도 변동미미). peer축·G1로 회복 시도, S6 확인.
- **G3 분식계정 미존재**: 미청구공사·자기자본·개발비가 account_level_series에 아예 없음(정규화 매핑/
  series 필터 별개 이슈, 다축 무력). S6서 recall 영향 측정.
- 실데이터(대주): capex flagged(순위15·delta+vol) ✅ / 관계기업 미달(순위39·trend_q 0.72, 금액 작아 깎임).

## ⑧ 남은 단계

- **S4**: ①peer 수준축(benchmark 연동) + D1 G1보강(strength 병행) + review_queue 통합·universal 흡수(관계사슬 유지)
- **S5**: materials(numeric/flow/change) LLM 입력에 다축 프로파일 표 주입
- **S6**: 백테스트 회귀 — recall 5/6 유지 + capex/관계기업 회복 + G2/G3 영향 측정

## ⑨ ★재개 전 규모 재평가 (필독)

이 재설계는 **경미한 누락 2개**(capex 자산 2.6%·관계기업 0.8%, **둘 다 분식 아님**)를 위해 **검증된
신호엔진(recall 5/6)을 통째 교체**하는 큰 작업이다. fitting 점검에서 갈수록 새 갭(mix·OR구멍·분식
미포착)이 나와 복잡도·회귀위험이 누적됐다. 사용자가 "스코프 과대"로 일시중단했다. **재개 시 먼저 판단**:
- **대안 A(권장 검토)**: D2를 "완전대체/하이브리드"가 아니라 **병행 추가**로 — 기존 신호 불변(회귀 0),
  다축은 "참고 후보"로만 review_queue에 추가. capex/관계기업만 surface, 5/6 보존. 작고 안전.
- **대안 B**: capex만 floor 경계 최소수정(재설계 접음). 관계기업은 경미라 보류.
- **대안 C(현 경로)**: 전체 재설계 S4~S6 + 보강 여러 라운드. 별도 프로젝트 규모로 각오.

## 관련 파일

- 설계: `docs/agent/PHASE1_SIGNAL_REDESIGN.md`(§11b·§11c에 발견 누적)
- 구현: `src/signals/profiler.py` · 테스트 `tests/test_signal_profiler.py`
- 측정/평가: `data/backtest/_e2e_measure.py`·`_E2E_MEASURE_00112457_2024.md`·`_e2e_eval.py`·`_E2E_EVAL_00112457_2024.md`
- 진단/점검: `data/backtest/_e2e_signal_probe.py`(누락 근본원인)·`_e2e_profile_probe.py`(실데이터)·`_e2e_fitting_check.py`(fitting)
- 회귀: `data/backtest/_REDESIGN_BASELINE.txt` · `src/backtest/run_backtest.py`
