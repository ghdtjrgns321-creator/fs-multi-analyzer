# 작업: P1 라운드11 수정 — 소계 동명블록 retag(R11-a) + derived 합계 부모-자식 중첩(R11-b)

> 라운드11(층화 **20사**·74 회사연도, seed=11) 감사 — **수렴 사다리 20사 단계에서 신규 결함 2종
> 발견**(라운드9·10 연속 0의 "수렴 가능성"이 표본 2배에서 깨짐 — 사용자 §9 의심이 옳았다).
> 증거 duckdb 재현 검증(매트릭스 `_VERDICT_MATRIX_round11.md` 게이트 PASS 74×6). 선행:
> [_P1_ROUND10_FIX_PROMPT.md](_P1_ROUND10_FIX_PROMPT.md) 완료.

## 1. 목표

- 동명 '소계' 다중블록 leaf 오분류(R11-a)와 derived 합계의 부모-자식 중첩 이중계상(R11-b)을
  제거한다.
- 성공 기준: §6 검증 명령 6개 전부 기대 출력 일치.

## 2. 컨텍스트

- 읽어야 할 파일: `src/normalize/sce.py`(`_retag_parent_subtotal_vectors`·
  `_add_derived_bare_totals`·`extract_sce_components`), `src/normalize/config.py`
  (`classify_change_role`·`subtotal_label_markers`), `config/canonical_accounts.yaml`,
  `tests/test_normalize.py`.
- 배경 (모르면 잘못 판단할 사실):
  - **R11-a 증거(00631518 105조, 2020~2022 검산 FAIL -2,754,752/4,174,729/3,621,615)**: CFS SCE에
    `change_label='소계'`(account_id=`-표준계정코드 미사용-`) 행이 **한 표에 여러 블록**(총포괄손익
    소계 + 자본거래 소계 등)으로 반복 출현, 전부 `change_role=leaf`로 검산 합산(DB 재현: 2021은
    소계 1,169,277 + 3,005,453 = 4,174,730 ≈ FAIL). `_retag_parent_subtotal_vectors`가
    `(change_label, account_id)`로 그룹화 → 동명 '소계' 두 블록이 한 그룹으로 통합돼 어떤 자식
    묶음과도 벡터 매칭 실패 → leaf 잔존. 세토피아 "동명+blank id" dedup 소실의 친척(여기선
    소실이 아니라 role 오분류).
  - **R11-b 증거(00153861 4.1조, 2020 FAIL -882·2021 FAIL -668)**: `_add_derived_bare_totals`의
    component축 중첩 이중계상. "FVOCI 처분"은 연결 총계행 없는 자본 내 대체(기타자본구성요소
    -882 + 이익잉여금 +882 = 0). derived 합계가 부모 컬럼(기타자본구성요소 -882)과 그 밑에
    nesting된 **자식 상세 컬럼(평가손익 -882)을 둘 다 summable로 합산** → -882 유령 leaf 생성,
    상쇄짝 +882은 누락. DB 재현: 그 derived leaf만 제외하면 검산 OK이며, 직접 `sce_balance`
    helper에서는 원 단위 잔차가 허용오차 이내로 남을 수 있다. **2021은 raw 연결member
    컬럼 직접 합산 시 diff 0 → 원공시 정상, FAIL은 순수 정규화 산물.** 라운드8 N2-f(형제 변동행
    합)와 다른 축(단일 변동행 내 부모member+중첩자식member 동시 합산).
  - **R11-c(부수, R11-a 해소로 동시 해결 가능)**: 00545716 2021/2022 — raw `account_id=
    ifrs-full_IssueOfEquity`(유상증자)에 `account_nm='총포괄손익 소계'` 모순. label에
    '총포괄손익' 포함이라 subtotal 마커가 잡으면 해소.

## 3. 설계 (이대로 구현 — 임의 변경 금지)

- **R11-a**: `_retag_parent_subtotal_vectors`의 그룹 단위를 `(change_label, account_id)`에서
  **source_order 인접 블록**(같은 표 내 연속 행 묶음)으로 분리해 동명 다중블록을 별개로
  매칭. 또는 `account_nm`이 정확히 '소계'인 bare 행(detail이 자본 member 최상위 컬럼)을
  `subtotal_label_markers`에 추가해 **초기 role 부여 단계에서 subtotal로 분류** — 단 일반 leaf
  흡수 위험을 막기 위해 발동 조건은 **수치 정합(인접 자식 합과 일치) 우선**, '소계' 라벨은 보조.
- **R11-b**: `_add_derived_bare_totals`의 summable 합산에서 **detail_path가 prefix-nested 관계인
  자식 컬럼을 제외**(부모 member + 그 자식 member 동시 합산 금지) — leaf끼리만 합산해 자본 내
  대체(net 0) 변동행이 유령 leaf를 만들지 않게. round 후 비교(accounting-precision).
- **R11-c**: R11-a의 subtotal 마커 경로가 '총포괄손익 소계'를 잡는지 테스트로 확인. 안 잡으면
  '총포괄손익' 부분문자열 마커를 config에 추가.
- 설계와 현장이 안 맞으면 **STATUS: NEEDS_CONTEXT**.

## 4. 단계 체크리스트 (순서 고정)

- [ ] Step 1: RED — ①동명 '소계' 2블록 각각 subtotal 재태깅 테스트 ②derived 합계 부모-자식
      중첩 제외 테스트 ③id-label 모순 '총포괄손익 소계' subtotal 처리 ④진짜 독립 leaf(벡터
      불일치)는 leaf 유지 가드 ⑤자본 내 대체(net 0) 상쇄짝 보존 가드.
      증거: `uv run python -m pytest tests/ -q -k "r11"` 출력 원문(failed 포함)
- [ ] Step 2: R11-a 구현 → GREEN. 증거: 출력 원문
- [ ] Step 3: R11-b 구현 → GREEN. 증거: 출력 원문
- [ ] Step 4: R11-c 확인/구현 → 전부 GREEN. 증거: failed 0 원문
- [ ] Step 5: 재정규화 — round11 20사 + round1~10 50사 + known 6사 `--force`. 증거: error=0
- [ ] Step 6(마지막): §6 전체 검증.
※ 단계 증거 원문 필수.

## 5. 금지 사항

- 하드코딩: corp_code·금액을 src/ 조건에 기입 금지. 마커·alias는 config로만.
- 테스트 약화 금지. 라운드1~10 테스트 무수정 통과 — 특히 R11-a가 라운드10 '소계 마커'·라운드8
  부모소계 판별을, R11-b가 라운드6 N1-g 도출을 깨지 않는지 가드 필수.
- 수정 가능: `src/normalize/{sce,config}.py`, `config/canonical_accounts.yaml`, `tests/`.
  **건드리면 실패**: 하니스, signals/backtest, 정답지·표본 json.
- 체크리스트 생략 금지. 실패·미완을 완료로 보고 금지.

## 6. 최종 검증

- round11 배치 → 기대: 00631518 2020~2022·00545716 2021/2022·00153861 2020/2021 검산 **OK**,
  소실 0·전기소실 0. 00631518/2025(-31)·00153861/2022(3,555)·00120216/2025(-1)은 원공시/
  granularity로 잔존 허용(사유 명시)
- known + round1~10 배치 → 기대: 무회귀(소계·도출 보강이 기존 검산 OK를 안 깸)
- 백테스트 → recall 5/6 유지
- `uv run python -m pytest tests/ -q` → 전체 passed
- (직접 증거) 00631518/2021 duckdb: change_label='소계' 행들의 change_role이 전부 'leaf'가 아님
- (직접 증거) 00153861/2020 duckdb: 검산 OK, derived 유령 leaf 소멸. 직접 `sce_balance`
  diff가 원 단위 잔차(예: `-1`)로 남아도 tolerance 이내이면 성공으로 본다.

## 7. 완료 보고 양식

```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: Step 1~6 [x]/[ ] + 각 단계 증거 원문
변경 파일 / 최종 검증 결과(§6 원문) / 미완·우회·우려 사항
```

---

## 부록: 수렴 사다리 갱신 (대상 아님 — 삭제 금지)

- **신규 유형 추이: 5→5→2→1→2→3→2→1→0→0→2**. 라운드11(20사)에서 신규 2종 — **라운드9·10의
  연속 0은 표본 부족이었음이 입증됨**. 수렴 카운터 리셋.
- **갱신 사다리: 본 수정 완료 → 라운드12=20사 재검(seed=12, 0 확인) → 50사 → 100사. 각 단계
  신규 0이어야 다음 진행, 100사까지 0이면 수렴 선언.** (직전 사다리에서 20사를 건너뛰지 않고
  다시 0을 확인하는 이유: 라운드11이 20사에서 처음 잡혔으므로 같은 규모 재현 필요.)
- 진짜 원공시 모순(00631518/2025·00153861/2022 등)·granularity(-1)는 정직 노출 유지.
