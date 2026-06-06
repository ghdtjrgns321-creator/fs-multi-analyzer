# Disclosure Review Agent — 설계 플랜

> **멀티에이전트 교차검증 기반 공시 재무제표·주석 변화 리뷰 도구**
> OpenDART XBRL 재무제표·주석을 수집해 BS-IS-CF 숫자 흐름, 주석 근거, 그리고 전기 대비
> 공시 변화를 교차검증하여, 감사인이 검토할 재무제표 리스크 후보를 제안하는
> Human-in-the-Loop 도구.

> 작성일: 2026-06-01 · 개정: 2026-06-01
> (L2 보강, tool DSL, 주석 인덱서, 공시 변화축 / D2·D3·D4 확정, 공시 변동 에이전트 승격)
> 상태: 초기 설계 (구현 전)

---

## 1. 프로젝트 정의

상장사가 공시한 재무제표(BS 중심, IS·CF·주석 포함)를 입력받아, (1) 숫자·주석·재무제표 간
흐름의 모순과 (2) 전기 대비 공시 변화를 교차검증하고, 감사인이 검토해야 할 리스크 후보를
구조화된 리포트로 제안한다.

부정을 확정하지 않는다. "이 회사는 분식이다"가 아니라 "감사인이 봐야 할 재무제표 리스크
신호"를 제시하는 review 도구다. (포지셔닝은 §15 참조)

차별점은 두 가지다. 첫째, 숫자만 보는 것이 아니라 **재무제표 간 흐름**(BS-IS-CF)을 사슬로
추적한다. 둘째, 올해 수준(level)만 보는 것이 아니라 **전기 대비 변화(change)**, 특히 주석
텍스트의 변화를 전담 에이전트로 분석한다(공시 변동 에이전트, §5).

---

## 2. 포트폴리오 3부작 포지셔닝

이 프로젝트(#3)는 기존 두 프로젝트와 함께 감사의 3개 층위를 나눠 갖는다.

```
              #1 k-ifrs-1115     #2 local-ai-assist     #3 multi-BS (본 프로젝트)
분석 대상     기준서·사례(지식)   전표 모집단(미시)       공시 재무제표(거시)
데이터        텍스트(RAG)        합성 전표               실제 공시(DART)
AI 패러다임   가둔다(환각방지)    룰 기반 스크리닝         멀티에이전트 교차검증
산출물        근거 기반 답변      review queue            재무제표 리스크 리포트
도메인 성격   닫힘(정답지 있음)   반열림(룰 기반)         열림(정답지 없음)
```

- #3은 #2의 최대 약점(실데이터·label 부재)을 **실제 DART 공시 데이터**로 보완한다.
- #3은 #1의 자산(PydanticAI 구조화 출력, 도메인 큐레이션)과 #2의 자산(DuckDB, review
  queue, config-driven 룰, 키워드/임베딩 매칭)을 재활용한다.

---

## 3. 핵심 설계 원칙

논의에서 확정된 5개 원칙. 이후 모든 설계는 이 원칙에 종속된다.

### 원칙 1. 계산은 코드, 발견은 LLM

- **계산(증감률·비율·항등식 등 숫자 그 자체)** 은 결정론 코드/SQL이 수행한다.
  근거: #1에서 LLM 산술 정확도는 Gemini 20~40%, gpt-4.1-mini 100%로 양립 불가 확인.
- **발견·해석·가설(무엇이 의심스러운가, 왜인가, 무엇을 더 볼까)** 은 LLM이 수행한다.
  근거: 재무제표 이상징후는 열린 도메인이라 규칙으로 전수 열거가 불가능하다.

### 원칙 2. 에이전트는 "역할(관점)"에만 대응, 계정은 "데이터"로 흐른다

- 에이전트 축은 **유한·고정인 검증 관점(역할)** 에만 대응한다. 무한히 갈라지는 데이터
  차원(계정·엔티티·기간)은 에이전트로 만들지 않는다.
- 근거: 계정은 산업마다 무한 증식하지만(건설사 미청구공사, 금융사 대출채권 등), 검증
  관점은 닫힌 집합이다. "이번 회사에서 어떤 계정을 볼지"는 신호엔진(§6)이 동적 선정한다.
- **에이전트 추가 게이트**: 새 에이전트는 ⑴ 검증 관점이 기존 직교 차원과 구별되고
  ⑵ 회사·산업과 무관하게 고정일 때만 추가한다. **분석 대상(계정·엔티티·기간 등 데이터
  차원)은 어떤 경우에도 에이전트로 만들지 않는다.** 이 게이트가 "계정으로 가면 끝없다"의
  재발을 막는다.

### 원칙 3. 계정 전문성·관계는 코드가 아니라 데이터(플레이북)에 둔다

- 계정 유형별 분석 지식과 계정 간 관계 사슬은 에이전트 코드가 아니라 설정으로 분리한다.
- 단, 플레이북은 "모든 신호의 전수 열거"가 아니라 **유한·보편 요소(회계 항등식 + 보편
  연산자 + 관계 사슬 + few-shot 예시)** 만 담는다. 정답지가 아니라 출발점이다. (§7 참조)

### 원칙 4. LLM은 풀되 사실에 앵커링한다

- LLM의 자유 추론은 1종오류(과잉지적)를 유발할 수 있다. 두 장치로 막는다.
  1. LLM은 **자유 SQL이 아니라 안전한 분석 함수(tool DSL)** 만 호출한다. 실제 SQL은
     코드가 생성·실행하고(결정론), LLM은 결과만 해석한다. (§8 참조)
  2. 모든 주장은 실제 계산 수치를 근거로 인용해야 하며(grounding), 반박 에이전트가
     근거 없는 주장을 기각한다. (#1의 result_validator 패턴 계승)

### 원칙 5. 수준(level)과 변화(change)를 함께 본다

- 올해 숫자의 수준뿐 아니라 **전기 대비 변화**를 1급 분석축으로 둔다.
- 수치 변화는 L2 신호엔진이, **주석 텍스트 변화(note diff)** 는 주석 인덱서가 생성하며,
  그 회계적 의미는 공시 변동 에이전트(④)가 전담 해석한다.
- "숫자는 그대로인데 주석 문구가 커졌다" 같은 **수치 vs 텍스트 교차**가 핵심 신호다.

---

## 4. 아키텍처 (L0~L6)

```
L0   수집        OpenDART: 단일회사 전체 재무제표(JSON) + 주석 XBRL(TSV), 3개년
L1   정규화      XBRL 계정 → canonical account tree (Arelle) + mapping confidence
L1.5 주석 인덱서  주석 → 섹션 분류 + 전기/당기 정렬 + note diff + 계정↔섹션 매핑
L2   신호엔진    결정론: materiality + relationship graph + QoE + 변화(수치/텍스트)
                 → "볼 가치 있는" 계정·신호 top-N 동적 선정 + 플레이북 주입
L3   역할에이전트(LLM, 고정 5개): 수치 → 주석 → 흐름 → 변동 → 반박
                 tool DSL 호출로 추가 확인. 모든 주장에 EvidenceRef 강제
L4   리포트      Finding(이슈유형·유의성·확신도·근거·반대근거·다음절차·위험도) 종합
L5   Human       감사인이 승인/기각/추가질문 (review queue 철학)
```

L1.5와 L2가 토대다. 나머지 레이어는 모두 이 출력에 얹힌다.

---

## 5. 에이전트 구성 및 리포트 스키마

### 역할 기반 고정 5개 — 분석의 직교 차원

에이전트는 회사·계정과 무관하게 동일하게 작동한다. 5개 역할은 분석 차원을 망라하는
닫힌 집합이며, 무한 증식하지 않는다(원칙2).

```
역할       차원              무엇을 보나
① 수치   정량 × 수준        당기 숫자의 이상 (추세·구성비·이상변동)
② 주석   정성 × 수준        당기 주석의 리스크 (우발부채·특수관계자·만기 등)
③ 흐름   공간 교차          재무제표 "간" 정합 — BS↔IS↔CF + 관계 사슬
④ 변동   시간 교차          전기↔당기 변화 + 수치 vs 텍스트 모순 (공시 변동 전담)
⑤ 반박   메타              ①~④ 결론을 근거로 검증·기각
```

- **③ 흐름 vs ④ 변동 경계**: 흐름은 재무제표 *간* 공간축, 변동은 한 재무제표 *내* 시간축.
  축이 직교하므로 책임이 겹치지 않는다.
- **④ 변동 에이전트도 계정-agnostic**: "무엇이 변했는지"는 주석 인덱서(L1.5)와 L2가
  데이터로 주입한다. 변동 에이전트는 변화 리스트의 회계적 의미만 해석한다.

### 리포트 스키마

```python
class EvidenceRef(BaseModel):
    source: Literal["financial_statement", "note", "cash_flow", "prior_year_note"]
    locator: str               # 계정 ID / 주석 섹션 ID 등 추적 키
    year: str
    value: str | None          # 결정론 레이어가 계산한 실제 수치

class AccountFinding(BaseModel):          # ①②③ 수준·흐름 분석
    account: str               # 분석 대상 계정 (신호엔진이 동적 선정)
    issue_type: IssueType      # enum (자유 문자열 금지 — 집계·필터 가능하도록)
    materiality_score: float   # 유의성 (절대금액 + 총계 대비 비율)
    anomaly_score: float       # 이상 정도 (변동·항등식 위반 등)
    confidence: Literal["High", "Medium", "Low"]   # 매핑·근거 강도 반영
    numeric_evidence: list[EvidenceRef]
    note_evidence: list[EvidenceRef]
    flow_evidence: list[EvidenceRef]
    counter_evidence: list[str]      # 숫자상 반대 가능성
    normal_explanation: list[str]    # 정상일 수 있는 사업적 설명
    next_procedure: list[str]        # 다음 감사 절차 (포트폴리오 킬러)
    risk_level: Literal["High", "Medium", "Low"]

class ChangeRef(BaseModel):              # ④ 공시 변동 전용 근거
    target: str                # 계정 또는 주석 섹션
    change_type: Literal["new_appearance", "removal", "expansion",
                         "reduction", "value_change"]
    prior: str | None
    current: str | None
    year_from: str
    year_to: str

class DisclosureChangeFinding(BaseModel):  # ④ 공시 변동 에이전트
    target: str
    issue_type: IssueType
    change_evidence: list[ChangeRef]
    cross_inconsistency: str | None    # 수치 vs 텍스트 모순 (핵심 신호)
    materiality_score: float
    confidence: Literal["High", "Medium", "Low"]
    counter_evidence: list[str]
    next_procedure: list[str]
    risk_level: Literal["High", "Medium", "Low"]
```

`IssueType`은 통제된 enum으로 둔다(예: `receivables_quality`, `inventory_obsolescence`,
`going_concern`, `contingent_liability_understatement`, `related_party_concentration`,
`earnings_quality`, `liquidity_risk`, `disclosure_change`, `unmapped_material_account`).

매트릭스(계정 × 검증관점)는 에이전트 편성이 아니라 **리포트 출력 구조**로 존재한다.
행은 신호엔진이 회사마다 동적 선정한 계정, 열은 검증관점이다.

---

## 6. 신호엔진 (L2) — 결정론 1차 스크리닝

LLM 이전 단계. 코드/SQL만 사용한다. 이 프로젝트의 성패가 여기에 달려 있으므로 두껍게 잡는다.
단순 이상치 탐지를 넘어 "감사적" 신호를 생성하는 것이 목표다.

### 6.1 Materiality engine

어떤 계정·변동이 검토할 가치가 있는지 점수화한다.

- 절대 금액 + 자산총계/매출 대비 비율
- 변동의 유의성(절대·상대 변동폭)
- 정상 범위 이탈 정도. **MVP는 단일회사 시계열(자기 과거 추세) 기준**(§14 D3).
  baseline source를 추상화해 향후 업종 벤치마크를 끼울 수 있게 둔다(§16).

### 6.2 Account relationship graph

계정 간 인과·연결 사슬을 그래프로 정의(플레이북, §7)하고 사슬을 따라 정합성을 점검한다.
단순 pairwise 비교를 넘어 "사슬 추적"이 핵심이다.

```
매출 → 매출채권 → 대손충당금 → 영업CF        (수익의 질·회수가능성)
재고 → 매출원가 → 재고평가손실               (재고 진부화·원가)
차입금 → 이자비용 → 재무활동CF → 만기 주석    (유동성·계속기업)
영업이익 → 영업외손익/법인세 → 당기순이익     (IS 흐름)
차입금 증감 → 재무활동CF → 투자활동CF/CAPEX   (자금 조달과 사용처)
순이익 → 영업CF → 운전자본 변동               (이익의 질)
```

### 6.3 Quality-of-earnings signals

이익의 질을 정량화한다.

- 발생액(accruals) vs 현금 괴리, 영업CF / 당기순이익 비율
- 일회성·평가이익(FVTPL 등)이 순이익에서 차지하는 비중
- DSO / DIO 추세, 매출채권·재고 회전율 변화

### 6.4 변화(change) 신호 — ④ 변동 에이전트 입력

- 수치 변화: 전기 대비 증감·z-score·추세 이탈
- 텍스트 변화: 주석 인덱서(L1.5)가 생성한 note diff —
  watchlist 키워드(소송·계속기업 불확실성·약정 위반·회수 지연 등)의 신규 등장,
  특수관계자 거래처·금액 급변, 우발부채 문구 확대 등
- 교차 모순: 수치(불변) vs 텍스트(확대) 등 → ④ 변동 에이전트의 `cross_inconsistency`

### 6.5 동적 계정 선정

materiality × anomaly × 신호강도로 top-N을 산정한다(#2의 topic_scoring / case priority
재활용). 산출물: "이번 회사에서 주목할 계정 + 결정론 계산 결과 + 관련 주석 위치 + 변화
리스트" → L3.

구현은 두 층으로 나눈다.

- 전수 보편 스캔: BS·IS·CF의 모든 `account_id`에 YoY, z-score, 구성비 급변을 적용한다.
  canonical에 등록되지 않은 회사 확장계정도 label/account_id로 추적한다.
- 깊은 분석: `relationship_chains.yaml`에 등록된 주요 계정 사슬은 별도 괴리·방향성 규칙으로
  더 깊게 본다. 연결 특유 이슈는 새 에이전트가 아니라 CFS/OFS 괴리와 연결 구조 사슬로 흡수한다.

---

## 7. 플레이북 — 정답지가 아니라 출발점

계정별 신호를 전수 열거하지 않는다. 유한·보편 요소만 설정으로 둔다.

```yaml
identities:                    # 회계 항등식 — 유한, 보편 (계정 무관)
  - 자산 = 부채 + 자본
  - 기초잔액 + 증감 = 기말잔액
  - 영업CF ↔ 당기순이익 + 비현금조정

universal_operators:           # 보편 연산자 — 전 계정에 일반 적용
  - yoy_change
  - z_score
  - mix_shift
  - cfs_ofs_gap
  - growth_divergence
  - flow_reconciliation

relationship_chains:           # 계정 관계 사슬 (§6.2) — 데이터로 정의
  - [매출, 매출채권, 대손충당금, 영업CF]
  - [재고, 매출원가, 재고평가손실]
  - [차입금, 이자비용, 재무활동CF, 만기주석]
  - [영업이익, 금융손익, 법인세, 당기순이익]
  - [장기차입금, 재무활동CF, 투자활동CF, 유형자산취득, 사업결합]
  - [당기순이익, 영업CF, 운전자본변동, 매출채권, 재고, 매입채무]
  - [지배기업소유주지분, 비지배지분, 지배기업귀속순이익, 비지배지분순이익, 관계기업투자, 지분법이익]

watchlist_keywords:            # 주석 변화 탐지용 (§6.4)
  - 소송
  - 계속기업 불확실성
  - 약정 위반
  - 회수 지연

few_shot_hints:                # LLM 가이드용 대표 예시 5~10개 (전수 아님)
  - "매출↑ + 영업CF↓ → 이익의 질"
  - "매출채권 증가율 > 매출 증가율 → 수익인식 공격성"
  - "충당부채 소액 + 주석상 소송·보증 다액 → 우발부채 과소"
```

새 산업·계정 추가 시 코드 변경 없이 설정만 확장한다(#2 config-driven 계승).

---

## 8. tool DSL — LLM이 호출하는 안전한 분석 함수

LLM에게 자유 SQL을 주지 않는다. LLM은 "어떤 함수를 호출할지"만 고르고, SQL은 코드가
생성·실행한다. 안정성과 설명력(어떤 분석을 했는지 함수명에 남음)을 함께 얻는다.

```
compare_growth(account_a, account_b, years=3)      # 증가율 괴리
compute_ratio(numerator, denominator, years=3)     # 비율 추세
scan_mix_shift(statement="BS", years=3)            # 구성비 급변
reconcile_cf_with_bs(account, years=3)             # BS-IS-CF 정합
find_note_mentions(account, note_sections)         # 관련 주석 검색
diff_notes(section_type, year_a, year_b)           # 주석 변화 (§6.4)
```

함수셋은 확장 가능하게 설계한다. 완전 자유 SQL(escape hatch)은 MVP에 두지 않는다(YAGNI).

### 환각 방지 장치 (원칙 4 상세)

```
장치 ① tool DSL 앵커링
   LLM "매출채권이 이상" 가설 → compare_growth("매출채권","매출") 호출 → 엔진 실측 →
   결과를 LLM이 해석. LLM은 숫자를 지어내지 못함.

장치 ② Grounding + 반박 에이전트
   모든 LLM 주장은 EvidenceRef(실제 수치·주석 위치)를 인용해야 함. 못 대면 반려.
   반박가: "그 숫자 DB에 있는가 / 주석 근거 있는가 / 다른 설명 가능한가" → 없으면 기각.
```

---

## 9. 데이터 소스 (OpenDART)

| 데이터              | API / 형식                    | 용도                          |
|---------------------|-------------------------------|-------------------------------|
| 단일회사 전체 재무제표 | OpenDART API (JSON, 정형)      | 수치 분석 입력 (BS/IS/CF 전 계정) |
| 주석                | XBRL note (TSV, 비정형 혼재)    | 주석 분석·변화 입력 (L1.5)      |
| 원본 XBRL / taxonomy | OpenDART                      | 계정 정규화(L1)                |

- 숫자 API는 정형이라 다루기 쉽지만, 주석 XBRL은 표·비정형 텍스트가 섞여 난이도가 높다.
- 라이브러리: OpenDartReader(수집), Arelle(XBRL 정규화) 검토.

### 계정 정규화 confidence (L1)

회사별 extension account, 한글 라벨, 연결/별도, 보고서 양식 차이로 표준 매핑이 자주 깨진다.
매핑 결과에 confidence를 부여하고, 미매핑 계정을 숨기지 않는다.

```
mapping_status:
  - exact_taxonomy_match       # 표준 taxonomy 정확 일치
  - label_alias_match          # 한글 라벨/별칭 매칭
  - parent_rollup_match        # 상위 계정으로 롤업
  - unmapped_extension_account # 회사 확장계정 — 매핑 실패
```

**unmapped 계정은 분석 제외가 아니라 "기타 중요 계정"으로 리포트에 별도 게시**한다.
유의성이 큰 미매핑 계정을 누락하면 그 자체가 2종오류다. mapping_status는 Finding의
confidence에 전파한다.

---

## 10. 주석 인덱서 (L1.5)

주석을 에이전트가 통으로 읽으면 비효율적이고 환각을 유발한다. 먼저 구조화한다.

- **섹션 분류**: 주석을 섹션 단위로 분할하고 유형을 분류한다(키워드 룰 + LLM 분류
  하이브리드, #1 임베딩 매칭 / #2 키워드 매칭 자산 재활용).

```
note_section_type:
  accounting_policy / financial_risk / borrowings_maturity / collateral /
  related_party / contingencies / fair_value / impairment / revenue /
  subsequent_events
```

- **계정 ↔ 섹션 매핑**: "매출채권 리스크 → financial_risk / contingencies" 식으로 연결해,
  L3 주석 분석가가 관련 주석을 빠르게 찾게 한다.
- **전기/당기 정렬 + note diff**: 동일 섹션을 연도 간 정렬해 변화(신규/삭제/변경 문구,
  watchlist 키워드 등장)를 추출한다. → §6.4 변화 신호이자 ④ 변동 에이전트의 입력.

---

## 11. 기술 스택 (기존 자산 재활용)

| 영역          | 기술                          | 출처                        |
|---------------|-------------------------------|-----------------------------|
| 언어/패키지   | Python 3.11 + uv              | #1, #2 공통                 |
| 에이전트·오케스트레이션 | PydanticAI + 순수 Python async | #1 재활용 (D2 확정)       |
| DB            | DuckDB (회사/연도 격리)         | #2 재활용                   |
| 설정          | pydantic-settings + YAML       | #2 config-driven 재활용     |
| 주석 분류/매칭 | 키워드 룰 + 임베딩              | #1, #2 매칭 자산 재활용      |
| XBRL 처리     | Arelle                        | 신규                        |
| 공시 수집     | OpenDartReader                | 신규                        |
| UI            | Streamlit + plotly             | #1, #2 재활용               |

- **오케스트레이션(D2 확정)**: 순수 Python async + PydanticAI. #1 ADR-1 경험 계승.
  L3 교차검증은 고정 순서 1회(수치→주석→흐름→변동→반박)이므로 프레임워크 불필요.
  토론이 사이클이 되는 부분만 경량 상태머신으로 국소 처리한다.
- LLM 모델 선택(추론용 강모델 / 수치용 경량)은 #1의 듀얼 라우팅 경험을 따른다.

---

## 12. MVP 범위

전 계정을 한 번에 다루지 않는다. 표준 계정 매핑이 쉽고 데모 임팩트가 큰 순서로 진행한다.

### MVP 1 — 유동성·운전자본 + 공시 변동 (우선)

- BS/IS/CF 3개년 수집 + canonical account mapping(confidence 포함)
- 매출 → 매출채권 → 영업CF 품질 분석 (관계 사슬)
- 차입금 / 유동성 기본 분석
- **공시 변동 에이전트**: 전기 대비 주석 변화 탐지 (watchlist 키워드 신규 등장 수준 —
  의미 diff 고도화는 후순위)
- Finding 리포트(AccountFinding + DisclosureChangeFinding) + 감사인 확인 질문

> 선정 이유: 계정 표준화가 쉽고, 매출↔채권↔영업CF 교차가 데모 임팩트가 크며, 공시 변동
> 에이전트를 MVP1부터 넣어 "숫자만 보는 도구"와의 차별점(제품 컨셉)을 처음부터 보여준다.

### MVP 2 — 차입금·계속기업 리스크

- 단기·장기차입금·이자비용·만기 주석·담보/약정

### MVP 3 — 우발부채·주석 리스크

- 충당부채 BS 금액 vs 우발부채·소송·보증 주석 (수치 vs 텍스트 교차 — ④ 변동 에이전트 강점)

---

## 13. 리스크 / 난관

| 난관                 | 내용                                                       | 대응                          |
|----------------------|------------------------------------------------------------|-------------------------------|
| L1 계정 정규화       | 회사별 확장계정·라벨·연결/별도·양식 차이로 매핑 자주 실패     | mapping confidence + unmapped를 "기타 중요 계정"으로 게시 |
| 주석 XBRL 파싱       | 표·비정형 텍스트 혼재로 난이도 높음                          | L1.5 인덱서로 섹션 분류, MVP는 핵심 섹션만 |
| 주석 의미 diff       | 정교한 의미 비교는 노이즈·난이도 큼                          | MVP는 watchlist 키워드 등장 수준부터       |
| materiality 정상범위 | 단일회사 시계열만으로는 "업종 대비 비정상" 판단 불가          | MVP는 자기 추세 기준, 업종 비교는 §16 개선방향 |
| LLM 과잉지적(1종오류) | 자유 추론이 헛것을 봄                                        | tool DSL 앵커링 + grounding + 반박         |

---

## 14. 결정 기록 (Decisions)

- **D1. LLM의 SQL 자유도** — **확정: tool DSL(안전한 분석 함수 호출).** 자유 SQL 미채택.
- **D2. 멀티에이전트 오케스트레이션** — **확정: 순수 Python async + PydanticAI.**
  #1 ADR-1 경험 계승. L3 교차검증이 고정 순서 1회라 프레임워크 불필요.
- **D3. 동종업계 비교** — **확정: MVP는 단일회사 시계열만.** materiality baseline을
  추상화해 향후 업종 벤치마크를 끼울 수 있게 인터페이스만 확보. 업종 풀은 §16 개선방향.
- **D4. 공시 변동의 위상** — **확정: 독립 "공시 변동 에이전트"(④)로 승격.** 원칙2는
  "데이터 차원(계정)을 에이전트화 금지"이지 "역할 추가 금지"가 아니므로 위반 아님.
  재발 방지: 원칙2에 에이전트 추가 게이트 명문화 + 역할을 직교 5차원 닫힌 집합으로 고정
  + 변동 에이전트도 계정-agnostic + 흐름(공간축)과 변동(시간축) 직교로 경계 분리.

---

## 15. 포지셔닝 / 금지 표현 (#2 정책 계승)

- 이 프로젝트는 부정을 판정하거나 운영 탐지 성능을 보장하는 모델이 아니다. 공시
  재무제표에서 감사인이 검토할 리스크 후보를 설명 가능한 형태로 제시하는 보조 도구다.
- **금지 표현**: "분식 확정", "부정 자동 적발", "운영 성능 검증 완료" 등 확정적·성능
  보장 표현은 사용하지 않는다.
- 모든 Finding은 반대 근거(counter_evidence)·정상 설명(normal_explanation)·감사인 확인
  질문, 그리고 다음 절차(next_procedure)를 포함해 확정을 회피하고 사람의 판단을 보조한다.

---

## 16. 추후 개선방향 (Out of MVP Scope)

MVP에서 제외하되 설계상 확장 가능하게 인터페이스를 열어둔 항목.

| 항목                  | 내용                                                      | 비고                     |
|-----------------------|-----------------------------------------------------------|--------------------------|
| 동종업계(⑥) 벤치마크   | 업종 자동 수집 → 피어는 지표만 → 업종 분위수로 "업종 대비 비정상" | B 접근 확정. 상세 §16.1 (A 소수 피어 단계는 건너뜀) |
| 주석 의미 diff 고도화  | watchlist 키워드 → 의미 단위 변화 비교                      | 임베딩·정렬 기반          |
| 공시 변동 다회 토론    | 고정 순서 1회 → debate-until-consensus 사이클               | 필요 시 LangGraph 재검토 (D2) |
| RAGAS류 자동 평가      | Finding 품질 정량 평가                                     | #1 개선방향과 공통        |

### 16.1 동종업계(⑥) 확장 방법 — B 접근 확정 (2026-06-02)

접근은 **B(업종 자동 + 지표)로 직행**한다. A(소수 피어 수동 지정)는 건너뛴다 — A→B 단계는
시간 낭비다.

핵심: 동종업계 비교의 비용은 "피어 정규화"인데, **피어는 풀 5축 분석이 아니라 지표 계산용
숫자만** 수집하면 부담이 크게 준다(D3의 "정규화 N배" 우려를 우회). 우리 회사만 5축 풀 분석,
피어는 지표 baseline용.

| 과제 | 방법 |
|------|------|
| ① 피어 선정 | DART 업종코드(KSIC) 자동 |
| ② 피어 데이터 | 기본 합계 + 핵심 계정만 (주석·교차 불필요) |
| ③ baseline | 피어 지표 중앙값·분위수 |
| ④ 비교·신호 | 우리 회사 지표의 업종 분위 위치(이탈) → 신호 |

- ⑥ 동종업계는 **6번째 관점**(⑤ 외부처럼 교차에 참여, 판단 직접 변경은 않음).
- 재활용: `src/signals/ratios.py` + materiality baseline 추상화(D3에서 인터페이스 이미 열어둠).
- 근거 기준: ISA 520 분석적 절차의 industry comparison (AUDIT_BASIS).
- 주의: 회사별 회계정책·사업구조 차이(사과-오렌지) → "확정"이 아니라 "참고 신호"(§15).

구현 상태(2026-06-04): B 접근을 `config/industry_peers.yaml`, `src/peers`,
`src/report/industry.py`로 구현했다. 대상 회사의 OpenDART `induty_code`를 조회해 해당
업종 config 피어만 사용하며, 피어는 `finstate_all` 재무제표만 수집해 지표 중앙값·분위수를
계산한다. 피어 미구성 업종은 ⑥ 관점만 deferred한다. 주석·외부·5축 분석은 피어에 적용하지
않는다. ⑥ 관점은 L4 교차에 참여하지만 내부 판단 필드를 변경하지 않는다(D15).
