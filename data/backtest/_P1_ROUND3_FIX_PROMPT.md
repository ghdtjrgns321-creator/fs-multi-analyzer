# 작업: P1 라운드3 수정 — SCE 소계 잔여 보정(R3-b) + alias 오염 분리(M1)

> 라운드3(층화 5사·16 회사연도, seed=3, `_round_targets_round3.json`) 감사 발견 수정.
> 증거 전부 duckdb·raw 재현 검증됨(매트릭스 `_VERDICT_MATRIX_round3.md` 게이트 PASS).
> 선행 회차: [_P1_ROUND2_FIX_PROMPT.md](_P1_ROUND2_FIX_PROMPT.md)(R1~R5 완료).
> 하니스 결함 2건(H1 절사 거짓소실·H2 §I 생존판정)은 감사 세션에서 **이미 수정 완료** — 대상 아님.

## 1. 목표

- SCE 검산의 부분자식 소계 잔여 누락(R3-b)과 config alias 오염(M1)을 수정한다.
- 성공 기준: §6의 검증 명령 4개가 전부 기대 출력과 일치하는 상태.
  ("검산이 좋아졌다" 같은 주관 표현은 성공 기준이 아니다.)

## 2. 컨텍스트

- 읽어야 할 파일 (수정 전 반드시):
  - `src/normalize/sce.py` (검산 leaf 합산·R3 보정이 구현된 곳)
  - `src/normalize/config.py` (SceComponentMap·change_role 로딩)
  - `config/canonical_accounts.yaml`의 `sce_change_roles`·`sce_deduction_changes`·1019행 부근
  - `data/backtest/_P1_ROUND2_FIX_PROMPT.md`의 R3 항목(이번에 일반화할 기존 규칙)
  - `tests/test_normalize.py`(기존 테스트 형식 — 같은 형식으로 추가)
- 배경 (모르면 잘못 판단할 사실):
  - **R3-b 증거**: 00557933/2023 OFS SCE — 회사가 OCI를 `기타포괄손익` 소계 1행(-183,471,915)
    으로 공시 + 구성요소 중 **확정급여재측정(-188,621,362)만** leaf로 별도 공시. 현 검산은
    "소계는 자식 leaf가 있으면 제외" → 소계 잔여 +5,149,447(FVOCI +16M, 해외사업환산 -11M
    상계)이 누락돼 차이 -5(백만). 값 자체는 CIS에 보존 — 소실이 아니라 검산 커버리지 문제.
  - **M1 증거**: `config/canonical_accounts.yaml:1019` — canonical
    `지분법기타포괄손익재분류가능`의 aliases에 `지분법이익잉여금`(이익잉여금 실질) 포함.
    00791209/2025 CFS SCE에서 +31,847,143원이 OCI로 분류(§F leaf -1,372 = -1,404 + 32 병합).
  - 라운드2 R3 규칙("bare leaf 자식 0개인 소계는 그 소계를 leaf로 채택")은 자식이 1개라도
    있으면 비적용 — R3-b는 그 규칙의 일반화다.

## 3. 설계 (이대로 구현 — 임의 변경 금지)

- **R3-b**: 검산(`sce_balance` 경로)의 소계 처리를 이분법에서 **잔여 보정**으로 일반화:
  `잔여 = 소계 bare 값 − Σ(그 소계의 구성 canonical 중 bare leaf로 공시된 것)` 를 leaf로
  합산. 자식 전부 공시 → 잔여≈0(기존 동작과 동치), 자식 0개 → 잔여=소계(기존 R3과 동치).
  소계-구성 멤버십은 **config 데이터**(`sce_change_roles` 확장 또는 인접 신규 키)로 선언 —
  최소 `기타포괄손익` 소계의 구성 canonical 목록(확정급여재측정손익·FVOCI평가손익·
  해외사업환산손익·지분법기타포괄손익 계열 등 기존 canonical 이름 사용).
- **M1**: `지분법이익잉여금`을 1019행 OCI alias에서 제거 → 전용 canonical
  `지분법이익잉여금변동`(role leaf)으로 분리 등록. 이어 동류 오염 스캔: yaml에서
  `이익잉여금` 토큰이 OCI/자본잉여금 계열 canonical의 alias에 들어간 곳을 grep로 전수 확인,
  발견 시 같은 방식으로 분리(발견 0이면 "0건"을 보고에 명시).
- 설계가 현장과 안 맞으면(예: 멤버십 선언 구조가 기존 config 스키마와 충돌): 임의 변경하지
  말고 즉시 멈추고 **STATUS: NEEDS_CONTEXT**로 보고할 것. 멈추는 것은 실패가 아니다.

## 4. 단계 체크리스트 (순서 고정 — 건너뛰기·합치기 금지)

- [ ] Step 1: RED — R3-b 실패 테스트 추가(부분자식 소계 합성 케이스: 소계 -183, 자식 -188
      → 검산 차이 0이어야 하는데 현재 -5로 실패). M1 실패 테스트(지분법이익잉여금 leaf가
      OCI canonical로 매핑되지 않아야 함).
      증거: `uv run python -m pytest tests/ -q -k "r3b or 지분법 or m1"` 출력에 **2 failed** 포함
- [ ] Step 2: R3-b 구현(config 멤버십 + 잔여 보정) → Step 1 테스트 GREEN.
      증거: 같은 명령이 **passed**(failed 0)로 끝난 출력 원문
- [ ] Step 3: M1 구현(alias 분리 + 동류 오염 grep 스캔 결과 기록).
      증거: `grep -n "지분법이익잉여금" config/canonical_accounts.yaml` 출력(전용 canonical
      아래에만 존재) + 동류 스캔 grep 명령·출력 원문
- [ ] Step 4: 재정규화 — round3 5사 + round1 5사 + round2 5사 + known 6사 전부 `--force`.
      증거: `PYTHONPATH=. uv run python -m src.normalize.renormalize_all --force <각 corp...>`
      마지막 줄([완료] 처리 N | renorm=... error=0)
- [ ] Step 5(마지막): §6 전체 검증 실행 후 출력 원문 확보.
※ 각 단계의 증거는 완료 보고에 원문 그대로 포함한다. 증거 없는 단계는 미수행으로 간주한다.

## 5. 금지 사항 (1건이라도 위반 시 작업 전체 실패)

- 하드코딩: corp_code(00557933·00791209 등)·연도·금액(-183,471,915 등)을 **src/ 코드에 분기
  조건으로 기입 금지**. 소계 멤버십·alias는 전부 `config/canonical_accounts.yaml` 데이터로.
- 테스트 약화 금지: skip/xfail 추가, 기존 assert 삭제·완화, 기대값을 출력에 맞춰 수정 금지.
  특히 라운드2 R3·D5 테스트를 R3-b에 맞춰 약화하는 것 금지(두 규칙은 동치 관계여야 함).
- 범위 밖 수정 금지 — 수정 가능: `src/normalize/sce.py`, `src/normalize/config.py`,
  `config/canonical_accounts.yaml`, `tests/` 신규·기존 normalize 테스트.
  **건드리면 실패**: `data/backtest/_p1_*.py` 하니스(이번 회차 수정분 없음),
  `src/signals/`·`src/backtest/`, `known_cases.json`, `_round_targets*.json`, 매트릭스 파일.
- 체크리스트 항목 생략·순서 변경 금지. 실패·미완을 완료로 보고 금지.

## 6. 최종 검증 (완료 선언 전 필수 실행 — 하나라도 다르면 DONE 금지)

- `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py data/backtest/_round_targets_round3.json`
  → 기대: 00557933/2023 SCE검산 **OK** (수집갭 6건·주석갭 1건 외 전 행 OK·소실 0)
- `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py` (known) → 기대: 기계검사 바닥 전수 PASS
- `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py data/backtest/_round_targets.json` 및
  `..._round_targets_round2.json` → 기대: 기존과 동일(round1: 수집갭 3건 외 OK / round2: 수집갭
  6+주석갭 1 외 OK) — R3·D5 회귀 0
- `PYTHONPATH=. uv run python -m src.backtest.run_backtest` 계열(STATE 참조) → 기대: recall 5/6 유지
- `uv run python -m pytest tests/ -q` → 기대: 전체 passed(기존 160+신규, failed 0)
※ 원인 미상 불일치는 BLOCKED로 보고.

## 7. 완료 보고 양식 (이 양식 그대로, 항목 생략 금지)

```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: Step 1~5 [x]/[ ] + 각 단계 증거(명령 + 출력 원문 붙여넣기)
변경 파일: <실제 변경한 파일만>
최종 검증 결과: §6 명령 5개 각각의 출력 원문
미완·우회·우려 사항: <정직하게 전부. 없으면 "없음">
```

신뢰 규칙: 부분 실패의 정직한 보고(DONE_WITH_CONCERNS/BLOCKED)는 정상 경로이며 다음 지시로
이어진다. 거짓 DONE은 설계자가 §6을 직접 재실행해 반드시 드러나고, 작업 전체를 재수행하게 된다.

---

## 부록: 기록 (이번 작업 대상 아님 — 삭제 금지)

- **N5 실증(본문 CF)**: 00614593/2025 — id `ifrs-full_AdjustmentsForReconcileProfitLoss` +
  label `영업에서 창출된 현금흐름`(-15,660). CF 항등식 재현으로 label이 실질 확정(id 오태깅).
  conflict 플래그 정상 작동. N5 2단계(매핑 규칙 변경) 결정 자료로 누적 — **선반영 금지**(사용자 결정 대기).
- **수집 갭(A6) 5사째 고착**: 00117267·00688996·01675421·00126256·00124106 전부 2020~2022만
  raw 헤더 1행(DART 빈 응답), 2023+ 정상. 금융업 집중 — 수집 레이어 별도 과제(라운드 루프와 분리).
- 부호반전 11건 전부 차감 -abs 의도 내. 금융 2사 거대 미분류(대출채권 61~65조)는 소계-자식
  일치 검증으로 의도 게시 확인.
