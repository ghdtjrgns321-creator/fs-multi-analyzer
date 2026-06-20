# 작업: P1 라운드6 수정 — restated 델타형 처리(N1-f) · 합계열 미공시 검산(N1-g) · 전기 비교치 dedup 소실(N4-c)

> 라운드6(층화 5사·23 회사연도, seed=6, `_round_targets_round6.json`) 감사 발견 수정.
> 신규 3종·당기 값 소실 0(N4-c는 전기/전전기 비교치 소실). 증거 duckdb·raw 재현 검증
> (매트릭스 `_VERDICT_MATRIX_round6.md` 게이트 PASS). 선행: [_P1_ROUND5_FIX_PROMPT.md](_P1_ROUND5_FIX_PROMPT.md)(N1-d·N1-e 완료).

## 1. 목표

- SCE 검산의 재작성 공시 변형 2종(N1-f·N1-g)과 전기 비교치 dedup 소실(N4-c)을 제거한다.
- 성공 기준: §6 검증 명령 7개 전부 기대 출력 일치.

## 2. 컨텍스트

- 읽어야 할 파일 (수정 전 반드시):
  - `src/normalize/sce.py` (`_retag_stock_balance_rows`·restated_begin 처리·`sce_balance` 검산)
  - `src/normalize/pipeline.py` (`_dedupe_*` — 라운드1 N4 EXACT 보존 가드 위치)
  - `config/canonical_accounts.yaml` (`stock_balance_label_markers`·`restated_begin` 마커)
  - `data/backtest/_p1_company_review.py` §D (N4-c 하니스 사각 보강 대상)
  - `tests/test_normalize.py` (N1-d/N1-e 테스트 형식)
- 배경 (모르면 잘못 판단할 사실):
  - **N1-f 증거(00127158/2020 검산 FAIL 31,300)**: `수정 후 금액`(33,872 = 기초 31,300 +
    재작성효과 2,572) 행이 role=leaf로 혼입(DB 재현됨, CFS/OFS 각 1행). 이중 결함:
    ⓐ`stock_balance_label_markers: [소계, 잔액]`에 '수정 후' 계열 미등록
    ⓑ`_retag_stock_balance_rows`가 restated_begin을 만나면 running을 **대체**하는데, 이
    재작성효과는 **델타형**(+2,572, begin과 벡터 다름)이라 잔액 매칭이 어긋남 — 마커만
    고치면 -2,572 잔차가 남는다. 둘 다 고쳐야 0.
  - **N1-g 증거(00127158/2023 검산 FAIL 514)**: `재무제표 재작성효과`(ord=10)가 이익잉여금
    구성요소 열에만 -514,362,877 공시, **합계열(component '-') 부재** → bare 기반 검산이
    영영 못 봄. restated_begin 분류 자체는 정확.
  - **N4-c 증거(00127158/2023 OFS)**: raw blank-id `전환사채` 2행 — 둘 다 당기 빈값, 한 행만
    전기 6,395,852,761 보유. 당기 NaN 동명행이 중복으로 오인돼 전기 보유 행이 드롭 →
    norm엔 amount·prior 모두 NaN인 행만 잔존(DB 재현됨). 동류: 같은 회사 유동파생상품자산
    (전기 4,014,310원), 00176914/2023 CFS 순확정급여부채(전전기 5,355,544천원).
    §D가 당기만 대조해서 하니스도 못 보던 사각.

## 3. 설계 (이대로 구현 — 임의 변경 금지)

- **N1-f**: ⓐ`stock_balance_label_markers`에 '수정후금액·조정후금액' 계열 등록(정규화 키 —
  N1-e의 normalize 매칭 경로 재사용). ⓑrestated_begin 처리를 벡터로 분기: begin 벡터와
  **전 셀 동일**(N1-c 판별 재사용)이면 running **대체**(잔액형), 다르면 running에 **가산**
  (델타형). 분기 결과를 검산식에도 일관 반영.
- **N1-g**: bare(component '-') 행이 없는 change 행 그룹은 **구성요소 열 합**으로 합계를
  도출해 검산에 투입(도출값임을 구분하는 플래그 컬럼 또는 component_std 별도 표기 —
  실데이터 행을 위조하지 말 것).
- **N4-c (파이프라인)**: dedup 키에 **prior_amount·prior2_amount 포함** — 당기 동일·전기
  상이 행은 중복이 아니다. 라운드1 N4의 EXACT 보존 가드와 일관되게, 드롭이 아니라 보존
  (대표 외 행 '기타' 강등 허용).
- **N4-c (하니스)**: `_p1_company_review.py` §D에 전기 대조 추가 — raw frmtrm_amount의
  |절대값|이 norm의 prior_amount 집합(+SCE prior)에 미출현이면 `전기소실` 카운트로 노출,
  [기계요약]에 `전기소실=N` 필드 추가 + `_p1_review_all.py` 파서·표 컬럼 동기화.
  (B5 시계열 값대조의 부분 구현이기도 함.)
- 설계와 현장이 안 맞으면 **STATUS: NEEDS_CONTEXT**로 멈춰 보고. 멈춤은 실패가 아니다.

## 4. 단계 체크리스트 (순서 고정 — 건너뛰기·합치기 금지)

- [ ] Step 1: RED — ①N1-f 델타형 restated 가산 테스트 ②N1-f 잔액형 대체 유지 가드(통과 유지)
      ③N1-g 합계열 미공시 도출 테스트 ④N4-c 당기 NaN·전기 상이 동명행 보존 테스트.
      증거: `uv run python -m pytest tests/ -q -k "n1f or n1g or n4c"` 출력에 **3 failed, 1 passed**(또는 동등) 포함
- [ ] Step 2: N1-f 구현(마커+델타 분기) → 해당 GREEN. 증거: 같은 명령 출력
- [ ] Step 3: N1-g 구현(구성요소 합 도출) → 해당 GREEN. 증거: 같은 명령 출력
- [ ] Step 4: N4-c 파이프라인 구현(dedup 키 prior 포함) → 전부 GREEN.
      증거: 같은 명령 **failed 0** 원문
- [ ] Step 5: N4-c 하니스 구현(§D 전기 대조 + 기계요약/러너 동기화).
      증거: `PYTHONPATH=. uv run python data/backtest/_p1_company_review.py 00127158 2023` 출력에
      `전기소실` 필드 존재(수정 전 데이터면 >0, Step 6 재정규화 후 0)
- [ ] Step 6: 재정규화 — round6 5사 + round1~5 25사 + known 6사 `--force`.
      증거: renormalize_all 마지막 줄(error=0)
- [ ] Step 7(마지막): §6 전체 검증 후 출력 원문 확보.
※ 단계 증거는 보고에 원문 포함. 증거 없는 단계 = 미수행.

## 5. 금지 사항 (1건이라도 위반 시 작업 전체 실패)

- 하드코딩: corp_code(00127158·00176914)·금액(31,300/514/6,395,852,761)·'수정 후 금액' 라벨
  문자열을 **src/ 판별 조건에 기입 금지**(마커는 config 데이터로만).
- 테스트 약화 금지: skip/xfail·assert 삭제·완화·기대값 출력 맞춤. 라운드1~5 테스트(N1-c·
  N1-d·N1-e·R3-b·D5·N4) 무수정 통과 필수. 특히 N4-c dedup 키 변경이 **진짜 중복**(당기·전기
  모두 동일) 제거를 깨뜨리지 않는지 가드.
- 범위 밖 수정 금지 — 수정 가능: `src/normalize/sce.py`, `src/normalize/pipeline.py`,
  `src/normalize/config.py`, `config/canonical_accounts.yaml`, `tests/`,
  `data/backtest/_p1_company_review.py`·`_p1_review_all.py`(**N4-c §D 전기 대조·요약 필드
  한정** — 다른 섹션 변경 금지). **건드리면 실패**: `_p1_verdict_gate.py`, `src/signals/`·
  `src/backtest/`, 정답지·표본 json·매트릭스.
- 체크리스트 생략·순서 변경 금지. 실패·미완을 완료로 보고 금지.

## 6. 최종 검증 (완료 선언 전 필수 — 하나라도 다르면 DONE 금지)

- round6 배치 → 기대: 00127158 2020·2023 SCE검산 **OK**, 전 행 소실 0·**전기소실 0**
  (수집갭 3건·주석갭 1건 외 OK)
- known 배치 → 기대: 전수 PASS (전기소실 포함)
- round1~round5 배치 → 기대: 기존과 동일 + 전기소실 0 (수집갭·주석갭 외)
- 백테스트 → 기대: recall 5/6 유지
- `uv run python -m pytest tests/ -q` → 기대: 전체 passed(167+신규, failed 0)
- (직접 증거) 00127158/2023 duckdb: 전환사채 행 prior_amount=6,395,852,761 존재
- (직접 증거) 00127158/2020 duckdb: '수정 후 금액' change_role이 leaf 아님

## 7. 완료 보고 양식 (이 양식 그대로, 항목 생략 금지)

```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: Step 1~7 [x]/[ ] + 각 단계 증거(명령 + 출력 원문)
변경 파일: <실제 변경한 파일만>
최종 검증 결과: §6 명령 7개 각각의 출력 원문
미완·우회·우려 사항: <정직하게 전부. 없으면 "없음">
```

신뢰 규칙: 정직한 DONE_WITH_CONCERNS/BLOCKED는 정상 경로. 거짓 DONE은 설계자의 §6 재실행으로
반드시 드러난다.

---

## 부록: 기록 (이번 작업 대상 아님 — 삭제 금지)

- **수집 단계 누락(재수집 필요)**: 00127158/2023 — financial_statement_xbrl.zip·notes_xbrl/·
  collection_summary.json 부재(타 5년 존재). 수집 레이어 과제에 누적(주석갭의 원인).
- 01584183 2020~2022 원천 부재(BOM·JSON []) — **비금융 첫 사례**(신규 공시 회사로 추정).
  수집 갭 패턴이 "금융업"이 아니라 "해당 연도 XBRL 미공시"일 가능성 — 수집 과제에서 함께 규명.
- 01406618/2022 CF의 원공시 XBRL 태깅 오류 9행(법인세 납부←DividendsPaid 등) — 일부
  exact 무경고 통과 = N5 검출 사각 보강감(N5 2단계 자료 누적).
- 금융업 혼합 BS(00176914 -52,131,318 = 금융업자산 보존 일치)·매각예정자산 항등식 차이 —
  데이터 특성. 부호반전 20건 전건 의도 -abs. 주석 적재율 급증은 원천 detail axis 확대(정상).
