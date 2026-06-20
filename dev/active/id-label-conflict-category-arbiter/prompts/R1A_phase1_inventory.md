# 작업: id_label_conflict 충돌 인벤토리 측정 + 264건 triage (Phase 1)

## 1. 목표
- corpus 충돌의 (id-canonical, label-canonical) 쌍을 전수 추출해 ①범주 부여 필요 canonical 집합 ②sj_div 4분면 ③동일표 범주상이 264건 draft triage를 산출.
- 성공 기준: 분석 스크립트가 "범주 부여 필요 canonical N개(N<600)"·"4분면 건수"·"동일표 범주상이 건수"를 출력하고, triage 문서가 264건(또는 실측치)을 진짜충돌/동의어로 분류.

## 2. 컨텍스트
- 읽어야 할 파일: `data/backtest/_is_cf_arithmetic.py`(corpus 순회·duckdb 패턴 참고), `data/backtest/_holistic_chunks.json`(corpus 101사/383cy 목록), `dev/active/id-label-conflict-category-arbiter/id-label-conflict-category-arbiter-plan.md`(범주 체계 표)
- 따라야 할 패턴: corpus 순회는 `_is_cf_arithmetic.py`의 `corpus_targets()`·duckdb read_only 방식 그대로.
- 배경: `normalized_financials.mapping_status='id_label_conflict'` 행이 충돌. 각 행은 canonical(=id가 채택된 것)과 label을 가짐. label이 가리키는 canonical은 mapper의 `_by_alias`로 다시 구해야 비교 가능(AccountMapper 재사용).
- 거친 범주 체계는 plan.md "범주(category) 차원 설계" 표 사용(pl_revenue/pl_expense/pl_subtotal/pl_oci/cf_operating/cf_investing/cf_financing/cf_subtotal/cf_adjust/bs_asset/bs_liability/bs_equity/sce_change).

## 3. 설계 (이대로 구현)
- 신규 스크립트 `data/backtest/_conflict_canonical_inventory.py`:
  - corpus 383cy 순회 → mapping_status='id_label_conflict' 행 수집.
  - 각 행: id_canonical=row.canonical, label=row.label → AccountMapper로 label_canonical 산출(`_by_alias.get(normalize_label(label))`).
  - 산출 1: 충돌에 등장하는 **distinct canonical 집합**(id측+label측 합집합) 크기 N 출력. (N<600 기대)
  - 산출 2: **sj_div 4분면** — id_canonical.statement·label_canonical.statement를 row.sj_div와 비교해 (id만맞음/label만맞음/둘다맞음/둘다불일치) 건수.
  - 산출 3: **동일표(두 canonical statement 동일) & 거친범주 상이** 쌍 목록 → 별도 출력(이게 triage 대상).
  - 거친 범주는 plan.md 표의 이름 패턴으로 함수 `coarse_category(name, statement)` 구현(자동 도출 시드와 동일 로직).
- triage 문서 `dev/active/id-label-conflict-category-arbiter/_264_triage.md`:
  - 산출3의 각 쌍을 "진짜충돌(label 채택 정당) / 범주노이즈 동의어(id 유지해야)"로 분류, 근거 1줄.
  - 거짓양성 유발 범주 경계 패턴 목록(예: 정부보조금수취 vs 수령 = 동의어인데 범주 갈림).
- 설계가 현장과 안 맞으면(예: label_canonical 산출 불가 다수) 멈추고 STATUS: NEEDS_CONTEXT.

## 4. 단계 체크리스트 (순서 고정)
- [ ] Step 1: `_is_cf_arithmetic.py`·`_holistic_chunks.json`·mapper.py 읽고 corpus순회·_by_alias 패턴 파악
      증거: corpus_targets 시그니처 + _by_alias 사용법 인용
- [ ] Step 2: `_conflict_canonical_inventory.py` 작성(산출1·2·3) → 산출물: 신규 스크립트
      증거: 스크립트 전문(또는 핵심 함수)
- [ ] Step 3: 실행 → 증거: `PYTHONPATH=. uv run python data/backtest/_conflict_canonical_inventory.py` 출력 원문(N·4분면·동일표범주상이 건수)
- [ ] Step 4: `_264_triage.md` 작성(동일표 범주상이 전수 분류) → 산출물: triage 문서
      증거: triage 문서의 집계(진짜충돌 X건/동의어 Y건) + 샘플 10줄
- [ ] Step 5(마지막): 자기검증 — 00545716 영업수익 케이스가 산출3(진짜충돌)에 포함되는지 확인
      증거: triage 문서에서 00545716 관련(영업이익↔매출 or 영업수익) 항목 인용

## 5. 금지 사항
- 하드코딩: corp_code·연도·계정명을 스크립트 분기 조건에 박지 말 것. corpus는 _holistic_chunks.json에서, 범주는 이름 패턴 함수로.
- src/·config/ 수정 금지(이번은 분석·문서만). 읽기만.
- 결과를 만들어내기(fabricate) 금지: 실제 corpus duckdb를 돌린 출력만. 빈 결과를 임의 채우지 말 것.
- triage에서 애매한 쌍을 "진짜충돌"로 과분류 금지 — 애매하면 동의어(보수적, id 유지). 거짓양성 방지가 목적.

## 6. 최종 검증
- `PYTHONPATH=. uv run python data/backtest/_conflict_canonical_inventory.py` → 기대: N<600, 4분면 합계 출력, 동일표범주상이 건수 출력
- `_264_triage.md` 존재 + 진짜충돌/동의어 집계 + 00545716 케이스 포함

## 7. 완료 보고 양식
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: 항목별 [x]/[ ] + 증거 원문
변경 파일: 경로 목록
최종 검증 결과: §6 출력 원문
미완·우회·우려: 정직하게(없으면 "없음")
