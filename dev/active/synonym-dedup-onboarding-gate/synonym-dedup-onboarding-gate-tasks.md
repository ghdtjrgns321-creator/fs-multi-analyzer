# 동의어 dedup + 온보딩 게이트 — Task Checklist

## Progress Summary
0 / 18 tasks complete (0%)

## Phase 1: dedup 후보 분류 (M)

- [ ] `_dedup_candidates.py` 신설 — 592쌍 3분류 시드
  - File: `data/backtest/_dedup_candidates.py`
  - Details: `_conflict_canonical_inventory.py` same-statement 덤프 입력. narrower 시드(한 name이
    다른 것 부분문자열 + 차이가 유동/비유동·장기/단기·순/총 접두뿐), mistag 시드(`_264_triage.md`
    진짜충돌 9쌍 패턴: 수익↔이익소계·조정↔소계·OCI↔법인세효과), 나머지 synonym 후보.
    생존자 규칙 자동(account_ids 개수 → ifrs-full 우선 → 일반명) + 신호엔진 참조 canonical 우선.
  - Acceptance: `_dedup_candidates.json` 출력, 592쌍 3분류 라벨링, synonym 후보 수 출력.
  - Size: M

- [ ] synonym 후보 사람 검수 → `_dedup_decisions.yaml`
  - File: `dev/active/synonym-dedup-onboarding-gate/_dedup_decisions.yaml`
  - Details: 각 쌍 synonym/narrower/mistag 확정 + 생존 canonical. 규칙 위반 선택 reason 기록.
    mistag 쌍은 게이트 트랙으로 분리 표기(dedup 대상 아님).
  - Acceptance: 592쌍 전부 판정(미판정 0). synonym/narrower/mistag 건수 집계.
  - Size: L

## Phase 2: dedup 적용 (M)

- [ ] `_apply_dedup.py` 신설 — 편집 지시 생성
  - File: `data/backtest/_apply_dedup.py`
  - Details: synonym 판정만 처리. 생존 canonical 흡수 account_ids/aliases + 삭제 키 목록 출력.
    ruamel.yaml round-trip 가능 시 직접 수정(주석·순서 보존), 불가 시 Edit 지시 목록.
  - Acceptance: 편집 지시 출력. 한 쌍 dry-run 미리보기.
  - Size: M

- [ ] yaml dedup 적용 (minimal edit, 인코딩 가드)
  - File: `config/canonical_accounts.yaml`
  - Details: 생존 블록 account_ids/aliases 흡수, 중복 키 블록 삭제. Edit 블록 단위.
  - Acceptance: yaml 파싱 성공, canonical 수 = 이전 − 통합건수, mojibake 0 (`grep -c $'\\ufffd'` = 0).
  - Size: L

- [ ] 충돌 소멸 측정
  - 검증: `PYTHONPATH=. uv run python data/backtest/_conflict_canonical_inventory.py`
  - Acceptance: 동의어 통합 쌍이 충돌 인벤토리에서 소멸, narrower·mistag 불변.
  - Size: S

## Phase 3: dedup 회귀 검증 (M)

- [ ] 전수 재정규화
  - 검증: `PYTHONPATH=. uv run python -m src.normalize.renormalize_all --force`
  - Acceptance: error 0, renorm 완료.
  - Size: M

- [ ] 신호 dangling 검사
  - 검증: `PYTHONPATH=. uv run python data/backtest/_f1_signal_dangling.py`
  - Acceptance: Layer A dangling 0(통합으로 사라진 canonical을 신호엔진이 참조하면 FAIL → alias 보강).
  - Size: S

- [ ] 백테스트 recall 5/6
  - 검증: `PYTHONPATH=. uv run python -m src.backtest.run_backtest`
  - Acceptance: recall 5/6 유지(회귀 0).
  - Size: S

- [ ] IS/CF 산술검산 무회귀
  - 검증: `PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py`
  - Acceptance: 경성 위반 증가 0.
  - Size: S

- [ ] known + SCE 검산 baseline
  - 검증: `uv run pytest tests/ -v`
  - Acceptance: pytest green, SCE 검산 baseline 유지.
  - Size: S

- [ ] 동의어 통합 케이스 재현
  - 검증: `PYTHONPATH=. uv run python data/backtest/_p1_company_review.py <corp> <year>`
  - Details: FVPL금융자산 등 통합 canonical의 §I 병합 가시화에서 두 raw label이 한 canonical로
    충돌 플래그 없이 수렴.
  - Acceptance: 통합 canonical 충돌 미발화, 값 보존.
  - Size: M

## Phase 4: 온보딩 게이트 골격 + quirk 스키마 (M)

- [ ] `config/company_quirks.yaml` 신설
  - File: `config/company_quirks.yaml`
  - Details: account_overrides(account_id+label+force_canonical+reason)·alias_additions(canonical+alias).
    corp_code/year 데이터 키. 예시 1건 주석.
  - Acceptance: yaml 파싱 성공, 예시 포함.
  - Size: S

- [ ] `load_company_quirks` 로더
  - File: `src/normalize/config.py`
  - Details: company_quirks.yaml → dict[corp][year]. 기존 로더 패턴 준수. 미존재 시 빈 dict.
  - Acceptance: 빈/미존재 안전, 예시 로드 단위테스트.
  - Size: S

- [ ] `_apply_company_quirks` 후처리 pass
  - File: `src/normalize/pipeline.py`
  - Details: `_arbitrate_conflicts` 다음 호출. corp_code/year 매칭 override는 canonical 덮음,
    alias_additions 흡수. corp_code는 인자(하드코딩 금지).
  - Acceptance: quirk 없는 회사 무변경, 예시 override 적용 단위테스트.
  - Size: M

## Phase 5: 게이트 부품화 + 러너 (M)

- [ ] 게이트 러너 `onboarding_gate.py` 신설
  - File: `src/normalize/onboarding_gate.py`
  - Details: G1~G6 순차. 기존 스크립트 핵심 함수 import(재구현 금지): `_p1_company_review`(완결성·검산),
    `_is_cf_arithmetic`(산술), `_conflict_canonical_inventory`(충돌). gate_report dict 집계.
    P1결함 0 + 기계검사 PASS면 통과.
  - Acceptance: `python -m src.normalize.onboarding_gate <corp> <year>` → 단계별 PASS/FAIL +
    이탈 목록. 기존 backtest 회사 PASS 재현.
  - Size: L

- [ ] G6 LLM 통독 연결
  - File: `src/normalize/onboarding_gate.py`
  - Details: `_p1_company_review.py` dump → `_HOLISTIC_AUDIT_PROMPT.md` 9렌즈 LLM(subagent 위임).
    findings를 P1결함/원공시/P2후보 파싱.
  - Acceptance: LLM findings 생성, P1결함 카운트가 종료조건 반영.
  - Size: M

- [ ] 반복 루프 + 종료조건(N=3)
  - File: `src/normalize/onboarding_gate.py`
  - Details: G7 quirk 등록 → G8 재정규화 → G1 재실행. P1결함 0 또는 N=3 종료.
  - Acceptance: 이탈 회사가 quirk 등록 후 이탈 0 수렴(시뮬레이션).
  - Size: M

## Phase 6: 일반 패턴 승격 (S)

- [ ] `_quirk_promote_scan.py` 신설
  - File: `data/backtest/_quirk_promote_scan.py`
  - Details: company_quirks.yaml 전수 스캔. 같은 alias/override 3개+ 회사 반복 시 승격 후보 +
    canonical_accounts.yaml 이관 편집 지시.
  - Acceptance: 3회+ 후보 목록, 1~2회는 quirk 유지 표기.
  - Size: M

## Deployment Checklist
- [ ] dedup yaml mojibake 0, 파싱 성공, canonical 수 검증
- [ ] 백테스트 recall 5/6 유지
- [ ] known + SCE/IS-CF 검산 baseline 무회귀
- [ ] 신호 dangling Layer A 0
- [ ] `_arbitrate_conflicts` 무회귀(선행 작업 미파손)
- [ ] company_quirks.yaml 스키마 문서화
- [ ] STATE.md 갱신, ROADMAP 체크
```
