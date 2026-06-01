# 프로젝트 셋업 정리 — 스킬 / CLAUDE.md / 문서화 / 폴더 구조

> 기존 두 프로젝트(k-ifrs-1115, local-ai-assist)와 글로벌 스킬에서 multi-BS가 가져올
> 자산을 정리한다. 설계 단일 출처는 [PLAN.md](PLAN.md). 본 문서는 그 위에 "무엇을 재활용
> 하고 무엇을 새로 만들지"를 정한다.

> 작성일: 2026-06-01 · 상태: 생성 완료, docs 구조 재편 반영

---

## A. 스킬 맵

### A-1. 글로벌 스킬 — 자동 활성 (복사 불필요)

`~/.claude/skills/` 에 이미 있고, description 트리거가 multi-BS 작업과 겹쳐 자동 활성된다.

| 스킬 | 용도 | multi-BS 적용 지점 |
|------|------|--------------------|
| `tdd` | RED-GREEN-REFACTOR | 전 작업 공통 (글로벌 CLAUDE.md §7) |
| `verification-before-completion` | 완료 증거 검증 | 전 작업 공통 |
| `systematic-debugging` | 4단계 근본원인 | 에러·버그 발생 시 |
| `ripple-search` | 스키마/설정 파급 검색 | canonical 계정·playbook·DSL 변경 시 |
| `subagent-orchestration` | 서브에이전트 모델/상태 | 5개 역할 에이전트 설계 시 |
| **`accounting-precision`** ⭐ | float 오차·materiality·round | **원칙1(결정론 계산), L2 materiality engine** |
| **`pandera-validation`** ⭐ | L1/L2/L3 3계층·COA YAML | **L1 정규화, 회계 항등식, mapping confidence** |
| `developing-with-streamlit` (+서브) | 대시보드·세션·레이아웃 | L4/L5 리포트 UI |
| `mermaid` | 다이어그램 | 문서 아키텍처 그림 |
| `find-skills` | 스킬 탐색 | 새 기술 도입 시 |

> ⭐ 두 스킬이 핵심이다. `accounting-precision`의 "materiality 비교 전 round 필수",
> `pandera-validation`의 "계정코드 하드코딩 금지 → YAML 외부화", "closing_balance =
> 당기증감 vs 누적잔액 구분"은 multi-BS의 L1·L2에서 그대로 적용된다. 둘 다 글로벌이라
> 추가 작업 없이 트리거되지만, 적용 지점을 CLAUDE.md Skill 맵에 명시해 환기한다.

### A-2. 프로젝트 특화 스킬 — 각색해서 신규 생성

#2의 `audit-review`/`audit-testing`은 골격(감사 도메인 리뷰·테스트 규약)이 유용하나
내용이 #2 전용(PHASE1, DataSynth/Rust, 31룰)이라 그대로 못 쓴다. multi-BS용으로 각색한다.

| 신규 스킬 | 원본 | 각색 방향 |
|-----------|------|-----------|
| `disclosure-review` | `audit-review` | PHASE1·DataSynth 제거 → Finding 스키마·공시변동·XBRL 정규화·grounding·**포지셔닝(분식 확정 금지, §15)** 규약으로 교체 |
| `disclosure-testing` | `audit-testing` | DataSynth/Rust 제거 → tool DSL 결정론 테스트·주석 인덱서·정규화 confidence·Streamlit smoke 로 교체 |
| `skill-rules.json` | #2 동일 | 위 2개의 프로젝트 스코프 트리거(키워드: 공시, 주석, XBRL, Finding, materiality, 정규화) |

**계승할 핵심 규약**(#2에서 검증된 것):
- 결과 언어가 "확정"으로 읽히지 않게 (review-only ↔ confirmed 구분) → §15와 일치
- severity 텍스트 직접 합산 금지 → score는 normalized 후 집계
- mapping confidence 투명, optional 누락은 graceful degradation
- LLM 출력은 evidence grounding, 라이브 API 호출은 default 테스트에서 금지
- `.env`·secret·raw 데이터 로깅/출력 금지

### A-3. 가져오지 않을 스킬 (이유)

| 스킬 | 제외 이유 |
|------|-----------|
| `imbalanced-ml` | 이 프로젝트는 지도학습 ML 아님 |
| `langgraph-rag-guidelines` | D2에서 LangGraph 미채택 (개선방향 §16 보류 시 재검토) |
| `docker-compose-infra-guidelines` | 배포 후순위 (MVP는 로컬 실행) |
| `docx`/`pptx`/`pdf`/`ppt-brand-guidelines` | 리포트 export 산출물 후순위 |
| `pytest-backend-testing` | FastAPI 채택 시에만. MVP는 Streamlit 단독 가능 → 보류 |

---

## B. CLAUDE.md 골격

두 프로젝트 형식을 합치되 글로벌 룰(§1~§8)을 중복하지 않는다. multi-BS용 구조:

```
# Disclosure Review Agent — Project Context

> (상단 고정) 포지셔닝 원칙: 분식 확정 금지, 검토 후보 신호 제시       ← #2의 PHASE1 원칙 패턴
                                                                    (§15 단일 출처)

## 워크플로우        작업 전 docs 읽기 / 작업 중 Agent·Skill 활용 / 작업 후 docs 갱신  ← #1 패턴
## Quick Reference   스택 표 (Python 3.11, uv, DuckDB, PydanticAI, Streamlit, Arelle)  ← #2 패턴
## 핵심 설계 원칙    PLAN §3 5원칙 요약 (계산=코드/발견=LLM, 에이전트=역할, 게이트 등)
## 환경 변수         DART_API_KEY, OPENAI_API_KEY / GOOGLE_API_KEY
## 핵심 코딩 규칙    100줄·SRP / 계산-LLM 분리 / 계정 YAML 외부화 / Pandera 3계층 / 결정론 우선
## Skill 활용 맵     레이어(L0~L6)별 활용 스킬 (A-1·A-2)
## Agent 활용 가이드  planner / code-reviewer / documentation-architect / Explore / Plan
## dependency-groups core / agent / dashboard / dev (uv groups)
## 문서 가이드       docs 인덱스 + 작업 전후 참조·갱신 규칙
```

- 글로벌 `~/.claude/CLAUDE.md` §1~§8을 재서술하지 않는다. 프로젝트 고유 규칙만 담는다.
- 루트 `AGENTS.md`는 Codex/비-Claude 에이전트 공통 진입점으로 둔다. Claude 전용 규칙은 `CLAUDE.md`,
  Codex 세부 규칙은 [CODEX.md](CODEX.md)에 둔다.

---

## C. 문서화 방안

문서는 보는 주체에 따라 `user/`과 `agent/`로 분리한다. 다른 프롬프트나 새 세션에서도
길을 잃지 않도록 [STATE.md](STATE.md)를 AI 작업 진입점으로 둔다.

### 문서 구조

```
docs/
├── README.md                    # docs 안내 (사람/AI 구분)
├── user/
│   └── TROUBLESHOOT.md          # 문제 해결 과정 (증상→원인→해결→교훈)
└── agent/
    ├── STATE.md                 # 세션 진입점 — 현재 위치·다음 할 일·열린 이슈
    ├── OVERVIEW.md              # 전체 흐름·아키텍처 1페이지
    ├── ROADMAP.md               # 단계별 할 일 체크리스트
    ├── DECISION.md              # 의사결정 + 이유
    ├── PLAN.md                  # 설계 단일 출처 (상세)
    ├── SETUP.md                 # 스킬·구조 자산 정리
    └── CODEX.md                 # Codex 작업 지침
```

### 문서 규칙 (글로벌 §6 계승)

- 톤: 평서체. 의인화·과장·감정 표현 금지.
- 도메인 문서는 "프로젝트에서 어떻게 쓰는지" 먼저, 배경은 뒤로.
- 표는 컬럼 폭 정렬. 작업 체크리스트는 항목마다 ✅ 갱신.
- 미해결 이슈는 발견 문서·해결 문서 양쪽에 교차 기록(#2 패턴).
- 작업 전 [STATE.md](STATE.md)를 읽고, 작업 후 STATE·ROADMAP을 갱신한다.
- 의미 있는 문제 해결 과정은 [../user/TROUBLESHOOT.md](../user/TROUBLESHOOT.md)에 시간순으로 기록한다.
- Codex/비-Claude 에이전트 공통 진입점은 [../../AGENTS.md](../../AGENTS.md), 세부 지침은 [CODEX.md](CODEX.md)에 둔다.

---

## D. 폴더 구조

PLAN의 L0~L6 레이어와 #2의 검증된 패턴(config 외부화, src 분리, DuckDB 회사/연도 격리)을
결합한다.

```
multi-BS/
├── pyproject.toml              # uv + dependency-groups
├── CLAUDE.md                   # §B 골격
├── .claude/
│   └── skills/
│       ├── disclosure-review/SKILL.md      # A-2
│       ├── disclosure-testing/SKILL.md     # A-2
│       └── skill-rules.json                # 프로젝트 스코프 트리거
├── config/
│   ├── settings.py             # pydantic-settings 중앙 설정
│   ├── canonical_accounts.yaml # XBRL → 표준 계정 매핑 (COA, 하드코딩 금지)
│   └── playbooks/              # 원칙3: 지식은 데이터로
│       ├── identities.yaml     #   회계 항등식
│       ├── relationship_chains.yaml  # 계정 관계 사슬 (§6.2)
│       └── watchlist.yaml      #   주석 변화 키워드 (§6.4)
├── src/
│   ├── collect/                # L0  OpenDART 수집 (재무제표 JSON + 주석 TSV)
│   ├── normalize/              # L1  XBRL → canonical + mapping confidence (Arelle)
│   ├── notes/                  # L1.5 주석 인덱서 (섹션 분류·계정매핑·note diff)
│   ├── signals/                # L2  materiality / relationship_graph / qoe / change
│   ├── analysis_tools/         #     tool DSL 함수 (compare_growth 등, §8)
│   ├── agents/                 # L3  5개 역할 에이전트 (PydanticAI)
│   ├── orchestrate/            #     순수 Python async 파이프라인 (D2)
│   ├── report/                 # L4  Finding 종합
│   ├── schemas/                #     EvidenceRef / AccountFinding / DisclosureChangeFinding
│   └── db/                     #     DuckDB ConnectionManager (회사/연도 격리)
├── dashboard/                  # L5  Streamlit + plotly (review queue UI)
├── data/
│   └── companies/{corp}/{year}/analysis.duckdb   # #2 격리 패턴
├── tests/
└── docs/                       # §C
```

- `config/playbooks/`·`canonical_accounts.yaml` 이 원칙3(지식은 데이터)을 물리적으로 강제.
- `data/companies/{corp}/{year}/` 격리는 #2의 Company/Engagement 패턴 그대로(회사·연도별 DB).
- `src/analysis_tools/` 는 LLM이 호출하는 tool DSL 전용 — 자유 SQL이 여기로 새지 않게 격리.

---

## E. dependency-groups (초안)

```
core      = ["pandas>=2.2", "pandera", "duckdb", "pyyaml", "pydantic-settings",
             "OpenDartReader", "arelle-release"]
agent     = ["pydantic-ai", "openai", "google-genai"]
dashboard = ["streamlit", "plotly"]
dev       = ["pytest", "ruff", "mypy"]
```

MVP 설치: `uv sync --group core --group agent --group dashboard --group dev`
(주석 섹션 분류에 임베딩이 필요해지면 `embed` 그룹 추가.)

---

## F. 생성 결과 (완료)

- [x] `CLAUDE.md` (§B 골격)
- [x] `.claude/skills/disclosure-review/SKILL.md` + `disclosure-testing/SKILL.md` + `skill-rules.json` (§A-2)
- [x] `pyproject.toml` + 폴더 스캐폴딩 (§D, §E)
- [x] `docs/agent/DECISION.md` (D1~D4 이관)
- [x] docs 구조 재편 (`user/` · `agent/` 분리, STATE/OVERVIEW/ROADMAP 신설)

이후 진행 상태는 [STATE.md](STATE.md), 할 일은 [ROADMAP.md](ROADMAP.md) 참조.
