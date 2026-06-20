# 작업: 온보딩 QA 게이트 러너 (결정론 G1~G5) + quirk 승격 스캐너

## 1. 목표
- 한 회사연도의 정규화 품질을 기존 검사 스크립트를 **부품화**해 순차 실행하는 `onboarding_gate.py`(결정론 단계 G1~G5 + G6 LLM 입력 dump 생성)와, 반복 quirk를 전사 승격 후보로 찾는 `_quirk_promote_scan.py`를 신설한다.
- 성공 기준: ①`onboarding_gate.py <corp> <year>`가 단계별 PASS/FAIL + 이탈 목록 + G6용 dump 경로를 출력 ②기존 backtest 회사로 실행 시 결정론 단계 정상 동작(재구현 아닌 기존 함수 재사용) ③`_quirk_promote_scan.py`가 3회+ 반복 quirk 후보 출력.

## 2. 컨텍스트
- 읽을 파일(필수): `data/backtest/_p1_company_review.py`(회사 dump·완결성·검산), `data/backtest/_is_cf_arithmetic.py`(IS/CF 산술검산 — `check_company_year` 함수), `data/backtest/_conflict_canonical_inventory.py`(충돌 인벤토리·회사 스코프), `data/backtest/_f1_signal_dangling.py`(Layer A dangling), `src/normalize/config.py`(load_company_quirks), `dev/active/synonym-dedup-onboarding-gate/synonym-dedup-onboarding-gate-plan.md`("게이트 단계 G0~G9"·"일반패턴 승격")
- 배경: 게이트는 raw→정규화 후 FS분석 전 품질 검문소. 결정론 단계(G1~G5)는 LLM 없이 floor. G6(LLM 통독)·반복(G7~G8)·UI는 다음 단계(R4)라 이번엔 **G1~G5 + G6 dump 생성까지**.

## 3. 설계 (이대로 — 재구현 금지, 기존 함수 재사용)
신규 `src/normalize/onboarding_gate.py`:
- `run_gate(corp_code, year) -> dict(gate_report)`:
  - G1 기계검사: `_p1_company_review.py`의 완결성·BS항등식·SCE검산 함수 재사용(import). 필수테이블 존재·항등식·검산 PASS 여부.
  - G2 충돌 인벤토리: `_conflict_canonical_inventory.py` 함수로 이 회사연도 id_label_conflict 수집(회사 스코프). dedup 후 잔여 충돌만.
  - G3 산술검산: `_is_cf_arithmetic.py:check_company_year(db)` 호출 — 경성 위반 목록.
  - G5 신호 무결성: `_f1_signal_dangling.py` Layer A(전사 1회, 회사 무관 — 결과 재사용 가능).
  - G6 dump: `_p1_company_review.py`로 dump 생성 경로 반환(LLM 통독 입력 — 실제 LLM 호출은 R4).
  - **함수가 import 불가(스크립트 __main__만)면**: 해당 스크립트의 핵심 함수를 import 가능하게 최소 리팩터(로직 무변경, `if __name__` 아래로 이동)하거나 subprocess 호출 후 출력 파싱. 로직 재구현 절대 금지.
- 통과기준(`gate_passed`): G1 완결성 FAIL 0 + BS 항등식 tol 이내 + G3 경성위반 0(또는 원공시 표기) + G5 dangling 0. G2 충돌·G6 dump는 보고용(LLM이 판정).
- CLI: `python -m src.normalize.onboarding_gate <corp> <year>` → gate_report 출력(단계별 상태·이탈).

신규 `data/backtest/_quirk_promote_scan.py`:
- `config/company_quirks.yaml` 전수 스캔. 같은 alias_addition/account_override가 **3개+ 회사**에서 반복되면 승격 후보 출력(canonical_accounts.yaml 이관 편집 지시). 1~2회는 quirk 유지 표기.

설계-현장 불일치(기존 함수 구조가 import 부적합 등) 시 멈추고 STATUS: NEEDS_CONTEXT.

## 4. 단계 체크리스트 (순서 고정)
- [ ] Step 1: 4개 검사 스크립트 읽고 재사용 가능한 핵심 함수 인용(import 경로·시그니처). import 불가면 최소 리팩터 계획 명시
- [ ] Step 2: `onboarding_gate.py` 작성(run_gate + CLI) → 증거: 핵심 함수 전문
- [ ] Step 3: 기존 backtest 회사로 실행 → 증거: `PYTHONPATH=. uv run python -m src.normalize.onboarding_gate <corp> <year>` 출력(단계별 PASS/FAIL+이탈+dump경로)
- [ ] Step 4: `_quirk_promote_scan.py` 작성+실행 → 증거: 실행 출력(현재 빈 quirk라 후보 0 정상)
- [ ] Step 5(마지막): 재사용 검증 — 게이트의 G3가 `_is_cf_arithmetic.py`와 동일 결과 내는지 한 회사로 대조(재구현 아님 입증)
      증거: 게이트 G3 출력 vs `_is_cf_arithmetic.py` 직접 실행 동일 회사 일치
- [ ] Step 6: 무회귀 → 증거: `PYTHONPATH=. uv run python -m pytest tests/ -q`(기존 함수 리팩터 시 회귀 0 확인)

## 5. 금지 사항 (1건 위반 시 전체 실패)
- 재구현 금지: 검산·완결성·충돌·dangling 로직을 새로 짜지 말 것. 기존 스크립트 함수 재사용(import 또는 subprocess).
- 하드코딩: corp_code·연도를 코드 분기에 박지 말 것(CLI 인자·데이터).
- 기존 스크립트 로직 변경 금지(import용 최소 리팩터는 로직 불변·테스트 통과 전제).
- 테스트 약화 금지. 범위 밖 수정 금지: onboarding_gate.py(신규)·_quirk_promote_scan.py(신규) + import용 최소 리팩터만. config/yaml 손대지 말 것.
- G6 LLM 실제 호출·반복 루프·UI 구현 금지(이번은 G1~G5 + dump 생성까지. R4 영역).

## 6. 최종 검증
- `python -m src.normalize.onboarding_gate <corp> <year>` 정상 출력(Step 3)
- G3 재사용 일치(Step 5) · pytest green(Step 6) · promote scan 동작(Step 4)

## 7. 완료 보고 양식
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: 항목별 [x]/[ ] + 증거 원문(명령+출력)
변경 파일: 경로 목록(신규/리팩터 구분)
최종 검증 결과: §6 출력 원문
미완·우회·우려: 정직하게(없으면 "없음")
