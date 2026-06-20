# 작업: P1 라운드5 수정 — SCE 스톡 행 leaf 혼입 판별 보강 (N1-d 잔액형 소계 · N1-e 정규화 누락)

> 라운드5(층화 5사·19 회사연도, seed=5, `_round_targets_round5.json`) 감사 발견 수정.
> 신규 2종(같은 계열: 스톡 행의 leaf 혼입)·값 소실 0. 증거 duckdb·raw 재현 검증
> (매트릭스 `_VERDICT_MATRIX_round5.md` 게이트 PASS). 선행: [_P1_ROUND4_FIX_PROMPT.md](_P1_ROUND4_FIX_PROMPT.md)(N1-c 완료).

## 1. 목표

- SCE에서 스톡(잔액) 성격 행이 leaf 변동으로 합산되는 두 변형(N1-d·N1-e)을 제거한다.
- 성공 기준: §6 검증 명령 6개 전부 기대 출력 일치.

## 2. 컨텍스트

- 읽어야 할 파일 (수정 전 반드시):
  - `src/normalize/sce.py` (change_role 부여·벡터동일성 retag(N1-c)·검산 경로)
  - `src/normalize/config.py` (`restated_begin_markers` 등 role 마커 로딩 + `normalize_label`)
  - `config/canonical_accounts.yaml`의 `sce_change_roles` 부근
  - `tests/test_normalize.py` (N1-c 테스트 형식)
- 배경 (모르면 잘못 판단할 사실):
  - **N1-d 증거(00158909 은행 557조, 2023~2025 검산 FAIL 28,075,518/30,257,516/32,425,618)**:
    raw CFS SCE의 blank-id **`소계`** 행 = "기초+소유주거래 반영 후 **잔액**"(스톡). 미등록이라
    `기타 중요 계정` leaf로 Σleaf에 혼입. 2023 bare 28,075,518 = FAIL 잔차와 정확 일치(재현됨).
    그 행 제외 시 3개년 모두 차이 0. **begin과 벡터가 다르므로(소유주거래 반영 후) N1-c
    벡터동일성으로 못 잡는다.** 또한 이 행을 subtotal로 등록하면 R3 잔여보정이 28조를 도로
    흡수하므로 **반드시 검산·잔여보정 양쪽에서 제외되는 stock 계열 role**이어야 한다.
  - **N1-e 증거(00164362/2020 검산 FAIL 24,889)**: 같은 회사 같은 표에 라벨 공백 변형 2행 —
    `회계정책변경 효과 반영후자본`(공백 有)은 **restated_begin으로 잡혔고**,
    `회계정책변경 효과반영후자본`(공백 無)은 **leaf로 샜다**(DB 재현: 전자 25,037.92
    restated_begin / 후자 24,889.34 leaf). 즉 1차 원인은 마커 미등록이 아니라
    **restated_begin 마커 비교가 공백 정규화(normalize_label류)를 거치지 않는 것**일 가능성이
    높다 — 코드에서 비교 경로를 먼저 확인하라. (보조: 이 행은 재작성이 구성요소 간
    재배분이라 N1-c 벡터동일성도 미발동 — 총계만 동일, 컬럼 불일치.)

## 3. 설계 (이대로 구현 — 임의 변경 금지)

- **N1-e (먼저)**: restated_begin 마커 매칭 경로에 라벨 정규화(공백 제거 등 기존
  `normalize_label` 재사용)를 적용. 마커 사전 자체도 정규화 키로 보관. 정규화 적용 후에도
  안 잡히는 변형('반영후자본' 계열)이 있으면 `restated_begin_markers`에 **config 데이터로**
  추가 등록.
- **N1-d**: 새 판별 규칙 — bare(component_std='-') 변동행이 다음을 모두 만족하면 change_role을
  `stock_balance`(신규 role, 검산 Σleaf와 R3 잔여보정 양쪽에서 제외)로 재지정:
  ①해당 행 시점까지의 누적(begin + 그 행보다 ord가 앞선 leaf bare 합)이 그 행 bare 값과
  round 후 일치(잔액 정합) ②라벨이 변동 동사형이 아닌 잔액형(소계·잔액 등 — 판별의 1차
  근거는 ①의 수치 정합이며 라벨은 보조. 라벨 문자열을 src/ 조건에 하드코딩하지 말 것 —
  잔액형 라벨 목록이 필요하면 config 데이터로).
  ord(원천 행 순서) 정보가 sce 프레임에 없으면 raw 적재 경로에서 보존하는 변경까지 포함하되,
  스키마 변경이 커지면 **STATUS: NEEDS_CONTEXT**로 멈춰 보고.
- 설계와 현장이 안 맞으면 임의 변경 금지 — NEEDS_CONTEXT. 멈추는 것은 실패가 아니다.

## 4. 단계 체크리스트 (순서 고정 — 건너뛰기·합치기 금지)

- [ ] Step 1: RED — ①N1-e 공백 변형 마커 매칭 테스트(현재 실패) ②N1-d 잔액 정합 행
      stock 재지정 테스트(현재 실패) ③역버그 가드: 진짜 leaf 변동(누적과 불일치)은 leaf 유지
      테스트(통과해야 함).
      증거: `uv run python -m pytest tests/ -q -k "n1d or n1e or stock"` 출력에 **2 failed, 1 passed**(또는 동등) 포함
- [ ] Step 2: N1-e 구현(정규화 매칭) → 해당 테스트 GREEN.
      증거: 같은 명령에서 N1-e 케이스 passed
- [ ] Step 3: N1-d 구현(잔액 정합 판별 + stock_balance role) → 전부 GREEN.
      증거: 같은 명령 **failed 0** 출력 원문
- [ ] Step 4: 재정규화 — round5 5사 + round1~4 20사 + known 6사 `--force`.
      증거: renormalize_all 마지막 줄(error=0)
- [ ] Step 5(마지막): §6 전체 검증 후 출력 원문 확보.
※ 단계 증거는 보고에 원문 포함. 증거 없는 단계 = 미수행.

## 5. 금지 사항 (1건이라도 위반 시 작업 전체 실패)

- 하드코딩: corp_code(00158909·00164362)·금액(28,075,518 등)·`소계` 라벨 문자열을 **src/
  판별 조건에 기입 금지**(잔액형 라벨 보조 목록은 config 데이터로만).
- 테스트 약화 금지: skip/xfail·assert 삭제·완화·기대값 출력 맞춤. 라운드1~4 테스트(N1-c
  벡터동일성·R3-b 잔여보정·D5) 무수정 통과 필수 — 특히 **N1-d role이 R3 잔여보정을 우회하는지
  반대로 잔여보정이 stock을 흡수하는지 양방향 테스트 필수**.
- 범위 밖 수정 금지 — 수정 가능: `src/normalize/sce.py`, `src/normalize/config.py`,
  `config/canonical_accounts.yaml`(마커/잔액형 목록 등록), `tests/`, (필요시 ord 보존 한정으로
  `src/normalize/pipeline.py`·`src/db/normalized.py` — 이 경우 보고에 사유 명시).
  **건드리면 실패**: 하니스(`data/backtest/_p1_*.py`), `src/signals/`·`src/backtest/`,
  정답지·표본 json·매트릭스.
- 체크리스트 생략·순서 변경 금지. 실패·미완을 완료로 보고 금지.

## 6. 최종 검증 (완료 선언 전 필수 — 하나라도 다르면 DONE 금지)

- `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py data/backtest/_round_targets_round5.json`
  → 기대: 00158909 2023~2025·00164362/2020 SCE검산 **OK**, 소실 0 (수집갭 3건·주석갭 1건 외 OK)
- `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py` → 기대: known 전수 PASS
- round1·round2·round3·round4 배치 → 기대: 기존과 동일(수집갭·주석갭 외 OK) — N1-c·R3-b·D5 무회귀
- 백테스트 → 기대: recall 5/6 유지
- `uv run python -m pytest tests/ -q` → 기대: 전체 passed(164+신규, failed 0)
- (역버그 직접 증거) 00158909/2023 duckdb:
  `SELECT change_role FROM sce_equity_components WHERE change_label='소계' AND component_std='-'`
  → 기대: stock_balance (leaf 아님)

## 7. 완료 보고 양식 (이 양식 그대로, 항목 생략 금지)

```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: Step 1~5 [x]/[ ] + 각 단계 증거(명령 + 출력 원문)
변경 파일: <실제 변경한 파일만>
최종 검증 결과: §6 명령 6개 각각의 출력 원문
미완·우회·우려 사항: <정직하게 전부. 없으면 "없음">
```

신뢰 규칙: 정직한 DONE_WITH_CONCERNS/BLOCKED는 정상 경로. 거짓 DONE은 설계자의 §6 재실행으로
반드시 드러난다.

---

## 부록: 기록 (이번 작업 대상 아님 — 삭제 금지)

- 수집 갭(A6) 금융 7사째(00158909 2020~2022 BOM만). 주석 부분 갭 변형: 00238782/2021만
  notes_xbrl 부재(본문 정상) — 수집 레이어 별도 과제 누적.
- 부호반전 16건 전건 차감 -abs 의도(거짓 경보). 동액 parent-child dedup(00238782 6개년) 기존 유형.
- 00238782/2023 혼합형 BS(금융업자산 분리표시) — blank-id 보존 확인, canonical 등록 후보(관찰).
- 00158909/2025 raw 태깅 변경(OtherFinancialLiabilities→OtherLiabilities)으로 canonical 시계열
  단절 — 매퍼 정동작, D6/시계열 관점 관찰.
