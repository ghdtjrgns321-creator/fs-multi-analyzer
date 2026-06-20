# 동의어 canonical dedup + per-company 온보딩 QA 게이트 — 전략 계획

## Executive Summary

id_label_conflict 오매핑의 **원인 제거**(갈래1)와 **잔여 이탈 흡수**(갈래2)를 함께 설계한다.
갈래1은 config에 같은 뜻 계정이 별도 canonical로 중복 등록된 것(동의어 중복)을 1개로 통합해
충돌 자체를 소멸시킨다(예: `FVPL금융자산`↔`당기손익-공정가치측정금융자산`). 갈래2는 새 회사가
들어올 때 FS 분석 전에 정규화 품질을 검사·교정하는 표준 게이트를 세우고, 현재 backtest에
산발한 검사 스크립트(`_is_cf_arithmetic.py`·`_conflict_canonical_inventory.py`·`_p1_company_review.py`
등)를 게이트의 정식 단계로 승격한다. 두 갈래 모두 사람 검수를 전제하되, 자동 후보 추출과
회귀 가드(백테스트 recall 5/6·known 무회귀·SCE/IS-CF 검산 baseline)로 안전망을 깐다.

## 선행 작업과의 관계 (중복 방지)

기존 작업 `dev/active/id-label-conflict-category-arbiter/`는 충돌을 **런타임에 심판**한다
(표 호환성 `_arbitrate_conflicts` + 범주 중재). 그 중 cross-statement(①)는 이미 구현·게이트
통과(`src/normalize/pipeline.py:_arbitrate_conflicts`). 본 작업은 **다른 두 갈래**다:

| | 선행 작업(category-arbiter) | 본 작업(synonym-dedup-onboarding-gate) |
|---|---|---|
| 접근 | 충돌을 런타임 심판(채택 결정) | 충돌 원인 제거(config) + 잔여 흡수(게이트) |
| 대상 | ① cross-statement(완료) + 동일표 범주상이 264 | ② 동의어 canonical 중복(가장 많음) + ③ 진짜오매핑 흡수 |
| 산출 | `_arbitrate_conflicts` 확장 | yaml dedup + 온보딩 게이트 파이프라인 |
| 핵심 자산 | `_conflict_canonical_inventory.py` | 동일 + `_is_cf_arithmetic.py`·`_p1_company_review.py`·`_HOLISTIC_AUDIT_PROMPT.md` |

`_arbitrate_conflicts`(표 호환성 심판)는 **무회귀 유지**한다. dedup으로 충돌이 줄어도 남는
충돌은 여전히 이 심판이 처리한다. 두 작업은 충돌 모집단을 양쪽에서 줄이는 상보 관계다.

## 측정으로 확정된 사실 (재측정 불필요)

- 매퍼 `src/normalize/mapper.py:map_row`: account_id 1순위 채택. id-canonical ≠ label-canonical이면
  `id_label_conflict` 플래그 + 두 후보 기록(`label_canonical`/`label_statement`).
- 충돌 3종류: ① cross-statement(해결됨) · ② 동의어 canonical 중복(가장 많음) · ③ within-category
  진짜오매핑(소수).
- **②와 ③을 mechanical하게 분리하는 systematic 신호 없음**(측정 확정): coarse category·한글 핵심명사
  lexical·영문 taxonomy-id 자카드 3종 모두 실패. 따라서 ③은 case-by-case이며 온보딩 게이트로 흡수.
- 규모: same-statement 충돌 distinct canonical **592쌍 / 4,806행**(대다수 동의어, 소수 진짜오매핑).
- 동의어 예시(통합 대상): `FVPL금융자산`↔`당기손익-공정가치측정금융자산`,
  `순확정급여부채`↔`퇴직급여부채`, `상각후원가측정금융자산`↔`상각후원가금융자산`.
- 세분화 예시(통합 **금지**): `유동리스부채`↔`리스부채`, `비유동FVOCI금융자산`↔`FVOCI금융자산`
  (id가 더 정확 — 통합 시 유동/비유동 정보 손실).

## Current State (코드 구조)

### config (config/canonical_accounts.yaml, 11k줄, 한글)
- `canonical_accounts`: name → {statement, account_ids[], aliases[], is_subtotal, category}.
- canonical name이 곧 키(중복 통합 = 키 병합 + account_ids/aliases 흡수 + 중복 키 삭제).
- `src/normalize/config.py:load_canonical_accounts`가 이 dict를 `CanonicalAccount`로 로드.
  `AccountMapper.__init__`이 `_by_id`(account_id→account)·`_by_alias`(normalize_label→account) 빌드.

### 매퍼/파이프라인
- `map_row`: id 1순위 → 충돌 시 두 후보 기록.
- `_arbitrate_conflicts`(pipeline.py): 충돌 행을 sj_div 표 호환성으로 심판(label 채택/id 유지/강등).
- `_dedupe_canonical_rows`: 같은 canonical 다중 행을 대표 1행 + 비대표 강등(소실 방지).
- 두 canonical을 하나로 합치면(dedup) `_by_id`·`_by_alias`가 같은 account를 가리켜 **map_row에서
  충돌 자체가 발생하지 않는다**(account.name 동일 → 플래그 미발화).

### 기존 검사 자산 (backtest 산발 — 게이트로 승격 대상)
| 스크립트 | 역할 | 게이트 단계 |
|---|---|---|
| `_conflict_canonical_inventory.py` | 충돌 인벤토리(sj 4분면·동일표 범주상이 덤프) | G2 충돌 인벤토리 |
| `_is_cf_arithmetic.py` | IS/CF 정의식 산술검산 | G3 산술검산 |
| `_f1_signal_dangling.py` | 신호엔진 canonical dangling(Layer A) | G5 신호 무결성 |
| `_p1_company_review.py` | 회사연도 전차원 dump(A~I 섹션) | G1 기계검사 + G6 LLM 입력 |
| `_HOLISTIC_AUDIT_PROMPT.md` | 9렌즈 LLM 통독 프롬프트 | G6 LLM 홀리스틱 |

### 회귀 가드 진입점 (검증 명령)
- 재정규화: `PYTHONPATH=. uv run python -m src.normalize.renormalize_all --force [corp]`
- 백테스트: `PYTHONPATH=. uv run python -m src.backtest.run_backtest`(recall 5/6)
- 산술검산: `PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py`
- 충돌수: `PYTHONPATH=. uv run python data/backtest/_conflict_canonical_inventory.py`
- 단위/검산: `uv run pytest tests/ -v`

## Proposed Solution

### 갈래1: config 동의어 canonical dedup

**핵심 동작**: 같은 뜻 canonical 2개+를 1개로 통합. 생존 canonical에 중복본의 account_ids·aliases를
흡수하고 중복본 키를 제거한다. 통합 후 id·label 둘 다 같은 canonical을 가리켜 **충돌 소멸**.

**동의어쌍 식별** (lexical·id 유사도 다 실패 → 사람 검수 전제 + 보수적 자동 후보 추출):
1. 자동 후보 추출(`_dedup_candidates.py` 신설): `_conflict_canonical_inventory.py`가 덤프한
   동일표(same-statement) 충돌 쌍 592개를 입력으로, 각 쌍을 3분류 시드로 라벨링.
   - **세분화 후보(통합 금지)**: 한 canonical name이 다른 것의 부분문자열이고 차이가 유동/비유동·
     장기/단기·순/총 접두사뿐이면 세분화로 시드(보수적 — 통합 후보에서 제외). 규제 §세분화 보존.
   - **진짜오매핑 후보**: `_264_triage.md`의 진짜충돌 9쌍 패턴(수익↔이익소계, 조정↔소계,
     OCI↔법인세효과)에 해당하면 dedup 아님 → 온보딩 게이트(③) 트랙으로 분리.
   - **동의어 후보(통합 대상)**: 위 둘 다 아닌 나머지 = 사람 검수 큐.
2. 사람 검수(3택): 각 쌍을 `synonym`(통합) / `narrower`(세분화 보존) / `mistag`(진짜오매핑) 으로
   판정. 판정 결과를 `_dedup_decisions.yaml`(작업 산출물)에 기록.

**생존자 선정 규칙** (검수 시 적용할 우선순위 — 결정론):
1. account_ids가 더 많은 쪽(매핑 커버리지 큰 쪽 생존).
2. 동수면 ifrs-full_ 표준 id를 가진 쪽(IFRS 정식 택소노미 우선).
3. 그래도 동수면 name이 더 일반적인 쪽(접두·수식어 적은 쪽 — 표시명 안정).
4. 검수자가 위 규칙에 반하는 선택 시 사유를 decisions에 기록(규칙 우선, 예외는 명시).

**yaml 흡수 방식 (인코딩 안전 — CLAUDE.md §4)**:
- 11k줄 한글 yaml 전체 재작성·formatter 금지. **minimal edit만**:
  - 생존 canonical 블록의 `account_ids:`·`aliases:` 리스트에 중복본의 항목을 추가(Edit 도구로
    해당 블록만 수정, 중복 제거).
  - 중복본 canonical 키 블록 전체를 삭제(Edit로 그 블록만 제거).
- 적용 스크립트(`_apply_dedup.py` 신설)는 `_dedup_decisions.yaml`을 읽어 **편집 지시 목록**을
  출력하고, 실제 yaml 수정은 ruamel.yaml round-trip(주석·순서·따옴표 보존) 또는 Edit 도구로
  블록 단위 수행. (신규 패키지 ruamel.yaml 필요 시 §8 사용자 확인 — 대안: Edit 수동 적용.)
- 적용 후 mojibake 0 검증(`grep -c '\\ufffd'` = 0), yaml 파싱 성공, canonical 수 = 이전 − 통합건수.

**충돌 소멸 측정**:
- dedup 전후 `_conflict_canonical_inventory.py` 재실행 → `id_label_conflict` 발화 행수 감소 확인.
- 기대: 동의어 통합분만큼 same-statement 충돌 감소, 세분화·진짜오매핑은 불변.

### 갈래2: per-company 온보딩 QA 게이트

**위치**: raw 수집 → 정규화 → **[QA 게이트]** → FS 분석(Phase2). 게이트를 통과해야 분석 진입.

**게이트 단계** (기존 자산 부품화 — 중복 구현 금지):

```
G0  입력: corp_code, year(s). 정규화 산출물(analysis.duckdb) 존재 전제.
G1  기계검사 (floor)        ← _p1_company_review.py §0 완결성 + §B/§F 검산
      필수 테이블 존재·비어있지 않음(normalized_financials·sce·notes), BS 항등식, SCE roll-forward.
G2  충돌 인벤토리            ← _conflict_canonical_inventory.py (회사 스코프)
      이 회사연도의 id_label_conflict 행 수집·sj 4분면 분류. dedup으로 줄어든 뒤 남은 충돌만.
G3  산술검산                ← _is_cf_arithmetic.py (회사 스코프)
      IS1(매출총이익)·IS_tax·CF 정의식. 경성 FAIL이면 이탈 후보.
G4  표 호환성 심판(자동)     ← 기존 _arbitrate_conflicts (정규화에 이미 내장)
      G2 충돌 중 표 비호환은 정규화가 이미 처리. 게이트는 결과 인벤토리만 확인(재구현 아님).
G5  신호 무결성             ← _f1_signal_dangling.py Layer A (전사 1회, 회사 무관)
      dedup으로 canonical name이 바뀌면 신호엔진 참조가 dangling되는지. dedup 직후 필수.
G6  LLM 홀리스틱 통독        ← _p1_company_review.py dump + _HOLISTIC_AUDIT_PROMPT.md 9렌즈
      G1~G5가 OK 도장 찍은 것 속 잔여 이탈(의미 오매핑·소실·이질병합)을 LLM이 식별.
G7  이탈 → quirk 등록        ← config quirk 스키마(신설)
      식별된 회사 고유 이탈을 alias/override로 등록.
G8  재정규화 → G1 반복       ← renormalize_all --force <corp>
      이탈 0 될 때까지 반복.
G9  통과 → FS 분석 진입
```

**반복 종료조건 (게이트 통과기준)**:
- G1 기계검사: 완결성 FAIL 0, BS 항등식 잔차 ≤ tol, SCE 검산 PASS 또는 명시적 SKIP 사유.
- G3 산술검산: 경성 위반 0(또는 위반이 원공시 특성으로 LLM이 판정·기록).
- G6 LLM: `[P1결함]` 0건(P1결함은 정규화 수정 대상 → quirk 또는 일반패턴으로 해소).
  `[원공시]`·`[P2후보]`는 통과 허용(분석 단계로 인계).
- **최대 반복 N=3**(무한루프 방지). 3회 내 P1결함 0 미달성이면 수동 에스컬레이션(일반패턴 승격 검토).

**company quirk config 스키마 (신설 — 하드코딩 금지, 데이터)**:
`config/company_quirks.yaml` 신설.
```yaml
# 회사 고유 이탈 교정. corp_code는 데이터 키(코드 분기 아님).
# 일반 패턴으로 승격 가능하면 canonical_accounts.yaml로 이관하고 여기서 제거.
company_quirks:
  "00204226":               # corp_code (데이터 키)
    "2022":                 # year (선택 — 생략 시 전 연도)
      account_overrides:
        - account_id: dart_CurrentPortionOfConvertibleBonds
          label: 유동성장기부채
          force_canonical: 유동성장기차입금   # id-first를 이 회사연도만 label로 덮음
          reason: "신고자가 전환사채 id에 일반 유동성장기부채 라벨 신고(원공시 오태깅)"
      alias_additions:       # 이 회사 고유 표기를 표준 canonical alias로 흡수
        - canonical: 매출
          alias: 영업수익
```
- 로더(`config.py`에 `load_company_quirks` 신설), 적용은 `map_row` 이후 후처리 pass
  (`_apply_company_quirks` 신설, `_arbitrate_conflicts` 다음). corp_code·year는 데이터 인자로 흐름.

**일반 패턴 승격 경로 (표 호환성처럼)**:
- 같은 quirk가 **3개 이상 회사**에서 반복되면(YAGNI: 1~2회는 quirk 유지) 일반 패턴으로 승격:
  - `alias_additions` 반복 → canonical_accounts.yaml의 해당 canonical aliases에 추가(전사 적용).
  - `account_overrides` 반복 → `_arbitrate_conflicts`의 일반 규칙 또는 새 심판 차원으로 흡수.
- 승격 시 company_quirks.yaml에서 제거(quirk는 임시·예외만 보유). 승격 판단은 `_quirk_promote_scan.py`
  (신설)가 회사 수를 세어 후보 제시 → 사람 결정.

## Implementation Phases

### Phase 1: dedup 후보 분류 (M, 1d)
**Goal**: 592 same-statement 충돌 쌍을 synonym/narrower/mistag 3분류 + 생존자 선정.
**Tasks**:
- [ ] `_dedup_candidates.py` 신설 — `_conflict_canonical_inventory.py` 덤프 입력, 3분류 시드 생성
  - File: `data/backtest/_dedup_candidates.py`
  - Details: same-statement 쌍 592개 로드. 부분문자열+유동/비유동/순/총 접두 차이=narrower 시드,
    `_264_triage.md` 진짜충돌 패턴 매칭=mistag 시드, 나머지=synonym 후보. 생존자 규칙(account_ids
    개수→ifrs-full 우선→일반명) 자동 계산해 제안.
  - Acceptance: `_dedup_candidates.json` 출력, 592쌍이 3분류로 라벨링됨. synonym 후보 수 출력.
  - Size: M
- [ ] synonym 후보 사람 검수 → `_dedup_decisions.yaml` 작성
  - File: `dev/active/synonym-dedup-onboarding-gate/_dedup_decisions.yaml`
  - Details: 각 쌍 synonym/narrower/mistag 확정 + 생존 canonical 명시. 규칙 위반 선택은 reason 기록.
  - Acceptance: 592쌍 전부 판정(미판정 0). mistag 쌍은 게이트 트랙으로 분리 표기.
  - Size: L

### Phase 2: dedup 적용 (M, 1d)
**Goal**: 동의어 통합을 yaml에 인코딩 안전하게 반영, 충돌 소멸 측정.
**Tasks**:
- [ ] `_apply_dedup.py` 신설 — decisions 읽어 yaml 편집 지시 생성
  - File: `data/backtest/_apply_dedup.py`
  - Details: synonym 판정 쌍만 처리. 생존 canonical에 흡수할 account_ids/aliases 목록 + 삭제할
    중복 키 목록 출력. ruamel.yaml round-trip 가능 시 직접 수정(주석·순서 보존), 불가 시 Edit 지시.
  - Acceptance: 편집 지시 목록 출력. 한 쌍 dry-run으로 흡수 결과 미리보기.
  - Size: M
- [ ] yaml dedup 적용 (minimal edit, 인코딩 가드)
  - File: `config/canonical_accounts.yaml`
  - Details: 생존 블록 account_ids/aliases에 흡수분 추가, 중복 키 블록 삭제. Edit 도구 블록 단위.
  - Acceptance: yaml 파싱 성공, canonical 수 = 이전 − 통합건수, mojibake 0(`grep -c '\\ufffd'`=0).
  - Size: L
- [ ] 충돌 소멸 측정
  - 검증: `PYTHONPATH=. uv run python data/backtest/_conflict_canonical_inventory.py`
  - Details: dedup 후 same-statement 충돌 행수가 통합분만큼 감소. 세분화·진짜오매핑 불변 확인.
  - Acceptance: 동의어 통합 쌍이 충돌 인벤토리에서 사라짐. narrower 쌍은 그대로 남음.
  - Size: S

### Phase 3: dedup 회귀 검증 (M, 1d)
**Goal**: dedup이 baseline을 깨지 않음 확인.
**Tasks**:
- [ ] 전수 재정규화
  - 검증: `PYTHONPATH=. uv run python -m src.normalize.renormalize_all --force`
  - Acceptance: error 0, renorm 완료.
  - Size: M
- [ ] 신호 dangling 검사(dedup으로 죽은 canonical 참조 없는지)
  - 검증: `PYTHONPATH=. uv run python data/backtest/_f1_signal_dangling.py`
  - Acceptance: Layer A dangling 0(통합으로 사라진 canonical을 신호엔진이 참조하면 FAIL — alias로 보강).
  - Size: S
- [ ] 백테스트 recall 5/6 + IS/CF 산술검산 + known 무회귀
  - 검증: `PYTHONPATH=. uv run python -m src.backtest.run_backtest` ·
    `PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py` · `uv run pytest tests/ -v`
  - Acceptance: recall 5/6 유지, 산술검산 악화 0, pytest green.
  - Size: M
- [ ] 동의어 통합 케이스 재현(예: FVPL금융자산 통합 후 두 라벨 모두 같은 canonical)
  - 검증: `PYTHONPATH=. uv run python data/backtest/_p1_company_review.py <corp> <year>`
  - Acceptance: 통합 canonical의 §I 병합 가시화에서 두 raw label이 한 canonical로 정상 수렴(충돌 플래그 없음).
  - Size: M

### Phase 4: 온보딩 게이트 골격 + quirk 스키마 (M, 1d)
**Goal**: 게이트 단계 인터페이스와 company quirk config 로더/적용 신설.
**Tasks**:
- [ ] `config/company_quirks.yaml` 신설(빈 스키마 + 주석 문서)
  - File: `config/company_quirks.yaml`
  - Details: account_overrides·alias_additions 스키마. corp_code/year 데이터 키.
  - Acceptance: yaml 파싱 성공, 예시 1건(주석 처리) 포함.
  - Size: S
- [ ] `load_company_quirks` 로더
  - File: `src/normalize/config.py`
  - Details: company_quirks.yaml → dict[corp][year] = overrides/aliases. 기존 로더 패턴 준수.
  - Acceptance: 빈 파일·미존재 시 빈 dict 반환(안전). 예시 로드 단위테스트.
  - Size: S
- [ ] `_apply_company_quirks` 후처리 pass
  - File: `src/normalize/pipeline.py`
  - Details: `_arbitrate_conflicts` 다음 호출. corp_code/year에 매칭되는 override는 canonical 덮음,
    alias_additions는 그 회사연도 매핑 시 흡수. corp_code는 인자(코드 분기 하드코딩 금지).
  - Acceptance: quirk 없는 회사는 무변경(통과). 예시 회사 override 적용 단위테스트.
  - Size: M

### Phase 5: 게이트 단계 부품화 + 러너 (M, 1d)
**Goal**: 기존 스크립트를 게이트 단계로 승격, 단일 진입점 러너.
**Tasks**:
- [ ] 게이트 러너 `onboarding_gate.py` 신설
  - File: `src/normalize/onboarding_gate.py`
  - Details: G1~G6을 순차 호출. 각 단계 기존 스크립트의 핵심 함수를 import해 회사 스코프로 실행
    (재구현 금지 — `_p1_company_review.py`·`_is_cf_arithmetic.py`·`_conflict_canonical_inventory.py`
    의 함수 재사용). 결과를 `gate_report` dict로 집계. P1결함 0 + 기계검사 PASS면 통과.
  - Acceptance: `PYTHONPATH=. uv run python -m src.normalize.onboarding_gate <corp> <year>` 실행 →
    단계별 PASS/FAIL + 이탈 목록 출력. 기존 backtest 회사로 PASS 재현.
  - Size: L
- [ ] G6 LLM 통독 연결(dump + 프롬프트)
  - File: `src/normalize/onboarding_gate.py`
  - Details: `_p1_company_review.py` dump 생성 → `_HOLISTIC_AUDIT_PROMPT.md` 9렌즈로 LLM 호출
    (subagent 위임). 산출 findings를 P1결함/원공시/P2후보로 파싱.
  - Acceptance: 한 회사연도에 LLM findings 생성, P1결함 카운트가 종료조건에 반영.
  - Size: M
- [ ] 반복 루프 + 종료조건(N=3)
  - File: `src/normalize/onboarding_gate.py`
  - Details: G7 quirk 등록 후 G8 재정규화 → G1 재실행. P1결함 0 또는 N=3 도달 시 종료.
  - Acceptance: 이탈 있는 회사가 quirk 등록 후 재정규화로 이탈 0 수렴(시뮬레이션 케이스).
  - Size: M

### Phase 6: 일반 패턴 승격 경로 (S, 0.5d)
**Goal**: 반복 quirk를 전사 패턴으로 승격하는 스캐너.
**Tasks**:
- [ ] `_quirk_promote_scan.py` 신설
  - File: `data/backtest/_quirk_promote_scan.py`
  - Details: company_quirks.yaml 전수 스캔. 같은 alias_addition/override가 3개+ 회사에서 반복되면
    승격 후보로 출력. canonical_accounts.yaml 이관 편집 지시 생성.
  - Acceptance: 반복 quirk 3회+ 후보 목록 출력. 미달(1~2회)은 quirk 유지로 표기.
  - Size: M

## Risk Assessment

- **High: dedup 과통합으로 세분화 손실**(유동리스부채↔리스부채를 동의어로 오판) -
  Mitigation: `_dedup_candidates.py`가 부분문자열+유동/비유동/순/총 접두 차이를 narrower로 자동
  시드(통합 후보 제외). 사람 검수 3택에서 narrower 확정. 회귀: dedup 후 `_p1_company_review.py` §I로
  유동/비유동 구분 보존 확인.
- **High: 신호엔진 dangling**(통합으로 canonical name 사라지면 신호 조용히 죽음) -
  Mitigation: 생존자 선정 시 신호엔진 참조 canonical(`_f1_signal_dangling.py`의 CODE_HARDCODED·
  playbook 참조)을 생존자로 우선. dedup 직후 G5 dangling 검사 필수(Layer A 0).
- **Medium: 게이트 LLM 의존(비용·확률성)** - Mitigation: G1~G5 결정론 검사가 floor(LLM 없이도
  대부분 이탈 포착). G6 LLM은 잔여만. N=3 캡으로 비용 상한. P1결함 0 미달 시 수동 에스컬레이션.
- **Medium: quirk 남용으로 일반화 회피**(특수 케이스를 quirk로만 쌓음) -
  Mitigation: `_quirk_promote_scan.py`로 3회+ 반복 quirk를 주기적 승격 강제. quirk는 임시·예외만.
- **Low: yaml 인코딩 손상** - Mitigation: minimal edit, mojibake 0 검증, ruamel round-trip 또는 Edit
  블록 단위. 전체 재작성·formatter 금지(§4).

## Success Metrics

- dedup: 동의어 통합 쌍이 `_conflict_canonical_inventory.py` 충돌 인벤토리에서 소멸. 세분화·진짜오매핑
  불변. 백테스트 recall 5/6·known·SCE/IS-CF 검산 무회귀. mojibake 0.
- 게이트: 기존 backtest 회사로 게이트 PASS 재현. 이탈 있는 회사가 quirk 등록 후 이탈 0 수렴.
- 신호 dangling 0(Layer A).
- 진짜오매핑(③) 케이스가 quirk 또는 일반패턴으로 해소(00545716 영업수익→매출 등).

## Dependencies

- Code: 갈래1(Phase 1~3)은 갈래2(Phase 4~6)의 선행(dedup으로 충돌 모집단 축소 후 게이트가 잔여 처리).
  Phase 4(quirk 스키마)는 Phase 5(게이트 러너 G7)의 선행.
- 자산: `_arbitrate_conflicts`(선행 작업 산출, 무회귀)·기존 backtest 스크립트(부품화 대상).
- External: 없음(재수집 불필요, 기존 raw로 재정규화). G6 LLM은 OPENAI/GOOGLE API(기존 환경변수).
- 신규 패키지: ruamel.yaml(yaml round-trip 보존 — 선택, 미설치 시 Edit 수동. §8 사용자 확인 필요).
