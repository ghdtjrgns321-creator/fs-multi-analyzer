# 작업: P1 라운드9 수정 — '당기' 접두 정규화 + CFS/OFS 교차 id 모순 플래그 + 하니스 원공시 모순 검사

> 라운드9(층화 5사·23 회사연도, seed=9, `_round_targets_round9.json`) 감사 결과 **신규 결함 0**
> (추이 5→5→2→1→2→3→2→1→0). 잔존은 기존 R1 라벨 변형 1종 + 검출 공백 1건 + 하니스 기계화
> 1건 — 전부 경미. 증거 duckdb·raw 재현 검증(매트릭스 `_VERDICT_MATRIX_round9.md` 게이트 PASS).
> 선행: [_P1_ROUND8_FIX_PROMPT.md](_P1_ROUND8_FIX_PROMPT.md)(N2-f·차감 id 기반 완료).

## 1. 목표

- R1 라벨 변형('당기' 접두) 일반화, CFS/OFS 교차 id 모순 검출, SCE 원공시 모순의 하니스
  기계화 — 3건의 경미 보강.
- 성공 기준: §6 검증 명령 5개 전부 기대 출력 일치.

## 2. 컨텍스트

- 읽어야 할 파일: `src/normalize/config.py`(`normalize_label`·alias 매칭),
  `src/normalize/mapper.py`(id_label_conflict 경로), `config/canonical_accounts.yaml`,
  `data/backtest/_p1_company_review.py` §F 부근, `tests/test_normalize.py`.
- 배경 (모르면 잘못 판단할 사실):
  - **T1(R1 변형) 증거(00927558 2021~2024)**: bare 변동행 `당기총포괄손익`(blank id)이
    총포괄손익 aliases(`[총포괄손익, 포괄손익, 총포괄이익]`) 밖 → unmapped leaf로 NI+OCI와
    이중계상(2021 -27,745 = NI -28,025 + 지분법 280 재현). 같은 회사 2020은 label이
    '총포괄손익'이라 정상 — '당기' 접두만의 차이.
  - **T2(검출 공백) 증거(00148504/2025)**: CFS의 label '발행사채의 증가'에
    `ifrs-full_ProceedsFromIssuingShares`(주식발행) id 오태깅 — **같은 회사연도 OFS의 동일
    label은 사채 id로 정상**. P1이 id를 믿어 1.375조를 주식발행으로 분류, exact 무경고 통과.
    label의 alias 사전 기반 conflict 검출이 비표준 label이라 미발화한 사각(N5 계열).
  - **T3(하니스) 증거**: 00428729 2020/2021(잔액성 값이 변동행 bare에 오입력 — 구성요소 합은
    내부이전 0)·00927558/2024 확정급여(bare +687 vs 구성요소 -687) — **원공시 자기모순**을
    하니스가 검산 FAIL로만 노출(원인 미구분). bare vs 구성요소합 불일치 검사를 기계화하면
    원공시 모순을 원천 단계에서 격리 표기 가능.

## 3. 설계 (이대로 구현 — 임의 변경 금지)

- **T1**: `normalize_label`에 SCE 변동행 매칭 한정으로 '당기' 접두 제거 정규화 추가
  (일반 본문 매칭에 영향 주지 않도록 SCE alias 매칭 경로에서만 적용 — 본문 '당기순이익' 등을
  깨면 안 된다). 보수안으로 막히면 `당기총포괄손익`을 alias에 등록(config)하고 접두 규칙은
  NEEDS_CONTEXT 보고.
- **T2**: 정규화 시 같은 (corp, year)에서 **동일 label이 CFS/OFS 간 다른 account_id**로
  태깅되면 양쪽 행에 `mapping_status='id_label_conflict'` 플래그(매핑은 기존 규칙 유지 —
  N5 1단계 정책과 동일: 플래그만, 변경 금지).
- **T3 (하니스)**: `_p1_company_review.py` §F 직전(또는 별도 §F-1)에 — bare(component '-')
  값과 구성요소 컬럼 합이 round 후 불일치하는 SCE 변동행을 `원공시모순=N`으로 카운트해
  [기계요약]에 추가(+`_p1_review_all.py` 파서·표 동기화). 검산 FAIL의 원인 구분 신호.
- 설계와 현장이 안 맞으면 **STATUS: NEEDS_CONTEXT**.

## 4. 단계 체크리스트 (순서 고정)

- [ ] Step 1: RED — ①'당기총포괄손익' subtotal 매칭 테스트 ②본문 '당기순이익' 무영향 가드
      ③CFS/OFS 교차 id 모순 플래그 테스트 ④하니스 원공시모순 카운트 테스트(있으면).
      증거: `uv run python -m pytest tests/ -q -k "r1v or crossfs or rawconflict"` 출력 원문
- [ ] Step 2: T1·T2 구현 → GREEN. 증거: failed 0 원문
- [ ] Step 3: T3 하니스 구현. 증거: 00428729/2020 단일 하니스 출력에 `원공시모순` 필드 >0
- [ ] Step 4: 재정규화 — round9 5사 + round1~8 35사 + known 6사 `--force`. 증거: error=0
- [ ] Step 5(마지막): §6 전체 검증.
※ 단계 증거 원문 필수.

## 5. 금지 사항

- 하드코딩: corp_code·금액을 src/ 조건에 기입 금지. '당기' 접두 규칙이 어려우면 alias는
  config 등록으로(코드에 라벨 문자열 금지).
- 테스트 약화 금지. 라운드1~8 테스트 무수정 통과.
- 수정 가능: `src/normalize/{config,mapper,sce,pipeline}.py`, `config/canonical_accounts.yaml`,
  `tests/`, `data/backtest/_p1_company_review.py`·`_p1_review_all.py`(T3 한정).
  **건드리면 실패**: `_p1_verdict_gate.py`, signals/backtest, 정답지·표본 json.
- 체크리스트 생략 금지. 실패·미완을 완료로 보고 금지.

## 6. 최종 검증

- round9 배치 → 기대: 00927558 2021~2023 검산 **OK**, 2024는 잔여 687×2 축소 또는 원공시모순
  표기 동반, 00428729 2020/2021은 원공시모순>0 표기(검산 FAIL 잔존 허용 — 원천 결함)
- known + round1~8 배치 → 기대: 무회귀(본문 '당기~' 매핑 분포 변화 0 포함 — 재정규화 전후
  canonical 분포 diff로 증명)
- 백테스트 → recall 5/6 유지
- `uv run python -m pytest tests/ -q` → 전체 passed
- (직접 증거) 00927558/2021 duckdb: 당기총포괄손익 change_role='subtotal'

## 7. 완료 보고 양식

```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: Step 1~5 [x]/[ ] + 각 단계 증거 원문
변경 파일 / 최종 검증 결과(§6 원문) / 미완·우회·우려 사항
```

---

## 부록: 기록 (대상 아님 — 삭제 금지)

- 00428729 2020/2021·00927558 2024 확정급여: 원공시 모순(bare≠구성요소합) — T3 표기 후에도
  검산 FAIL 잔존은 정직 노출이 맞음.
- 00241209/2025 주석 no_report 정합(absence 기록 일치). 00428729/2025 병합 2그룹은 분리 보존
  확인(무해). 금융 2사 2020~22 dart_no_data.
- **배증 결정 입력: 라운드9 신규 0** — 라운드10은 10사(배증 규칙 발동).
