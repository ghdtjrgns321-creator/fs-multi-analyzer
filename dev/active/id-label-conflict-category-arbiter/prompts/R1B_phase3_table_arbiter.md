# 작업: 충돌 해소 1단 — 표 호환성 심판 (Phase 3, mapper + pipeline)

## 1. 목표
- map_row가 충돌 시 label 후보를 함께 기록하게 하고, pipeline에 `_arbitrate_conflicts`(1단 표 호환성)를 신설해 기존 `_apply_statement_guard`를 흡수·확장한다.
- 성공 기준: ①기존 전체 테스트 무회귀(`uv run pytest tests/ -v`) ②합성 단위검증으로 "label만 표호환이면 label 채택, id만 표호환이면 id 유지, 둘다 비호환이면 기타중요계정 강등(기존 statement_guard 동작 보존)" 확인 ③MappingResult 소비처 ripple-search로 파급 0 확인.

## 2. 컨텍스트
- 읽어야 할 파일(수정 전 필수): `src/normalize/mapper.py`(MappingResult·map_row), `src/normalize/pipeline.py`(`_apply_statement_guard` line~89, `_STATEMENT_COMPATIBLE`, normalize_raw_file 호출체인 line~84, `_canonical_score`)
- 설계 출처: `dev/active/id-label-conflict-category-arbiter/id-label-conflict-category-arbiter-plan.md` "2단 심판 로직"·"충돌 해소 로직의 위치"
- 배경: 현재 map_row(line 49~58)는 충돌 시 id-canonical 채택 + ID_LABEL_CONFLICT 플래그만. `_apply_statement_guard`는 canonical.statement≠sj_div면 기타중요계정으로 드롭(대안 채택 안 함). **이번 작업은 1단(표 호환성)까지만** — 2단(범주 중재)은 다음 단계라 손대지 않는다.

## 3. 설계 (이대로 구현 — 임의 변경 금지)
### 3-1. mapper.py
- `MappingResult`에 필드 2개 추가: `label_canonical: str = ""`, `label_statement: str = ""`.
- `map_row` 충돌 분기(현재 line 56~57, by_alias.name != account.name): **id 채택은 그대로 유지**하되 `label_canonical=by_alias.name`, `label_statement=by_alias.statement`를 MappingResult에 함께 기록. 비충돌 행은 두 필드 빈 문자.
- `map_change_row`(SCE)는 이번에 손대지 않음.

### 3-2. pipeline.py
- `_arbitrate_conflicts(frame)` 신설. 충돌 행(label_canonical 비어있지 않음)에 대해 1단:
  - `id_ok = compatible(sj_div, canonical_statement)`, `label_ok = compatible(sj_div, label_statement)` (compatible = sj==statement 또는 `_STATEMENT_COMPATIBLE` 쌍).
  - `label_ok and not id_ok` → **label 채택**(canonical←label_canonical, mapping_status 사유 기록 예: `id_label_conflict:table_label`).
  - `id_ok and not label_ok` → id 유지(현 동작).
  - `not id_ok and not label_ok` → 기타중요계정 강등(**기존 _apply_statement_guard 드롭 동작과 동일**).
  - `id_ok and label_ok` → id 유지(2단은 다음 단계 — 이번엔 변경 없음).
  - 비충돌 행: 기존 statement_guard와 동일하게 canonical.statement≠sj_div면 강등(흡수).
- `_apply_statement_guard` 로직을 `_arbitrate_conflicts`에 흡수하고 normalize_raw_file 호출체인(line 84)을 `_arbitrate_conflicts`로 교체. 호출 순서 보존: arbitrate → dedupe_statement → dedupe_canonical.
- **MappingResult 필드 추가에 따라 frame에 label_canonical/label_statement 컬럼이 실리도록** map 결과 → frame 변환부(line 56 부근) 확인·반영.

설계가 현장과 안 맞으면 멈추고 STATUS: NEEDS_CONTEXT. 임의 변경 금지.

## 4. 단계 체크리스트 (순서 고정)
- [ ] Step 1: mapper.py·pipeline.py 읽고 MappingResult·map_row 충돌분기·_apply_statement_guard·_STATEMENT_COMPATIBLE·호출체인 인용
- [ ] Step 2: **ripple-search** — `MappingResult` 소비처 전수(`grep -rn "MappingResult\|\.mapping_status\|label_canonical" src/`) → 필드 추가가 깨는 곳 없는지 목록화
      증거: grep 결과 + "파급 영향 없음/조치" 판단
- [ ] Step 3: mapper.py 수정(필드 2개 + 충돌분기 기록) → 증거: `git diff src/normalize/mapper.py`
- [ ] Step 4: pipeline.py 수정(_arbitrate_conflicts 신설 + statement_guard 흡수 + 호출체인 교체) → 증거: `git diff src/normalize/pipeline.py`
- [ ] Step 5: 합성 단위검증 — 4분면(label만맞음/id만맞음/둘다맞음/둘다비호환) 각각 1행 합성 DataFrame으로 _arbitrate 결과 확인
      증거: 작성한 검증 스니펫 + 출력(각 분면의 최종 canonical)
- [ ] Step 6(마지막): 전체 무회귀 → 증거: `uv run pytest tests/ -v` 출력(passed/failed 수)

## 5. 금지 사항 (1건이라도 위반 시 전체 실패)
- 하드코딩: 특정 corp·연도·계정명을 _arbitrate 분기에 박지 말 것. 판정은 sj_div·statement 비교로만.
- 2단(범주 중재) 구현 금지 — 이번은 1단(표 호환성)까지. category 필드 참조 금지.
- 기존 statement_guard 드롭 동작 약화 금지(둘다 비호환 케이스가 여전히 기타중요계정으로 강등돼야).
- 테스트 약화 금지(skip/xfail/assert삭제/기대값을 출력에 맞춤).
- 범위 밖 수정 금지: `src/normalize/mapper.py`·`src/normalize/pipeline.py` 외 변경 금지. config.py·yaml 손대지 말 것.
- map_change_row(SCE) 수정 금지.

## 6. 최종 검증 (완료 선언 전 필수)
- `uv run pytest tests/ -v` → 기대: 기존 baseline과 동일 passed(회귀 0). 실패 시 DONE 금지.
- Step 5 합성검증 → 기대: label만맞음→label채택, id만맞음→id, 둘다비호환→기타중요계정.
- ripple-search(Step 2) → 기대: MappingResult 필드 추가가 기존 소비처를 깨지 않음(기본값 빈문자라 하위호환).

## 7. 완료 보고 양식
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
체크리스트: 항목별 [x]/[ ] + 증거 원문(명령+출력 붙여넣기)
변경 파일: 경로 목록(변경한 것만)
최종 검증 결과: §6 명령별 출력 원문
미완·우회·우려: 정직하게 전부(없으면 "없음")
신뢰 규칙: 부분실패의 정직 보고(BLOCKED/CONCERNS)는 정상 경로. 거짓 DONE은 리뷰게이트 재현에서 드러남.
