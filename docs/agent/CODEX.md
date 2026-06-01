# Codex 작업 지침 — 스킬 / 문서 / 워크플로우

> 본 문서는 [SETUP.md](SETUP.md)의 Claude 전용 지시를 Codex 작업 환경에 맞게 분리한 문서다.
> 설계 단일 출처는 [PLAN.md](PLAN.md)이며, Claude용 셋업 정리는 [SETUP.md](SETUP.md)를 참조한다.
> 루트 Codex 진입점은 [../../AGENTS.md](../../AGENTS.md)다.

> 작성일: 2026-06-01 · 상태: Codex 작업 기준 초안

---

## 1. 목적

Codex가 `multi-BS` 프로젝트를 진행할 때 사용할 문서, 스킬, 작업 절차를 정의한다.

이 프로젝트는 OpenDART XBRL 재무제표와 주석을 수집해 BS-IS-CF 숫자 흐름과 주석 근거를
교차검증하고, 감사인이 검토할 공시 재무제표 리스크 후보를 제안하는 도구다.

Codex 작업의 기본 원칙은 다음과 같다.

- 구현 전 [PLAN.md](PLAN.md)를 기준으로 설계 의도를 확인한다.
- Claude 전용 스킬명과 Codex에서 실제 사용 가능한 스킬명을 혼동하지 않는다.
- 계산·정규화·검증은 결정론 코드와 테스트로 고정하고, LLM은 해석·가설·리포트 작성에만 사용한다.
- 모든 Finding은 분식·부정 확정이 아니라 검토 후보 신호로 표현한다.

---

## 2. 문서 읽기 순서

작업 유형별로 아래 순서를 따른다.

| 작업 유형             | 먼저 읽을 문서                 | 추가로 읽을 문서                       |
|----------------------|-------------------------------|----------------------------------------|
| 새 세션 / 핸드오프    | [STATE.md](STATE.md)           | [OVERVIEW.md](OVERVIEW.md), 본 문서     |
| 설계 변경             | [PLAN.md](PLAN.md)             | [SETUP.md](SETUP.md), 본 문서           |
| 스캐폴딩 / 구조 생성  | 본 문서                        | [PLAN.md](PLAN.md) §4, §10, §11         |
| 신호엔진 / DSL 구현   | [PLAN.md](PLAN.md) §6, §8      | 향후 `SIGNAL_ENGINE.md`                 |
| XBRL 정규화           | [PLAN.md](PLAN.md) §4, §9      | 향후 `DATA_CONTRACT.md`                 |
| 주석 인덱서           | [PLAN.md](PLAN.md) §5, §9      | 향후 `DATA_CONTRACT.md`                 |
| UI / 리포트           | [PLAN.md](PLAN.md) §5, §14     | 향후 `PROJECT_OVERVIEW.md`              |
| 의사결정 기록         | [PLAN.md](PLAN.md) §13         | [DECISION.md](DECISION.md)              |

현재 존재하는 핵심 agent 문서는 다음 7개다.

- [STATE.md](STATE.md): 현재 상태·다음 할 일. Codex도 이 파일부터 읽는다.
- [OVERVIEW.md](OVERVIEW.md): 전체 흐름·아키텍처 1페이지 요약.
- [ROADMAP.md](ROADMAP.md): 단계별 할 일 체크리스트.
- [DECISION.md](DECISION.md): 의사결정과 이유.
- [PLAN.md](PLAN.md): 제품·아키텍처·MVP 범위의 단일 출처.
- [SETUP.md](SETUP.md): Claude 기준 스킬, `CLAUDE.md`, 폴더 구조 정리.
- [CODEX.md](CODEX.md): Codex 기준 작업 지침.

---

## 3. Codex에서 사용할 스킬

현재 Codex 세션에서 확인된 스킬명을 기준으로 작성한다. [SETUP.md](SETUP.md)에 있는
`accounting-precision`, `pandera-validation` 등은 Claude 환경 기준이며, 현재 Codex 스킬
목록에는 직접 노출되어 있지 않다. 해당 원칙은 문서·설계 규약으로 계승하되, 스킬 호출명으로
사용하지 않는다.

### 3-1. 필수 작업 스킬

| Codex 스킬                         | 사용 시점                                   | 적용 방식 |
|------------------------------------|---------------------------------------------|----------|
| `claude-agent-planner`              | 큰 기능, 폴더 구조, 단계별 구현 계획 수립    | 구현 전 계획 문서 또는 작업 분해 작성 |
| `claude-agent-documentation-architect` | 한국어 기술 문서 작성·정리                  | `docs/*.md` 작성, 링크·톤·중복 점검 |
| `claude-systematic-debugging`       | 원인 불명 오류, 테스트 실패, 파싱 실패       | 증상 재현 → 원인 격리 → 최소 수정 |
| `claude-verification-before-completion` | 완료 전 검증 범위 점검                      | 실행한 테스트·남은 리스크 확인 |
| `claude-ripple-search`              | 스키마, 설정, 계정명, DSL 변경              | downstream 사용처 검색 |

### 3-2. Python / 데이터 / DB 스킬

| Codex 스킬              | 사용 시점                               | 적용 방식 |
|-------------------------|-----------------------------------------|----------|
| `python-code-quality`   | Python lint, format, type 품질           | `ruff`, `ty` 또는 기존 프로젝트 도구 확인 |
| `claude-python-code-quality` | Python 품질 작업 보조                 | 기존 Claude 스타일 지침 확인 |
| `duckdb`                | DuckDB 스키마, 쿼리, 분석 테이블 설계    | 회사·연도별 분석 DB, 신호엔진 결과 저장 |
| `data-analysis`         | CSV/JSON/TSV 탐색, 샘플 데이터 분석      | OpenDART 응답, XBRL note TSV 탐색 |
| `claude-data-analysis`  | 데이터 분석 보조                        | 대량 표본 점검, 분석 결과 요약 |

### 3-3. Streamlit / UI 스킬

| Codex 스킬                         | 사용 시점                          | 적용 방식 |
|------------------------------------|------------------------------------|----------|
| `setting-up-streamlit-environment` | Streamlit 앱 환경 구성              | `uv` 기반 실행 환경 정리 |
| `using-streamlit-layouts`           | 대시보드 레이아웃                   | 사이드바, 탭, 컨테이너 구성 |
| `building-streamlit-dashboards`     | KPI, Finding 카드, 표 대시보드       | 리스크 리포트와 review queue UI |
| `displaying-streamlit-data`         | dataframe, chart, metric 표시       | 신호엔진 결과·증감률·흐름 시각화 |
| `using-streamlit-session-state`     | 사용자 선택·추가질문 상태 관리      | 회사/연도/분석 결과 상태 유지 |
| `using-streamlit-cli`               | 앱 실행·진단                        | 로컬 실행과 smoke 검증 |

### 3-4. OpenAI / 에이전트 구현 스킬

| Codex 스킬       | 사용 시점                                      | 적용 방식 |
|------------------|-----------------------------------------------|----------|
| `openai-docs`    | OpenAI API, 모델, structured output 사용       | 공식 문서 MCP 우선 확인 |
| `claude-tdd`     | 기능을 테스트 우선으로 구현할 때               | RED-GREEN-REFACTOR 흐름 |
| `claude-subagent-orchestration` | 멀티에이전트 역할 설계 참고       | 역할·상태·입출력 경계 검토 |

### 3-5. 웹 조사 스킬

| Codex 스킬                            | 사용 시점                            | 적용 방식 |
|---------------------------------------|--------------------------------------|----------|
| `claude-agent-web-research-specialist` | OpenDART, XBRL, Arelle 등 최신 확인   | 공식 문서·신뢰 가능한 자료 우선 |
| `playwright-cli`                      | 웹 UI 검증, 브라우저 자동화           | Streamlit 화면 확인 |
| `playwright-explore-website`          | 외부 사이트 구조 탐색                 | OpenDART 화면·문서 탐색 보조 |

---

## 4. Claude 전용 항목의 Codex 대체 기준

[SETUP.md](SETUP.md)는 Claude 전용 파일 생성까지 염두에 둔다. Codex에서는 아래처럼 해석한다.

| SETUP 항목                                  | Codex 기준 처리 |
|---------------------------------------------|----------------|
| `.claude/skills/disclosure-review/SKILL.md`  | Claude 프로젝트 스킬이다. Codex는 자동 활성하지 않지만 도메인 리뷰 체크리스트로 참고할 수 있다. |
| `.claude/skills/disclosure-testing/SKILL.md` | Claude 프로젝트 스킬이다. Codex는 자동 활성하지 않지만 테스트 범위 선정 체크리스트로 참고할 수 있다. |
| `CLAUDE.md`                                  | Claude 실행 환경용이다. Codex 공통 진입점은 루트 [../../AGENTS.md](../../AGENTS.md), 세부 지침은 본 문서다. |
| `skill-rules.json`                           | Claude 스킬 자동 활성용이다. Codex에서는 사용하지 않는다. |
| `accounting-precision`                       | 직접 호출하지 않는다. materiality, rounding, currency 원칙을 설계 규약으로 반영한다. |
| `pandera-validation`                         | 직접 호출하지 않는다. 스키마 검증과 계정 YAML 외부화 원칙을 코드·테스트로 반영한다. |

Codex와 Claude가 공유해야 하는 최소 공통 정책은 루트 [../../AGENTS.md](../../AGENTS.md)에 둔다.

---

## 5. Codex 작업 워크플로우

### 5-1. 작업 전

1. [STATE.md](STATE.md)를 먼저 읽고 현재 위치·다음 할 일·열린 이슈를 확인한다.
2. 사용자 요청이 설계·구현·문서·검증 중 어디에 해당하는지 분류한다.
3. [OVERVIEW.md](OVERVIEW.md)와 [PLAN.md](PLAN.md)에서 해당 레이어(L0~L5)를 확인한다.
4. 관련 스킬을 최소한으로 선택한다.
5. 기존 파일이 있으면 먼저 읽고, 없는 경우 새 파일 생성 범위를 명확히 한다.

### 5-2. 구현 중

1. 스키마·계정명·설정명 변경 시 `rg`로 사용처를 검색한다.
2. 수치 계산은 LLM이 직접 만들지 않고 코드·SQL·테스트로 검증한다.
3. LLM 출력 스키마는 근거 참조를 필수 필드로 둔다.
4. 원본 공시 데이터, API 키, `.env` 내용은 출력하지 않는다.

### 5-3. 완료 전

1. 가능한 최소 테스트를 실행한다.
2. 문서 변경 시 링크와 파일 경로를 확인한다.
3. 구현이 PLAN의 원칙과 충돌하면 [DECISION.md](DECISION.md)에 ADR로 남긴다.
4. 작업 결과를 [STATE.md](STATE.md)에 반영하고, 진척이 있으면 [ROADMAP.md](ROADMAP.md)를 갱신한다.
5. 문제를 겪었으면 [../user/TROUBLESHOOT.md](../user/TROUBLESHOOT.md)에 증상·원인·해결·교훈을 기록한다.
6. 실행하지 못한 검증은 최종 응답에 명시한다.

---

## 6. 프로젝트에서 우선 만들 문서

현재 문서만으로 구현을 시작하면 데이터 계약과 테스트 기준이 부족하다. 아래 문서를 우선 생성한다.

| 문서                     | 목적 |
|--------------------------|------|
| `SIGNAL_ENGINE.md`        | L2 신호엔진, materiality, relationship graph, tool DSL 정의 |
| `TESTING.md`              | 결정론 계산, 주석 인덱서, agent output schema, Streamlit smoke 검증 기준 |
| `PROJECT_OVERVIEW.md`     | 구현 시작 후 실제 디렉토리·실행 방법·문서 인덱스 |

[DECISION.md](DECISION.md)는 이미 D1~D4를 담고 있고, [DATA_CONTRACT.md](DATA_CONTRACT.md)는
L0 수집 스파이크 관찰을 담고 있다. 다음 문서 생성 순서는 `SIGNAL_ENGINE.md` → `TESTING.md`를
권장한다. `PROJECT_OVERVIEW.md`는 코드 스캐폴딩 이후 작성한다.

---

## 7. 구현 시 고정할 설계 결정 후보

아래 항목은 Codex 구현 기본값으로 둔다. 사용자가 다른 결정을 지시하면 [PLAN.md](PLAN.md)와
[DECISION.md](DECISION.md)를 갱신한다.

| 항목                    | Codex 기본값 |
|-------------------------|--------------|
| SQL 자유도              | 완전 자유 Text-to-SQL보다 안전한 tool DSL 우선 |
| 에이전트 오케스트레이션 | 별도 프레임워크보다 순수 Python async + PydanticAI 우선 |
| MVP 분석 범위           | 유동성·운전자본 + 주석 변화 탐지 우선 |
| 계정 정규화             | canonical mapping confidence를 필수 산출물로 둔다 |
| 주석 처리               | 주석 분석 전 note section indexer를 먼저 만든다 |
| Finding 표현            | 확정 표현 금지, counter evidence와 next procedure 포함 |

---

## 8. 금지 및 주의 사항

- "분식 확정", "부정 적발", "운영 성능 검증 완료"로 표현하지 않는다.
- LLM이 계산한 숫자를 근거로 사용하지 않는다.
- severity 텍스트를 직접 더해 점수화하지 않는다.
- 계정명·DART 라벨을 코드에 하드코딩하지 않는다. 설정 또는 mapping layer를 사용한다.
- `.env`, API key, 원본 민감 데이터, 대용량 원천 파일 내용을 출력하지 않는다.
- Claude 전용 스킬 파일을 Codex가 자동으로 사용할 수 있다고 가정하지 않는다.
