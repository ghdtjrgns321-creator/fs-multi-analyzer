# Disclosure Review Agent — Project Context

> 멀티에이전트 교차검증 기반 공시 재무제표·주석 변화 리뷰 도구.
> 설계 단일 출처: [docs/agent/PLAN.md](docs/agent/PLAN.md) · 자산 정리: [docs/agent/SETUP.md](docs/agent/SETUP.md).
> 글로벌 룰(`~/.claude/CLAUDE.md` §1~§8)은 자동 적용되므로 여기서 재서술하지 않는다.

> **포지셔닝 원칙 (최우선·고정)**: 이 도구는 부정을 확정하지 않는다. 공시 재무제표에서
> 감사인이 검토할 리스크 후보를 설명 가능한 형태로 제시한다. "분식 확정", "부정 자동
> 적발", "운영 성능 검증 완료" 등 확정·성능보장 표현을 쓰지 않는다. 모든 Finding은
> 반대근거·정상설명·확인질문·다음절차를 포함한다. 단일 출처: [docs/agent/PLAN.md §15](docs/agent/PLAN.md).

## 워크플로우

문서는 보는 주체로 나뉜다(안내: [docs/README.md](docs/README.md)). `docs/agent/`는 AI 작업용,
`docs/user/`은 사람용이다.

- **작업 전**: [docs/agent/STATE.md](docs/agent/STATE.md)(현재 위치·다음 할 일) → 필요 시
  [OVERVIEW](docs/agent/OVERVIEW.md)·[PLAN](docs/agent/PLAN.md) 해당 레이어를 읽고 시작.
- **작업 중**: Agent·Skill 적극 활용 (병렬 탐색·리뷰는 subagent 위임).
- **작업 후 (필수)**: [docs/agent/STATE.md](docs/agent/STATE.md) 갱신(현재 위치·다음 할 일),
  진행 시 [ROADMAP](docs/agent/ROADMAP.md) 체크. 문제를 겪었으면
  [docs/user/TROUBLESHOOT.md](docs/user/TROUBLESHOOT.md)에 증상·원인·해결·교훈 기록.

## Quick Reference

| 항목        | 값                                       |
| ----------- | ---------------------------------------- |
| Python      | 3.11+                                    |
| 패키지 관리 | uv + pyproject.toml (dependency-groups)  |
| DB          | DuckDB (회사/연도 격리)                  |
| 에이전트    | PydanticAI + 순수 Python async (D2)      |
| 데이터      | OpenDART (재무제표 JSON + 주석 XBRL TSV) |
| XBRL 처리   | Arelle                                   |
| UI          | Streamlit + plotly                       |
| 테스트      | pytest (`uv run pytest tests/ -v`)       |
| 실행        | `uv run streamlit run dashboard/app.py`  |

## 핵심 설계 원칙 (PLAN §3)

1. **계산은 코드(결정론), 발견은 LLM.** 숫자 계산을 LLM에 맡기지 않는다.
2. **에이전트는 역할(관점)에만 대응, 계정은 데이터로 흐른다.** 데이터 차원(계정·기간)을
   에이전트로 만들지 않는다(추가 게이트).
3. **계정 전문성·관계는 코드가 아니라 데이터(playbook).** `config/` YAML 외부화.
4. **LLM은 풀되 사실에 앵커링.** tool DSL + EvidenceRef grounding + 반박 에이전트.
5. **수준(level)과 변화(change)를 함께 본다.** 공시 변동 에이전트(④)가 변화 전담.

## 환경 변수

```bash
# .env (프로젝트 루트, 커밋 금지)
DART_API_KEY=xxxxx          # OpenDART OpenAPI
OPENAI_API_KEY=sk-xxxxx     # LLM (추론/계산)
GOOGLE_API_KEY=xxxxx        # LLM 대안 (선택)
```

## 핵심 코딩 규칙

- 파일당 **100줄 내외**, SRP 준수.
- **계산-LLM 분리**: 숫자 계산은 `src/signals`·`src/analysis_tools`의 결정론 코드,
  LLM은 해석만. 둘을 한 함수에 섞지 않는다.
- **하드코딩 금지**: 계정 코드·관계 사슬·watchlist 키워드는 `config/` YAML 외부화
  (`pandera-validation` 스킬의 COA 패턴).
- **데이터 검증 Pandera 3계층**: L1 구조 → L2 회계 항등식 → L3 통계 (순차).
- **금액 비교는 round 후** (`accounting-precision` 스킬). materiality 비교 전 필수.
- **LLM 출력**: PydanticAI structured output + EvidenceRef로 실제 수치/주석 grounding 강제.
- **DuckDB**: `data/companies/{corp}/{year}/analysis.duckdb` 회사/연도 격리, 전역 공유 금지.
- **mapping confidence 투명**: unmapped 계정은 분석 제외가 아니라 "기타 중요 계정"으로 게시.

## Skill 활용 맵

| 레이어 / 상황                 | 활용 Skill                                   |
| ----------------------------- | -------------------------------------------- |
| 전 작업 공통                  | `superpowers` 플러그인 (TDD·완료검증·디버깅) |
| 파급 변경 (계정·playbook·DSL) | `ripple-search`                              |
| L1 정규화 / L2 신호엔진       | `pandera-validation`, `accounting-precision` |
| L3 에이전트 설계              | `subagent-orchestration`                     |
| L4/L5 리포트·UI               | `developing-with-streamlit`, `mermaid`       |
| 도메인 코드 리뷰              | `disclosure-review` (프로젝트 스코프)        |
| 도메인 테스트·완료 검증       | `disclosure-testing` (프로젝트 스코프)       |

## Agent 활용 가이드

| Agent                     | 용도                                  |
| ------------------------- | ------------------------------------- |
| `Plan` (빌트인)           | 새 레이어/단계 시작 시 구현 계획 수립 |
| `code-reviewer`           | 모듈 구현 완료 후 코드 리뷰           |
| `documentation-architect` | 문서 작성/리뷰/품질 검증              |
| `Explore` / `Plan`        | 코드베이스 탐색 / 아키텍처 설계       |

## dependency-groups

```
core      = pandas, pandera, duckdb, pyyaml, pydantic-settings, OpenDartReader, arelle-release
agent     = pydantic-ai, openai, google-genai
dashboard = streamlit, plotly
dev       = pytest, ruff, mypy
```

MVP 설치: `uv sync --group core --group agent --group dashboard --group dev`

## 문서 가이드

전체 안내는 [docs/README.md](docs/README.md). 핵심:

| 문서                                                   | 분류    | 내용                                                       |
| ------------------------------------------------------ | ------- | ---------------------------------------------------------- |
| [docs/agent/STATE.md](docs/agent/STATE.md)             | 🤖 AI   | **현재 상태·다음 할 일** (세션 진입점, 작업 종료마다 갱신) |
| [docs/agent/OVERVIEW.md](docs/agent/OVERVIEW.md)       | 🤖 AI   | 전체 흐름·아키텍처 요약                                    |
| [docs/agent/ROADMAP.md](docs/agent/ROADMAP.md)         | 🤖 AI   | 단계별 할 일 체크리스트                                    |
| [docs/agent/DECISION.md](docs/agent/DECISION.md)       | 🤖 AI   | 의사결정 + 이유 (D1~D4 이후)                               |
| [docs/agent/PLAN.md](docs/agent/PLAN.md)               | 🤖 AI   | 설계 단일 출처 (상세)                                      |
| [docs/agent/SETUP.md](docs/agent/SETUP.md)             | 🤖 AI   | 스킬·구조 자산 정리                                        |
| [docs/user/TROUBLESHOOT.md](docs/user/TROUBLESHOOT.md) | 👤 사람 | 문제 해결 과정 (시간순 누적)                               |

작업 전 STATE를 읽고, 완료 후 STATE·관련 docs를 갱신한다.

## Agent skills

### Issue tracker

이슈는 GitHub Issues(`ghdtjrgns321-creator/fs-multi-analyzer`)에서 추적하며 `gh` CLI로 처리한다. 외부 PR은 triage 대상이 아니다. `docs/agents/issue-tracker.md` 참조.

### Triage labels

5개 표준 역할(needs-triage / needs-info / ready-for-agent / ready-for-human / wontfix)을 기본 문자열 그대로 사용한다. `docs/agents/triage-labels.md` 참조.

### Domain docs

단일 컨텍스트(루트 `CONTEXT.md` + `docs/adr/`). `docs/agents/domain.md` 참조.
