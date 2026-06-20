# 작업: P1 라운드8 수정 — SCE 부모소계 leaf 이중계상 판별(N2-f) + 차감 판정 id 기반 보강

> 라운드8(층화 5사·18 회사연도, seed=8, `_round_targets_round8.json`) 감사 발견 수정.
> 신규 1종 + 기존 변형 1건·소실 0·전기소실 0. 증거 duckdb·raw 재현 검증(매트릭스
> `_VERDICT_MATRIX_round8.md` 게이트 PASS). 선행: [_P1_ROUND7_FIX_PROMPT.md](_P1_ROUND7_FIX_PROMPT.md)(N2-d·N2-e 완료).

## 1. 목표

- SCE 변동행의 taxonomy 부모-자식 이중계상(N2-f)을 구조 판별로 제거하고, 배당 차감 판정을
  canonical 문자열 열거에서 account_id 기반으로 보강한다.
- 성공 기준: §6 검증 명령 6개 전부 기대 출력 일치.

## 2. 컨텍스트

- 읽어야 할 파일 (수정 전 반드시):
  - `src/normalize/sce.py` (`_retag_stock_vectors`(N1-c 벡터동일성)·role 부여·검산 경로)
  - `config/canonical_accounts.yaml` `sce_deduction_changes`(10994행 부근)·`sce_change_roles`
  - `tests/test_normalize.py`
- 배경 (모르면 잘못 판단할 사실):
  - **N2-f 증거(00123772 금융, 2023~2025 검산 FAIL 13,036/-5,055/26,742 — 3개년 단일 근원)**:
    raw SCE에 ①`dart_…ChangeInFairValue` 평가손익 13,036 ②`dart_…Disposal` 처분손익 0
    ③`ifrs-full_OtherComprehensiveIncome…FinancialAssets…` **관련손익 13,036**(① + ② 합,
    2025는 label '…관련손익 합계') — 셋 다 change_role=leaf로 합산돼 평가손익이 2번 계상
    (DB 재현됨). FAIL 값이 매년 FVOCI 평가손익과 정확히 일치, 부모 제외 시 3개년 ±1백만 내
    정합. 기존 벡터동일성 retag는 **기초/재작성 stock과의 동일성만** 검사해 변동행끼리의
    부모=자식합 관계는 사각.
  - **N2-e 변형(00131054/2023 FAIL 11,021 = 2×5,510.3)**: raw 현금배당금
    +5,510,348,700(`dart_AnnualDividendsPaid` 추정 — 확인할 것) → canonical `배당금의 지급`
    이 차감 목록에 없어 -abs 미적용. 배당 변형 누락이 **3번째**(배당금지급→N3,
    비지배배당→N2-e, 이번 배당금의 지급) — 문자열 열거는 두더지잡기이므로 id 기반이 근본책.
    같은 회사 2024(연차배당→배당변동)는 정상 차감된 대조군.

## 3. 설계 (이대로 구현 — 임의 변경 금지)

- **N2-f**: 변동행(leaf) 그룹에 **부모-자식 구조 판별** 추가 — 다음 둘 다 만족하면 해당 행을
  subtotal로 재태깅(검산 Σleaf 제외):
  ①그 행의 컬럼 벡터(전 component, 당기·전기)가 같은 표 내 **다른 leaf 변동행들의 부분집합
  벡터 합과 round 후 전 셀 일치** ②(보조 신호 — 일치 후보가 복수일 때 우선순위)
  account_id가 ifrs-full(표준 부모)이고 합산 대상이 dart_ 자식이거나, label이 '관련손익·합계'
  류. 1차 근거는 ①의 수치 정합 — 라벨·id 패턴을 src/ 하드코딩 조건의 단독 근거로 쓰지 말 것
  (보조 마커 목록이 필요하면 config로).
  주의: 우연한 벡터합 일치(전 셀·전기까지 동일)는 사실상 불가능하지만, **자식 2개 이상 또는
  (자식 1개 + 0값 자식)일 때만** 발동해 단순 동액 중복행과 구분.
- **차감 id 기반 보강**: config에 `sce_deduction_ids`(account_id 목록 — `dart_AnnualDividendsPaid`,
  `ifrs-full_DividendsPaid` 계열 등 배당·상환 표준 id) 신설, 차감 판정을 canonical 목록 **또는**
  id 목록 매칭으로 확장. 기존 `sce_deduction_changes`는 유지(canonical 경로 무회귀).
  `배당금의 지급`도 canonical 목록에 추가(이중 안전망).
- 설계와 현장이 안 맞으면 **STATUS: NEEDS_CONTEXT**. 멈춤은 실패가 아니다.

## 4. 단계 체크리스트 (순서 고정 — 건너뛰기·합치기 금지)

- [ ] Step 1: RED — ①부모=자식합 벡터 합성 케이스(부모 subtotal 재태깅 기대, 현재 실패)
      ②진짜 독립 변동행(벡터합 불일치)은 leaf 유지 가드 ③id 기반 차감(-abs) 테스트
      ④동액 단순 중복행은 부모 판별 미발동 가드.
      증거: `uv run python -m pytest tests/ -q -k "n2f or dedid"` 출력 원문(failed 포함)
- [ ] Step 2: N2-f 구현 → 해당 GREEN. 증거: 같은 명령 출력
- [ ] Step 3: 차감 id 기반 구현 → 전부 GREEN. 증거: failed 0 원문
- [ ] Step 4: 재정규화 — round8 5사 + round1~7 30사 + known 6사 `--force`.
      증거: renormalize_all 마지막 줄(error=0)
- [ ] Step 5(마지막): §6 전체 검증 후 출력 원문 확보.
※ 단계 증거 원문 필수. 증거 없는 단계 = 미수행.

## 5. 금지 사항 (1건이라도 위반 시 작업 전체 실패)

- 하드코딩: corp_code(00123772·00131054)·금액(13,036 등)을 src/ 조건에 기입 금지. id·마커
  목록은 config 데이터로만.
- 테스트 약화 금지. 라운드1~7 테스트(특히 N1-c 벡터동일성·N2-d bare 한정·N1-g 도출) 무수정
  통과 필수 — N2-f 판별이 N1-g 도출 행을 오인 재태깅하지 않는지 가드.
- 범위 밖 수정 금지 — 수정 가능: `src/normalize/sce.py`, `src/normalize/config.py`,
  `config/canonical_accounts.yaml`, `tests/`. **건드리면 실패**: 하니스, signals/backtest,
  정답지·표본 json.
- 체크리스트 생략·순서 변경 금지. 실패·미완을 완료로 보고 금지.

## 6. 최종 검증 (완료 선언 전 필수 — 하나라도 다르면 DONE 금지)

- round8 배치 → 기대: 00123772 3개년·00131054/2023 SCE검산 **OK**, 소실 0·전기소실 0.
  00440712 2022(-26,783)/2023(190)은 원공시 오류로 잔존 허용(사유 보고 명시)
- known + round1~7 배치 → 기대: 기존과 동일(차감·검산 무회귀 — 배당 보유사 전체 포함)
- 백테스트 → 기대: recall 5/6 유지
- `uv run python -m pytest tests/ -q` → 기대: 전체 passed(178+신규, failed 0)
- (직접 증거) 00123772/2023 duckdb: ifrs-full FVOCI 관련손익 행 change_role ≠ leaf
- (직접 증거) 00131054/2023 duckdb: 배당금의 지급 bare = **-5,510,348,700**

## 7. 완료 보고 양식 (이 양식 그대로, 항목 생략 금지)

```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: Step 1~5 [x]/[ ] + 각 단계 증거(명령 + 출력 원문)
변경 파일: <실제 변경한 파일만>
최종 검증 결과: §6 명령 6개 각각의 출력 원문
미완·우회·우려 사항: <정직하게 전부. 없으면 "없음">
```

---

## 부록: 기록 (이번 작업 대상 아님 — 삭제 금지)

- 00440712/2022(-26,783): raw 결손보전 행의 공시자 부호 오류(양변 동부호) — 원공시 결함,
  파이프라인이 충실 전파(정직 노출). 00440712/2023(190): raw SCE 자기모순(total≠컬럼합·ord
  결번) — 원천 행 누락 의심.
- 00310156 CF '이자의 지급'→이자비용조정 id_label_conflict 1건(합산 무영향) — N5 자료 누적.
- 금융 2사 2020~22 dart_no_data 자동 표기 정상.
