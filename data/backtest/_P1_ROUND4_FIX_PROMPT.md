# 작업: P1 라운드4 수정 — 스톡 재태깅 변동의 벡터 동일성 판별(N1-c)

> 라운드4(층화 5사·16 회사연도, seed=4, `_round_targets_round4.json`) 감사 발견 수정.
> 신규 1종·값 소실 0(매트릭스 `_VERDICT_MATRIX_round4.md` 게이트 PASS, 증거 duckdb·raw 재현).
> 선행: [_P1_ROUND3_FIX_PROMPT.md](_P1_ROUND3_FIX_PROMPT.md)(R3-b·M1 완료).

## 1. 목표

- 회사가 "수정후 기초자본 스톡"을 변동 concept(`오류수정에 따른 증가(감소)` 등)에 재태깅한
  행을 구조적으로 판별해 검산 이중계상을 제거한다.
- 성공 기준: §6 검증 명령 5개 전부 기대 출력과 일치.

## 2. 컨텍스트

- 읽어야 할 파일 (수정 전 반드시):
  - `src/normalize/sce.py` (change_role 부여·검산 leaf 합산 경로)
  - `src/normalize/config.py` (`sce_change_roles` 로딩)
  - `tests/test_normalize.py` (기존 R3-b/D5 테스트 형식)
- 배경 (모르면 잘못 판단할 사실):
  - **증거(00136776/2025 CFS, 검산 FAIL 29,636)**: `dart_IncreaseDecreaseThroughCorrectionsOfErrors`
    ('오류수정에 따른 증가(감소)') 행의 **component 벡터가 기초자본(begin) 행과 완전 동일** —
    bare 29,636.06 / 기타자본구성요소 44,754.19 / 이익잉여금 -144,297.17 / 자본금 2,242.42 /
    자본잉여금 127,417.93 / **전기(prior)까지 전부 동일**. 즉 델타가 아니라 "수정후 기초 스톡"의
    재태깅. 현재 role=leaf로 합산돼 기초가 이중계상(차이=기초 bare 그대로).
  - **라벨/role 등록으로 못 고치는 이유**: '오류수정에 따른 증가(감소)'는 다른 회사에서 진짜
    델타(소급 수정액)로 쓰인다. concept 단위 등록은 그 회사들을 역으로 깨뜨림 — 그래서 라벨이
    아니라 **구조(벡터 동일성)** 판별이어야 한다.
  - 진짜 델타가 begin과 전 구성요소·당기·전기 모두 동일할 확률은 사실상 0(동일성은 재태깅의
    지문이다).

## 3. 설계 (이대로 구현 — 임의 변경 금지)

- `sce.py`의 role 부여 단계(또는 직후 후처리)에 **벡터 동일성 규칙** 추가:
  같은 (fs_div, change_label 그룹)의 component 벡터(component_std → (amount, prior_amount)
  전체 셀)가 **begin 행 그룹의 벡터와 전 셀 일치**(round 후 비교 — `accounting-precision`)하면
  그 변동행 그룹의 change_role을 `restated_begin`으로 재지정(검산 leaf 합산에서 제외, 행 자체는
  보존 — 드롭 금지).
- 비교 대상은 begin뿐 아니라 기존 `restated_begin`(조정후 기초) 그룹도 포함(이미 인식된 조정후
  기초와 동일한 재태깅 변형 흡수).
- 부분 일치(일부 component만 동일)는 재지정하지 않는다 — 전 셀 일치만. 임계·완화 금지.
- 설계가 현장과 안 맞으면(예: role 부여 시점에 그룹 벡터 비교가 구조적으로 불가) 임의 변경하지
  말고 **STATUS: NEEDS_CONTEXT**로 멈춰 보고할 것. 멈추는 것은 실패가 아니다.

## 4. 단계 체크리스트 (순서 고정 — 건너뛰기·합치기 금지)

- [ ] Step 1: RED — 합성 케이스 테스트 추가: ①begin과 전 벡터 동일한 '오류수정' 행 →
      restated_begin 기대(현재 leaf라 실패) ②벡터가 다른(진짜 델타) '오류수정' 행 → leaf 유지
      기대(통과해야 함 — 역버그 가드).
      증거: `uv run python -m pytest tests/ -q -k "n1c or 오류수정 or vector"` 출력에 **1 failed, 1 passed**(또는 동등) 포함
- [ ] Step 2: 벡터 동일성 규칙 구현 → Step 1 전부 GREEN.
      증거: 같은 명령 **failed 0** 출력 원문
- [ ] Step 3: 재정규화 — round4 5사 + round1~3 15사 + known 6사 `--force`.
      증거: renormalize_all 마지막 줄(error=0)
- [ ] Step 4(마지막): §6 전체 검증 실행 후 출력 원문 확보.
※ 각 단계 증거는 보고에 원문 포함. 증거 없는 단계 = 미수행.

## 5. 금지 사항 (1건이라도 위반 시 작업 전체 실패)

- 하드코딩: corp_code(00136776)·금액(29,636 등)·'오류수정' **라벨 문자열을 src/ 판별 조건에
  기입 금지** — 판별은 벡터 동일성 구조 규칙만. (라벨 기반 등록이 필요해 보이면 NEEDS_CONTEXT.)
- 테스트 약화 금지: skip/xfail, 기존 assert 삭제·완화, 기대값 출력 맞춤 수정. 특히 라운드1~3의
  N1/D5/R3-b 테스트 무수정 통과 필수.
- 범위 밖 수정 금지 — 수정 가능: `src/normalize/sce.py`, `src/normalize/config.py`(필요시),
  `tests/`. **건드리면 실패**: `config/canonical_accounts.yaml`(이번 회차 등록 없음 — 라벨 등록
  방식이 아니므로), 하니스(`data/backtest/_p1_*.py`), `src/signals/`·`src/backtest/`,
  정답지·표본 json·매트릭스.
- 체크리스트 생략·순서 변경 금지. 실패·미완을 완료로 보고 금지.

## 6. 최종 검증 (완료 선언 전 필수 — 하나라도 다르면 DONE 금지)

- `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py data/backtest/_round_targets_round4.json`
  → 기대: 00136776/2025 SCE검산 **OK**, 전 행 소실 0 (수집갭 3건 외 OK)
- `PYTHONPATH=. uv run python data/backtest/_p1_review_all.py` → 기대: known 기계검사 바닥 전수 PASS
- `..._p1_review_all.py data/backtest/_round_targets.json`·`..._round2.json`·`..._round3.json`
  → 기대: 기존과 동일(수집갭·주석갭 외 OK) — 특히 round1 00159616(진짜 소급수정 보유사) 검산 무회귀
- 백테스트 → 기대: recall 5/6 유지
- `uv run python -m pytest tests/ -q` → 기대: 전체 passed(162+신규, failed 0)

## 7. 완료 보고 양식 (이 양식 그대로, 항목 생략 금지)

```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: Step 1~4 [x]/[ ] + 각 단계 증거(명령 + 출력 원문)
변경 파일: <실제 변경한 파일만>
최종 검증 결과: §6 명령 5개 각각의 출력 원문
미완·우회·우려 사항: <정직하게 전부. 없으면 "없음">
```

신뢰 규칙: 정직한 DONE_WITH_CONCERNS/BLOCKED는 정상 경로. 거짓 DONE은 설계자가 §6을 직접
재실행해 반드시 드러난다.

---

## 부록: 기록 (이번 작업 대상 아님 — 삭제 금지)

- 동질 병합 다발(00165343 4~8그룹·00163673 등)은 동액 parent-child 재태깅 dedup으로 값 왜곡 0
  (라운드2 유형 재현, 정동작 확인). 00165343 그룹 수 변화는 2022 별도전용 전환(데이터 특성).
- N5 검출 사각 관찰: label이 비표준이면 conflict 플래그 미발화(00136776 기타투자자산→공동기업
  투자, 340,600원 미미) — N5 2단계 결정 자료에 누적.
- component(열) 라벨 '이익잉여금(결손금)' 변형 미등록(00163673 unmatched 10~13, 검산 무영향) —
  경미 config 등록감, 다음 라운드 묶음 처리 후보.
- 수집 갭(A6) 금융 6사째(00131850 증권금융 2020~2022). 수집 레이어 별도 과제 누적.
