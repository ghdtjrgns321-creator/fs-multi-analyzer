# id_label_conflict 의미 오매핑 — 2단 심판(표 호환성 + 범주 중재) 설계

## Executive Summary

본문 정규화 `map_row`가 `account_id`(영문 표준코드)를 1순위로 채택하는 id-맹신 정책 때문에, 신고자가 XBRL 템플릿을 복붙해 영문 id를 틀린 채 두고 한글 라벨만 실제 항목으로 고친 행에서 의미 오매핑이 발생한다(corpus 101사/383cy 전수 홀리스틱 재검에서 ~10건 확인, 전부 값 보존·의미만 틀림). id를 맹신하면 이 ~10건을 놓치고, label로 뒤집으면 CF 운전자본 라인 수십~수백개가 BS 잔액으로 오염된다. 본 설계는 **case 열거 없이** 충돌을 (1) 표 호환성(sj_div) → (2) 경제적 범주(config 데이터) → (3) 산술검산의 3단 심판으로 자동 중재한다. 최종 저장값은 여전히 2,028개 구체 canonical 중 하나로 보존한다(범주는 심판용 메타데이터일 뿐).

## Current State (데이터로 확정한 사실)

### 매핑 정책 (src/normalize/mapper.py)

- `map_row`(본문 BS/IS/CF/CIS/SCE 전부 — 메인 정규화는 모든 sj_div를 이 함수로 돈다):
  account_id가 `_by_id`에 있으면 무조건 id-canonical 채택(line 49~58). label 정확 alias가
  다른 canonical을 가리키면 `id_label_conflict` 플래그만 남기고 **id를 채택**.
- `map_change_row`(SCE 전용 추가 산출물 `sce_components_company_year` 경로): 충돌 시 **label 우선**(line 77~78).
- 즉 메인 `normalized_financials` 테이블에는 SCE sj_div 행도 포함되며(corpus 1,038건), 이들은 id-first로 처리된다.

### 기존 심판 장치 (src/normalize/pipeline.py)

- `_apply_statement_guard`(line 89~120): 행의 `sj_div`가 매핑된 canonical의 `statement`와
  다르면 매핑 무효화 → `기타 중요 계정`으로 강등. `IS↔CIS`만 호환(`_STATEMENT_COMPATIBLE`).
  **이것이 이미 "표 호환성 심판"의 절반을 수행 중이다** — 단, id-canonical 한쪽만 보고 드롭할 뿐,
  label-canonical로 **승격 채택하지 않는다**(드롭만 하고 대안을 안 쓴다).
- 호출 순서(line 84): `_apply_statement_guard` → `_dedupe_statement_rows` → `_dedupe_canonical_rows`.
- `_canonical_score`(line 257): sj_div==canonical_statement면 6점(최우선) → dedup 대표 선정에 sj 일치 이미 반영.

### 산술검산 (data/backtest/_is_cf_arithmetic.py — 별도 backtest 스크립트)

- IS1(매출총이익=매출−|매출원가|), IS_tax(|순익−세전|=|세금|), CF(기말=기초+순증감) 검산 구현됨.
- 단 이것은 정규화 **사후 감사** 스크립트(DB read-only)이지 정규화 파이프라인 내부 로직이 아니다.

### config 구조 (config/canonical_accounts.yaml — 11,054줄)

- `canonical_accounts`: 2,028개. statement 분포 = BS 601 / IS 38 / CIS 458 / SCE 153 / CF 778.
- account 하위 키: `statement`, `account_ids`, `aliases`, `is_subtotal`. **category 키는 없다(신설 대상)**.

### 충돌 실태 (corpus 383cy 측정 — 본 분석에서 직접 계측)

| 구분 | 건수 | 의미 |
|------|------|------|
| `id_label_conflict` 발화 행 | 9,285 | sj 분포: BS 3,649 / CF 2,649 / CIS 1,529 / SCE 1,038 / IS 420 |
| label에 alias 없음(by_alias=None) | 760 | 현재 코드가 충돌 감지 못함(config gap, 별도 트랙) |
| 두 canonical statement **상이** | 3,086 | 표 호환성(sj_div)으로 갈림 가능 |
| 두 canonical statement **동일** | 5,439 | 표 호환성으로 안 갈림 → 범주 필요 |
| └ 동일표 중 거친범주 **동일**(동의어) | 5,175 | 현 동작 유지(id) — 무변경 대상 |
| └ 동일표 중 거친범주 **상이**(진짜충돌 후보) | 264 | 범주 중재 핵심 타깃 |

**상이표 충돌의 sj_div 4분면**(3,086 중 by_alias 있는 2,686):
- id만 맞음 2,416 / 둘다 맞음 402 / label만 맞음 84 / 둘다 불일치 184.
- 대다수(2,416)는 sj_div가 id-canonical과 일치 → 현 statement_guard가 이미 옳게 유지/드롭.
- **label만 맞음 84건**이 표 호환성 심판이 새로 구제할 핵심(예: SCE행 label "연차배당"→배당변동(SCE)인데 id가 다른 표).

**진짜 오매핑(~10건)은 거의 전부 동일표**임을 케이스 재현으로 확정:
- 00545716/2021·2022: id 영업이익(IS) vs label "영업수익"→매출(IS) — **동일표 IS, 범주 수익 vs 이익소계 상이** → 범주 중재 필요.
- 01406618/2022: id 당기순이익(CF) vs label "영업에서 창출된 현금"→영업창출현금흐름(CF) — **동일표 CF**.
- 00688996/2023: id 사채의발행 vs label "사채의증가"→사채발행 — **동의어**(둘 다 사채발행, 진짜 오매핑 아님).

### 핵심 결론 (설계 방향 확정)

1. **표 호환성만으로는 진짜 오매핑을 못 잡는다** — 진짜 오매핑은 대부분 동일표(같은 sj_div).
2. **범주 중재가 진짜 오매핑 해소의 본체** — 동일표 충돌을 거친범주로 가르면 진짜충돌 후보가 5,439 → 264로 좁혀진다.
3. **표 호환성 심판은 상이표 84건(label만 맞음) 구제 + statement_guard 정밀화**가 역할.
4. **264건 중에도 범주 도출 노이즈로 인한 거짓양성 존재**(정부보조금수취[유출입-] vs 정부보조금수령[기타] = 사실 동의어) → 범주 경계는 보수적으로(과채택 방지) 설계해야 한다.

## Proposed Solution

### 설계 원칙

- **id 유지가 기본(보수)**. 충돌은 "label로 뒤집을 명확한 근거"가 있을 때만 label 채택.
  근거 = (A) 표 비호환(id-canonical의 statement가 row sj_div와 불일치하는데 label-canonical은 일치)
  또는 (B) 동일표인데 경제적 범주 상이(수익↔이익, 잔액↔현금흐름조정 등)이고 label-canonical이 sj_div와 호환.
- **범주는 심판용 메타데이터**. 저장 canonical은 항상 구체 canonical 1개. "수익/부채"로 뭉개지 않는다.
- **범주는 config 데이터**(canonical_accounts.yaml의 각 canonical에 `category` 키 신설). 코드 하드코딩 금지.
- **동의어(같은 범주 충돌)는 현 동작 그대로**(id 유지, 소실·변경 0).

### 2단 심판 로직 (충돌 발생 시)

```
충돌(by_id != by_alias, 둘 다 존재) 발생 →
  cand_id   = id-canonical   (statement = S_id,   category = C_id)
  cand_label= label-canonical(statement = S_lb,   category = C_lb)
  sj = row.sj_div

  [1단: 표 호환성]
  id_ok    = compatible(sj, S_id)      # sj==S 또는 (sj,S)∈{(IS,CIS),(CIS,IS)}
  label_ok = compatible(sj, S_lb)
  if label_ok and not id_ok:  → label 채택 (사유=table_only_label)
  if id_ok and not label_ok:  → id 유지   (사유=table_only_id, 현 동작)
  if not id_ok and not label_ok: → id 유지 + 흔적(statement_guard가 후속 강등)
  if id_ok and label_ok:      → 2단으로

  [2단: 범주 중재] (둘 다 표 호환)
  if C_id == C_lb:  → id 유지 (동의어, 사유=same_category_keep_id)  # 5,175건 무변경
  else:             → 진짜충돌. label이 사람 의도 → label 채택 (사유=category_conflict_label)
                      단, 검산 가능 슬롯(IS/CF 정의식)은 산술이 최종 중재(아래 [3단])

  [3단: 산술검산 중재] (선택적·범주 상이 + 검산 대상일 때만)
  IS/CF 정의식 구성요소·소계에 한해, label 채택 시 항등식이 더 잘 성립하면 label 확정,
  악화되면 id 유지로 롤백. (정규화 단계가 아니라 사후 검증 게이트로 둔다 — 아래 결정 참조.)
```

### 충돌 해소 로직의 위치 — 결정

**별도 후처리 pass로 둔다(map_row 안에 두지 않는다).** 근거:

- `map_row`는 row 단위라 sj_div는 보이지만, 산술검산(3단)은 회사연도×fs_div 집계가 필요 → row 단위 불가.
- 표 호환성·범주 중재(1·2단)는 row 단위로 가능하지만, 이미 `_apply_statement_guard`가
  후처리 pass로 sj_div 심판을 수행 중 → **그 함수를 "드롭 전용"에서 "재중재(re-arbitrate)"로 확장**하는 것이
  중복 없는 자연스러운 위치.
- 따라서: `map_row`는 현행 유지(id-first + 충돌 플래그 + **두 후보를 함께 기록**). 후처리에서 중재.
  → `MappingResult`에 `label_canonical`·`label_statement` 필드를 추가해 후처리가 두 후보를 모두 알게 한다.

**파이프라인 순서 변경**:
```
map_row (두 후보 기록)
  → _arbitrate_conflicts (신설: 1·2단 심판, statement_guard 흡수·확장)
  → _dedupe_statement_rows
  → _dedupe_canonical_rows
  → (3단 산술검산은 정규화 밖 사후 게이트로 유지 — _is_cf_arithmetic.py 재실행)
```

`_apply_statement_guard`는 `_arbitrate_conflicts`에 흡수한다(드롭 로직 = "두 후보 다 비호환" 케이스).

### 범주(category) 차원 설계

**config 스키마**: 각 canonical에 `category: <범주코드>` 추가. 자동 도출 + 수동 검토.

거친 범주 체계(중재에 필요한 최소 입도 — 과세분화 금지):

| statement | category 코드 | 판별 기준(자동 도출 시드) |
|-----------|--------------|--------------------------|
| IS/CIS | `pl_revenue` | 매출·수익 포함, 원가·비용·손실 미포함 |
| IS/CIS | `pl_expense` | 원가·비용·상각·법인세 포함(차감전 제외) |
| IS/CIS | `pl_subtotal` | 이익·순이익·소계·총포괄 |
| IS/CIS | `pl_oci` | 기타포괄·재측정·환산·평가손익 |
| CF | `cf_operating` | 영업활동·창출현금·운전자본·당기순이익조정 |
| CF | `cf_investing` | 유형/무형자산·금융상품·부동산 취득/처분·투자 |
| CF | `cf_financing` | 차입금·사채·배당·자기주식·증자·재무 |
| CF | `cf_subtotal` | 활동현금흐름·순증감·기초/기말현금 |
| CF | `cf_adjust` | 조정·가감·증감(운전자본 조정 라인) |
| BS | `bs_asset` / `bs_liability` / `bs_equity` | statement=BS + 자산/부채/자본 위치 |
| SCE | `sce_change` | (SCE는 변동 단일 범주, 충돌 시 label 우선이 원칙이므로 영향 적음) |

**자동 도출 가능성 추정**(프로토타입 계측 기준):
- IS/CIS(496개): 이름 패턴(매출/수익/원가/비용/이익/포괄)으로 ~80% 자동 도출 가능. 나머지 ~100개 수동.
- CF(778개): 활동분류(영업/투자/재무)가 이름만으론 562/778이 미분류(`cf?`). **CF 활동분류는 수동 비중 높음**.
  단, 충돌 중재에 실제 필요한 건 "방향(취득/처분=유출입±)"과 "조정 여부"이며 이는 이름 패턴으로 잘 잡힘.
- BS(601개): 자산/부채/자본 3분류는 이름+기존 섹션 순서로 ~90% 자동.
- **결론**: 2,028개 전수에 정밀 활동분류를 다는 것은 과투자. **충돌에 실제 등장하는 canonical에만 우선 부여**한다
  (corpus 충돌 쌍에 등장하는 distinct canonical은 수백 개 규모로 추정 → Phase 1에서 정확 집계).

### 작업량 최소화 전략

1. **표 호환성만으로 풀리는 케이스(상이표 84건 + statement_guard 정밀화)에는 범주 불필요** → 먼저 처리.
2. **범주는 "충돌에 실제 등장하는 canonical"에만 부여**(전수 2,028개 아님). Phase 1에서 충돌 쌍의 distinct canonical 집합을 추출해 그 부분집합에만 category를 단다.
3. **자동 도출 → 수동 검토 2단계**: 스크립트로 시드 category 생성 → 충돌 쌍에 등장하는 것만 사람이 검수.

## Implementation Phases

### Phase 1: 측정·범위 확정 (S, 0.5d)
**Goal**: 범주를 달아야 할 canonical 집합과 표 호환성만으로 풀리는 케이스를 분리 확정.
**Tasks**:
- [ ] 충돌 쌍에 등장하는 distinct canonical 집합 추출 - File: `data/backtest/_conflict_canonical_inventory.py`(신규 분석 스크립트) - Size: S
- [ ] 상이표 "label만 맞음" 84건 + "둘다불일치" 184건 목록화(표 호환성 트랙) - Size: S
- [ ] 동일표 범주상이 264건을 "진짜충돌 / 범주노이즈 동의어"로 수기 분류(거짓양성 규모 확정) - Size: M

### Phase 2: 범주 config 스키마 + 자동 도출 (M, 1d)
**Goal**: canonical_accounts.yaml에 category 차원 추가, 충돌 등장 canonical에 부여.
**Tasks**:
- [ ] `CanonicalAccount`에 `category: str = ""` 필드 추가 - File: `src/normalize/config.py` - Size: S
- [ ] `load_canonical_accounts`가 `category` 키 로드 - File: `src/normalize/config.py` - Size: S
- [ ] category 자동 도출 시드 스크립트(이름 패턴+statement) - File: `data/backtest/_derive_category_seed.py` - Size: M
- [ ] 충돌 등장 canonical에 category 수동 검수·기입(yaml) - File: `config/canonical_accounts.yaml` - Size: L

### Phase 3: 표 호환성 심판 확장 (M, 1d)
**Goal**: `_apply_statement_guard`를 `_arbitrate_conflicts`로 확장 — 드롭 전용 → 재중재.
**Tasks**:
- [ ] `MappingResult`에 `label_canonical`·`label_statement` 추가, `map_row`가 두 후보 기록 - File: `src/normalize/mapper.py` - Size: M
- [ ] `_arbitrate_conflicts` 신설(1단 표 호환성) - File: `src/normalize/pipeline.py` - Size: L
- [ ] `_apply_statement_guard` 로직을 `_arbitrate_conflicts`에 흡수, 호출부 교체 - File: `src/normalize/pipeline.py` - Size: M

### Phase 4: 범주 중재 (2단) (M, 1d)
**Goal**: 동일표 + 표 호환 충돌에서 범주 상이 시 label 채택.
**Tasks**:
- [ ] `_arbitrate_conflicts`에 2단 범주 비교 추가 - File: `src/normalize/pipeline.py` - Size: M
- [ ] 중재 사유를 `mapping_status` 또는 신규 흔적 컬럼에 기록(감사 추적성) - File: `src/normalize/pipeline.py` - Size: S

### Phase 5: 전수 재정규화 + 회귀 검증 (M, 1d)
**Goal**: baseline 무회귀 확인.
**Tasks**:
- [ ] 전수 재정규화 - 검증: `PYTHONPATH=. uv run python -m src.normalize.renormalize_all --force` - Size: M
- [ ] 백테스트 recall 5/6 유지 - 검증: `PYTHONPATH=. uv run python -m src.backtest.run_backtest` - Size: S
- [ ] IS/CF 산술검산 무회귀 - 검증: `PYTHONPATH=. uv run python data/backtest/_is_cf_arithmetic.py` - Size: S
- [ ] known_cases 무회귀, SCE 검산 baseline 유지 - 검증: `uv run pytest tests/ -v` - Size: S
- [ ] 진짜 오매핑 ~10건 재현 확인(00545716 영업수익→매출 등 수정 검증) - Size: M

### Phase 6: config gap 별도 트랙 (S, 0.5d — 분리)
**Goal**: by_alias=None 760건(충돌 미감지)은 별개 문제 — config alias 보강.
**Tasks**:
- [ ] 00148504 "발행사채의 증가"→사채발행 alias 보강 등 - File: `config/canonical_accounts.yaml` - Size: M

## Risk Assessment

- **High: 범주 경계 모호로 과채택**(정부보조금수취 vs 수령 같은 동의어를 진짜충돌로 오판) -
  Mitigation: 264건 수기 분류로 거짓양성 목록 확정 → 범주 도출을 보수적으로(애매하면 같은 범주로) 설계. id 유지가 기본.
- **High: CF 운전자본 무회귀**(재고자산증감 영어 id가 BS 잔액으로 오염) -
  Mitigation: 이 케이스는 상이표(CF flow vs BS 잔액)라 1단 표 호환성에서 id(CF) 채택으로 자동 보호. label "재고자산"→BS는 sj_div=CF와 비호환이라 label 거부됨. 회귀테스트로 고정.
- **Medium: SCE 행 이중 정책**(메인 map_row는 id-first, sce_components는 label-first) -
  Mitigation: 메인 SCE 행도 _arbitrate가 1·2단으로 처리하면 두 경로 정책이 수렴. 영향 측정 후 결정.
- **Medium: 두 후보 기록으로 MappingResult/OUTPUT 스키마 변경 파급** -
  Mitigation: ripple-search로 MappingResult·normalized_financials 소비처 전수 점검.

## Success Metrics

- 진짜 오매핑 ~10건 해소(00545716 영업수익→매출 등 재현 통과).
- 백테스트 recall 5/6 유지, known_cases·SCE 검산 baseline 무회귀.
- 동의어 5,175건 무변경(id 유지), CF 운전자본 라인 무오염.
- 범주 거짓양성으로 인한 신규 오매핑 0.

## Dependencies

- Code: Phase 2(category 로드)가 Phase 4(범주 중재)의 선행. Phase 3(표 호환성)는 Phase 2와 독립 병행 가능.
- External: 없음(OpenDART 재수집 불필요, 기존 raw로 재정규화만).
