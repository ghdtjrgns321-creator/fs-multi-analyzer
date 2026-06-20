# id_label_conflict 범주 중재 — Task Checklist

## Progress Summary
0 / 20 tasks complete (0%)

## Phase 1: 측정·범위 확정 (3/3) ✅ R1-A 리뷰게이트 통과

- [x] 충돌 쌍 distinct canonical 집합 추출 — `_conflict_canonical_inventory.py` + `_conflict_pairs.json`
  - ★실측 **N=964**(기대 <600 초과). 범주 부여 대상이 plan 추정보다 많음 → Phase2 범위 재산정.
  - 단 same-statement 충돌에만 범주 필요(상이표는 표호환성으로 해결) → 실제 태깅 필요 부분집합은 더 작음(R2에서 추출).
- [x] 표 호환성 4분면 — id만2452 / label만266 / 둘다5659 / 불일치148. "label만맞음 266"이 표호환성 신규 구제 대상.
- [x] 동일표 범주상이 triage(`_264_triage.md`) — **진짜충돌 9쌍/48행 + 동의어 74쌍/391행**(보수: 89% 동의어).
  - 핵심 케이스 00545716 영업이익↔매출 = 진짜충돌 확인(직접 재현 검증). 법인세비용↔법인세비용조정 = 동의어 id유지 확인.
  - 거짓양성 경계 6패턴 목록화(지분/채무/증감 어휘로 범주 갈림). CIS 법인세효과 4쌍은 Phase4 산술 교차검증 보류.

## Phase 2: 범주 config 스키마 + 자동 도출 (0/4)

- [x] CanonicalAccount에 category 필드 추가 (R1-C, 리뷰게이트 통과)
  - File: `src/normalize/config.py` line 19 `category: str = ""`
  - Acceptance: pytest test_normalize 71 passed 무회귀 ✓
  - Size: S

- [x] load_canonical_accounts가 category 로드 (R1-C)
  - File: `src/normalize/config.py` line 144 `category=str(values.get("category",""))`
  - Acceptance: 2,028 canonical 전부 category 필드 보유(직접 재현 확인), 미기입 시 빈문자 ✓
  - Size: S

- [ ] category 자동 도출 시드 스크립트
  - File: `data/backtest/_derive_category_seed.py`(신규)
  - Details: plan.md "범주(category) 차원 설계" 표의 판별 기준으로 각 canonical에 시드 category 산출. Phase 1에서 추출한 "충돌 등장 canonical"만 대상. yaml 패치 후보 출력(자동 수정 금지, 사람 검수용).
  - Acceptance: 충돌 등장 canonical 전체에 시드 category 부여, 미분류(애매) 건 별도 표시
  - Size: M

- [ ] 충돌 등장 canonical에 category 수동 검수·기입
  - File: `config/canonical_accounts.yaml`
  - Details: 시드를 사람이 검수해 category 키 기입. Phase 1 거짓양성 패턴(정부보조금 등)은 보수적으로 같은 범주 처리. 한글 인코딩 주의(minimal edit, 전체 재작성 금지).
  - Acceptance: 재로드 후 충돌 등장 canonical 100%에 category 존재, mojibake 0
  - Size: L

## Phase 3: 표 호환성 심판 확장 (3/3) ✅ R1-B 리뷰게이트 통과

- [x] MappingResult에 label 후보 필드 추가 + map_row 두 후보 기록 — mapper.py. frozen dataclass 끝에 빈문자 기본값(하위호환), ripple-search 파급0 확인
- [x] _arbitrate_conflicts 신설(1단 표 호환성) — pipeline.py. label_ok & not id_ok → label 채택(status=id_label_conflict:table_label). 직접재현: CF줄 id측 비호환→label 채택 확인
- [x] _apply_statement_guard 흡수 + 호출부 교체 — pipeline.py. 둘다 비호환→기타중요계정 강등 보존. 203 passed/1 xfailed
  - ※테스트 import 1곳 수정(옛 함수명→_arbitrate_conflicts): 설계 함수흡수 지시 불가피, assert 약화 0(비약화 적응)

## Phase 4: 범주 중재 (2단) (0/2)

- [ ] _arbitrate_conflicts에 2단 범주 비교 추가
  - File: `src/normalize/pipeline.py`
  - Details: 1단에서 둘 다 표 호환일 때, C_id==C_lb면 id 유지, 상이면 label 채택. category는 mapper가 MappingResult에 함께 실어 전달(또는 후처리에서 category 룩업 dict 주입).
  - Acceptance: 00545716 영업수익(C=pl_revenue) vs 영업이익(C=pl_subtotal) → label(매출) 채택
  - Size: M

- [ ] 중재 사유 흔적 기록
  - File: `src/normalize/pipeline.py`
  - Details: 채택 사유(table_only_label / category_conflict_label / same_category_keep_id)를 mapping_status 또는 신규 흔적 컬럼에 기록해 감사 추적.
  - Acceptance: 재정규화 후 사유별 건수 집계 가능
  - Size: S

## Phase 5: 전수 재정규화 + 회귀 검증 (0/5)

- [ ] 전수 재정규화
  - 검증: `PYTHONPATH=. uv run python -m src.normalize.renormalize_all --force`
  - Acceptance: 에러 없이 완료, 충돌 전환 건수 로그 출력
  - Size: M

- [ ] 백테스트 recall 5/6 유지
  - 검증: `PYTHONPATH=. uv run python -m src.backtest.run_backtest`
  - Acceptance: 발굴 recall(positive) 5/6 유지(BACKTEST_REPORT.md)
  - Size: S

- [ ] IS/CF 산술검산 무회귀(3단 사후 게이트)
  - 검증: `PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py`
  - Acceptance: 경성 위반 건수 baseline 이하(악화 0), 범주 중재로 일부 개선 기대
  - Size: S

- [ ] known_cases·SCE 검산 baseline 유지
  - 검증: `uv run pytest tests/ -v`
  - Acceptance: 전체 테스트 통과, SCE roll-forward 검산 무회귀
  - Size: S

- [ ] 진짜 오매핑 ~10건 재현 확인
  - File: `dev/active/id-label-conflict-category-arbiter/_resolution_check.md`(산출물)
  - Details: 00545716/2021·2022(영업수익→매출), 01089378/2025(단기금융상품취득), 01406618/2022(영업창출현금), 00367844, 00688996 재정규화 후 canonical 확인.
  - Acceptance: 각 케이스 canonical이 label 의도대로 수정됨, 값 보존
  - Size: M

## Phase 6: config gap 별도 트랙 (0/1)

- [ ] by_alias=None 충돌 미감지 케이스 alias 보강
  - File: `config/canonical_accounts.yaml`
  - Details: 00148504/2025 "발행사채의 증가"→사채발행 등 760건 중 진짜 오매핑 유발 라벨에 alias 추가(전수 아님, 검토 후보만). 한글 minimal edit.
  - Acceptance: 보강 후 해당 행이 충돌 감지·올바른 canonical 매핑, mojibake 0
  - Size: M

## Deployment Checklist
- [ ] 전수 재정규화 완료(4,777 DB 또는 corpus 범위)
- [ ] 백테스트 recall 5/6, known·SCE baseline 무회귀
- [ ] IS/CF 산술검산 악화 0
- [ ] CF 운전자본 라인 오염 0(재고자산증감 등 회귀테스트)
- [ ] 범주 거짓양성 신규 오매핑 0
- [ ] docs/agent/STATE.md 갱신
