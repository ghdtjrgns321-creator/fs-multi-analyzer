# docs 안내

문서는 **보는 주체**에 따라 둘로 나눈다.

## 👤 `user/` — 사람이 읽는 문서

이 프로젝트를 누구에게든 설명할 때 쓴다. 하나로 합치지 않고 주제별로 나눴다.

| 문서 | 내용 |
|------|------|
| [user/FEATURES.md](user/FEATURES.md) | 핵심 기능 — 이 프로젝트가 무엇을 하는가 |
| [user/TECH_STACK.md](user/TECH_STACK.md) | 사용 기술과 이유 (비전문가용 풀이 포함) |
| [user/UI.md](user/UI.md) | 화면 구성 (설계안) |
| [user/UX.md](user/UX.md) | 사용자 경험 흐름 (설계안) |
| [user/TROUBLESHOOT.md](user/TROUBLESHOOT.md) | 문제 해결 과정 (증상→원인→해결→교훈, 시간순 누적) |

## 🤖 `agent/` — AI가 작업 중 확인하는 문서 (새 세션 진입점)

새 세션·다른 프롬프트로 작업을 시작할 때 **STATE → OVERVIEW** 순으로 읽으면 현재 맥락을
잡을 수 있다. 작업이 끝나면 STATE를 갱신한다.

Codex 또는 비-Claude 에이전트는 루트 [../AGENTS.md](../AGENTS.md)를 먼저 읽고,
세부 지침은 [agent/CODEX.md](agent/CODEX.md)를 따른다.

| 문서 | 내용 | 갱신 시점 |
|------|------|-----------|
| [agent/STATE.md](agent/STATE.md) | **현재 작업 상태·다음 할 일** (세션 핸드오프) | 작업 종료마다 |
| [agent/OVERVIEW.md](agent/OVERVIEW.md) | 전체 흐름·아키텍처 요약 + 문서 맵 | 구조 변경 시 |
| [agent/ROADMAP.md](agent/ROADMAP.md) | 단계별 할 일 체크리스트 | 진척마다 |
| [agent/DECISION.md](agent/DECISION.md) | 의사결정 + 이유 (D1~D4 이후) | 결정마다 |
| [agent/PLAN.md](agent/PLAN.md) | 설계 단일 출처 (상세) | 설계 변경 시 |
| [agent/DATA_CONTRACT.md](agent/DATA_CONTRACT.md) | OpenDART raw 구조·규모·정규화 입력 관찰 | 수집/스키마 변경 시 |
| [agent/NORMALIZE_REPORT.md](agent/NORMALIZE_REPORT.md) | L1 canonical 매핑 측정 결과 | 정규화 변경 시 |
| [agent/SIGNAL_REPORT.md](agent/SIGNAL_REPORT.md) | L2 결정론 신호 계산 결과 | 신호엔진 변경 시 |
| [agent/FINDING_REPORT.md](agent/FINDING_REPORT.md) | 첫 Finding 실행 기록 | Finding 생성 시 |
| [agent/SETUP.md](agent/SETUP.md) | 스킬·구조 자산 정리 | 셋업 변경 시 |
| [agent/CODEX.md](agent/CODEX.md) | Codex 에이전트 작업 지침 | — |
