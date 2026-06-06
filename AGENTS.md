# AGENTS.md

> Codex 및 비-Claude 에이전트용 프로젝트 진입점이다. Claude 전용 상세 규칙은
> [CLAUDE.md](CLAUDE.md), Codex 상세 작업 지침은 [docs/agent/CODEX.md](docs/agent/CODEX.md)를 참조한다.

## Project

`multi-BS`는 OpenDART XBRL 재무제표와 주석을 수집해 BS-IS-CF 숫자 흐름, 주석 근거,
전기 대비 공시 변화를 교차검증하는 Disclosure Review Agent다.

이 도구는 부정이나 분식을 확정하지 않는다. 감사인이 검토할 공시 재무제표 리스크 후보를
설명 가능한 형태로 제시한다.

## Required Entry Flow

새 세션이나 다른 프롬프트에서 작업을 시작할 때는 아래 순서로 읽는다.

1. [docs/agent/STATE.md](docs/agent/STATE.md) — 현재 위치, 다음 할 일, 열린 이슈
2. [docs/agent/OVERVIEW.md](docs/agent/OVERVIEW.md) — 전체 흐름과 아키텍처
3. [docs/agent/CODEX.md](docs/agent/CODEX.md) — Codex 작업 지침
4. 필요 시 [docs/agent/PLAN.md](docs/agent/PLAN.md) — 상세 설계 단일 출처

작업이 끝나면 [docs/agent/STATE.md](docs/agent/STATE.md)를 갱신한다. 진척이 있으면
[docs/agent/ROADMAP.md](docs/agent/ROADMAP.md)를 갱신하고, 의미 있는 문제 해결 과정은
[docs/user/TROUBLESHOOT.md](docs/user/TROUBLESHOOT.md)에 기록한다.

## Core Rules

- 숫자 계산은 LLM이 아니라 결정론 코드와 SQL로 수행한다.
- LLM은 계산 결과, 주석 근거, EvidenceRef를 해석하는 역할로 제한한다.
- 자유 Text-to-SQL보다 안전한 tool DSL을 우선한다.
- 계정명, 관계 사슬, watchlist 키워드는 코드에 하드코딩하지 않고 설정 또는 매핑 레이어에 둔다.
- 분석을 구동하는 회사·연도·계정·fs_div·규모 기준은 데이터나 호출 인자에서 받아야 하며, 상수·샘플 config 리터럴이 실제 계산을 좌우하면 버그다.
- Finding은 `counter_evidence`, `normal_explanation`, `confirm_question`, `next_procedure`를 포함한다.
- "분식 확정", "부정 적발", "운영 성능 검증 완료" 같은 확정·성능보장 표현을 쓰지 않는다.
- `.env`, API 키, 토큰, 원본 공시 payload, 대용량 민감 데이터 내용을 출력하지 않는다.

## Documentation Map

| 문서 | 목적 |
|------|------|
| [docs/README.md](docs/README.md) | 사람용·AI용 문서 구조 안내 |
| [docs/agent/STATE.md](docs/agent/STATE.md) | 세션 진입점 |
| [docs/agent/OVERVIEW.md](docs/agent/OVERVIEW.md) | 전체 흐름 1페이지 |
| [docs/agent/ROADMAP.md](docs/agent/ROADMAP.md) | 단계별 할 일 |
| [docs/agent/DECISION.md](docs/agent/DECISION.md) | 의사결정과 이유 |
| [docs/agent/PLAN.md](docs/agent/PLAN.md) | 설계 단일 출처 |
| [docs/agent/DATA_CONTRACT.md](docs/agent/DATA_CONTRACT.md) | OpenDART raw 구조·규모·정규화 입력 관찰 |
| [docs/agent/SETUP.md](docs/agent/SETUP.md) | 스킬·구조 자산 정리 |
| [docs/agent/CODEX.md](docs/agent/CODEX.md) | Codex 작업 지침 |
| [docs/user/TROUBLESHOOT.md](docs/user/TROUBLESHOOT.md) | 사람용 문제 해결 기록 |

## Verification

문서만 수정한 경우 링크와 참조 경로를 확인한다. 코드 변경 시 변경 범위에 맞는 최소 테스트를
먼저 실행하고, 완료 보고에 실행 명령과 결과를 구분해 적는다.
