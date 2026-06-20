# id_label_conflict 범주 중재 — Context & Decisions

## Status
- Phase: 설계 완료(미착수)
- Progress: 0 / 6 phases
- Last Updated: 2026-06-14

## Key Files

**Modified(예정)**:
- `src/normalize/mapper.py` - `MappingResult`에 label 후보 필드 추가, `map_row`가 두 후보 기록
- `src/normalize/pipeline.py` - `_apply_statement_guard` → `_arbitrate_conflicts` 확장(1·2단 심판)
- `src/normalize/config.py` - `CanonicalAccount.category` 필드 + 로더
- `config/canonical_accounts.yaml` - 충돌 등장 canonical에 `category` 키 부여

**New(예정)**:
- `data/backtest/_conflict_canonical_inventory.py` - 충돌 등장 canonical 집합 추출
- `data/backtest/_derive_category_seed.py` - category 자동 도출 시드

**참조(수정 안 함)**:
- `data/backtest/_is_cf_arithmetic.py` - 산술검산(3단), 사후 게이트로 유지
- `data/backtest/_holistic_chunks.json` - corpus 101사/383cy 타깃 정의

## Key Decisions

1. **충돌 해소를 후처리 pass로(map_row 내부 아님)** (2026-06-14)
   - Rationale: 산술검산(3단)은 회사연도×fs_div 집계 필요 → row 단위 불가. 이미 `_apply_statement_guard`가 후처리에서 sj 심판 중이라 그것을 확장하는 게 중복 없는 위치.
   - Alternatives: map_row 안에서 1·2단만 처리(고려) → 산술검산과 분리되고 statement_guard와 로직 중복.
   - Trade-offs: MappingResult에 후보 필드 추가 필요(스키마 파급) vs 로직 일원화.

2. **표 호환성보다 범주 중재가 진짜 오매핑 해소의 본체** (2026-06-14)
   - Rationale: 데이터 계측 결과 진짜 오매핑(~10건)은 거의 전부 동일표(같은 sj_div). 표 호환성만으론 못 잡힌다. 동일표 충돌을 거친범주로 가르면 진짜충돌 후보가 5,439 → 264로 좁혀진다.
   - Alternatives: 표 종류로 가르기(현흐=영어/나머지=한글) → 현흐 안에 둘 다 섞여 실패(데이터 확인).

3. **범주는 전수 2,028개가 아니라 충돌 등장 canonical에만 우선 부여** (2026-06-14)
   - Rationale: CF 활동분류 자동 도출률 낮음(562/778 미분류). 전수 정밀 부여는 과투자. 중재에 실제 등장하는 부분집합만.
   - Trade-offs: 신규 충돌이 미부여 canonical을 건드리면 id 유지(안전한 기본값)로 폴백 → 점진 확장.

4. **id 유지가 기본, label은 명확한 근거 있을 때만** (2026-06-14)
   - Rationale: label 맹신은 CF 운전자본 수백 라인 오염. 범주 도출 노이즈로 거짓양성(정부보조금수취 vs 수령) 존재 확인 → 보수적 채택.

5. **by_alias=None 760건은 별도 트랙(Phase 6)** (2026-06-14)
   - Rationale: 현재 코드가 충돌 자체를 감지 못하는 config gap. 중재 로직과 별개 문제(00148504 발행사채 등). 섞으면 검증 혼란.

## Known Issues

- **범주 거짓양성**: 동일표 범주상이 264건 중 일부는 범주 도출 노이즈로 인한 동의어(정부보조금수취[cf_financing?] vs 수령[cf_adjust?]). Phase 1 수기 분류로 거짓양성 규모 확정 전까지 범주 채택 범위 미확정.
- **SCE 이중 정책**: 메인 `map_row`(id-first) vs `sce_components`(label-first). 메인 SCE 1,038건을 _arbitrate가 처리하면 두 경로 수렴 가능하나 영향 미측정.
- **MappingResult 스키마 파급**: 후보 필드 추가 시 소비처 점검 필요(ripple-search 대상).

## 측정 근거(corpus 383cy, 본 설계에서 직접 계측)

| 지표 | 값 |
|------|----|
| id_label_conflict 발화 행 | 9,285 |
| 두 canonical statement 상이(표 호환성 트랙) | 3,086 |
| └ label만 sj와 맞음(표 호환성이 구제) | 84 |
| 두 canonical statement 동일(범주 트랙) | 5,439 |
| └ 거친범주 동일=동의어(무변경) | 5,175 |
| └ 거친범주 상이=진짜충돌 후보 | 264 |
| by_alias=None(충돌 미감지, 별도 트랙) | 760 |
