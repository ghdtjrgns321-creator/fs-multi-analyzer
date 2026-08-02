# OVERVIEW — 전체 흐름

> 1페이지 길잡이. 상세는 [PLAN.md](PLAN.md). 현재 진행 상태는 [STATE.md](STATE.md).

## 무엇을 만드나

공시 재무제표(BS 중심 + IS·CF·주석)를 읽고, 숫자·주석·재무제표 간 흐름의 모순과 전기 대비
공시 변화를 멀티에이전트가 교차검증해, 감사인이 검토할 리스크 후보를 제안한다.
**부정을 확정하지 않는다** (포지셔닝: PLAN §15).

## 파이프라인 (L0~L6)

```
L0 수집(OpenDART) → L1 정규화(XBRL→canonical) → L1.5 주석 인덱서
→ L2 신호엔진(결정론) → L3 역할 에이전트 5개 → L4 리포트 → L5 Human
```

## 신규 회사 온보딩 (L1→L2 진입 전 관문)

처음 보는 회사는 직선 파이프라인을 바로 타지 않는다. 정규화 직후 **온보딩 게이트**를
거쳐 분석에 진입한다(`src/normalize/onboarding_gate.py`·`src/report/alias_suggest.py`·
`dashboard/onboarding.py`). 회사별 라벨 변주(무표준코드 계정)를 quirk로 흡수하는 경로다.

```
raw 수집 → L1 정규화
  → [온보딩 게이트]
       G1~G5 결정론 점검(완결성·BS 항등식·산술검산·신호무결성)  ← 기존 감사 스크립트 재사용
       G6 LLM 전문 통독(gpt-5.4 9렌즈 홀리스틱 dump)
       무표준코드 계정 별칭 제안: 후보검색=코드 → 분류선택=LLM → 적용=사람 확인(자동적용 금지)
  → 사람이 확정하면 config/company_quirks.yaml(alias_additions/account_overrides) 등록
  → 재게이트 통과 시 L2 진입
```

- **자동적용 금지·앵커링**: LLM은 코드가 좁힌 candidate 안에서만 고르고(밖이면 '기타 중요
  계정' 강등), 등록은 사람 확인 클릭으로만. 부정 확정 아님(제안은 후보).
- quirk는 corp_code/year를 **데이터 키**로 그 회사·연도에만 적용(`_apply_company_quirks`,
  하드코딩 분기 아님). 매칭 없는 회사는 무변경(무회귀).

## 데이터 흐름 (전수 읽기 → 관점 배분 → 독립 판단)

```
   ┌──────────────────────────────────────────────────────────┐
   │  L1 frame · 5종 전 계정  (BS · IS · CIS · CF · SCE)         │
   └──────────────────────────────────────────────────────────┘
                          │  L2 전수 스캔
                          │  universal · red_flags · restatement
                          ▼
   ┌──────────────────────────────────────────────────────────┐
   │  review_queue          (strict 점수 = BS·IS 만)            │
   │  account_level_series  (5종 전 계정 시계열)                │
   │  ratio_summary · note_sections · restatements             │
   └──────────────────────────────────────────────────────────┘
                          │  materials.py 관점별 발췌
                          ▼
   ┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
   │numeric ││ flow   ││ change ││ note   ││external││industry│
   └────────┘└────────┘└────────┘└────────┘└────────┘└────────┘
     GPT-5.4   GPT-5.4   GPT-5.4   GPT-5.4   Gemini    GPT-5.4
                          │  create_perspective_assessment ×6 (독립)
                          ▼
                  crosscheck (교차, 결정론)
                          │
                          ▼
              synthesis (종합) ──▶ L5 Human 확인
```

- **strict 채점 경계 = `sj_div ∈ {BS, IS}`**. CF·CIS·SCE·restatement는 점수 제외, material 단서로만.
- 관점은 발췌만 받음(통째 X). 관점당 LLM 1회 + 종합 1회. 관점끼리 결과 입력 안 받음(독립).

- **전수 읽기는 결정론(L2)**: `universal.scan_*`가 5종 전 계정을 스캔해 후보 큐·전계정 시계열·지표·주석을 만든다.
- **strict 채점 경계 = `sj_div ∈ {BS, IS}`**(S3 보완). CF·CIS·SCE·restatement는 결정론 점수에서 제외하고
  `account_level_series`·관점 material에 단서로만 실어 LLM이 맥락 판단(S2·S3 격하 패턴).
- **관점은 발췌만 받는다**: `materials.py`가 역할별로 분배(numeric=큐+지표+시계열, note=주석섹션, flow=흐름,
  change=변동+재작성, external=Gemini grounding, industry=peer). 내부 5관점 GPT-5.4, external Gemini.
- LLM 호출 = **관점당 1회(6) + 종합 1회**. 관점끼리 결과를 입력으로 받지 않는다(독립). 교차·종합은 그 뒤.

## 5원칙 (요약)

1. 계산은 코드(결정론), 발견은 LLM
2. 에이전트는 역할(닫힌 5차원), 계정은 데이터로 흐른다
3. 계정 전문성·관계는 플레이북(데이터)
4. LLM은 풀되 사실에 앵커링 (tool DSL + grounding + 반박)
5. 수준(level)과 변화(change)를 함께 본다

## 에이전트 5개 (직교 차원)

```
① 수치 (정량×수준)  ② 주석 (정성×수준)  ③ 흐름 (공간교차)
④ 변동 (시간교차)   ⑤ 반박 (메타)
```

## 핵심 결정 ([DECISION.md](DECISION.md))

- D1 tool DSL (자유 SQL 금지)
- D2 순수 Python async + PydanticAI (프레임워크 미채택)
- D3 단일회사 시계열 (업종 벤치마크는 추후)
- D4 공시 변동 독립 에이전트(④) 승격

## 문서 맵

[../README.md](../README.md) 참조 — user/ 와 agent/ 구분.
