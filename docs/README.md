# docs 안내

문서는 **보는 주체**에 따라 둘로 나눈다.

## 👤 `user/` — 사람이 읽는 문서

이 프로젝트를 누구에게든 설명할 때 쓴다. 하나로 합치지 않고 주제별로 나눴다.

| 문서                                                   | 내용                                                                                                |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| [user/FEATURES.md](user/FEATURES.md)                   | 핵심 기능 — 이 프로젝트가 무엇을 하는가                                                             |
| [user/LIMITATIONS.md](user/LIMITATIONS.md)             | 프로젝트 한계 — 못 하는 것·주의할 것 한곳 정리(외화재무 제외·LLM 의존·게이트 경계)                  |
| [user/DATA_SCOPE.md](user/DATA_SCOPE.md)               | 어떤 데이터를 쓰고 무엇을 넣고 빼나(DART 포함/제외) + 미검증 부분                                   |
| [user/WHY_NOT_LLM.md](user/WHY_NOT_LLM.md)             | 재무제표를 LLM에 그대로 넣는 것과 무엇이 다른가 (재현·전수·앵커링·일관성)                           |
| [user/LLM_MODEL_COMPARE.md](user/LLM_MODEL_COMPARE.md) | 온보딩 LLM 모델 비교 — 고위험 10사에서 gpt-5.4 vs 기존 검수, 왜 gpt-5.4를 쓰나                      |
| [user/MULTI_AGENT.md](user/MULTI_AGENT.md)             | 관점(에이전트) 6개의 기능·작동·근거 + 왜 멀티에이전트인가                                           |
| [user/TECH_STACK.md](user/TECH_STACK.md)               | 사용 기술과 이유 (비전문가용 풀이 포함)                                                             |
| [user/UI.md](user/UI.md)                               | 화면 구성 (설계안)                                                                                  |
| [user/UX.md](user/UX.md)                               | 사용자 경험 흐름 (설계안)                                                                           |
| [user/METHODOLOGY.md](user/METHODOLOGY.md)             | 분석 기준(인과관계·지표)을 정하는 2단계 방법론 + 왜                                                 |
| [user/BACKTEST.md](user/BACKTEST.md)                   | 실제 분식사건으로 도구를 검증하는 방법·정답지·한계                                                  |
| [user/BACKTEST_ANALYSIS.md](user/BACKTEST_ANALYSIS.md) | 백테스트 결과 해부 — 무엇을 잡고 무엇을 왜 놓쳤나(도구 약점 vs 결정론 한계)                         |
| [user/VERIFICATION.md](user/VERIFICATION.md)           | 엔진 검증 — 121사 전수 홀리스틱 리뷰 + 교차검증으로 계산 정확성을 세운 방법                         |
| [user/P1_AUDIT_HARNESS.md](user/P1_AUDIT_HARNESS.md)   | Phase1 감사 하니스 — 본질적 한계(입력 변형·LLM 확률성)와 회사 전수·판정 매트릭스·전용 에이전트 설계 |
| [user/TROUBLESHOOT.md](user/TROUBLESHOOT.md)           | 문제 해결 과정 (증상→원인→해결→교훈, 시간순 누적)                                                   |

## 🤖 `agent/` — AI가 작업 중 확인하는 문서 (새 세션 진입점)

새 세션·다른 프롬프트로 작업을 시작할 때 **STATE → OVERVIEW** 순으로 읽으면 현재 맥락을
잡을 수 있다. 작업이 끝나면 STATE를 갱신한다.

Codex 또는 비-Claude 에이전트는 루트 [../AGENTS.md](../AGENTS.md)를 먼저 읽고,
세부 지침은 [agent/CODEX.md](agent/CODEX.md)를 따른다.

| 문서                                                                           | 내용                                                                                         | 갱신 시점                |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | ------------------------ |
| [agent/STATE.md](agent/STATE.md)                                               | **현재 작업 상태·다음 할 일** (세션 핸드오프)                                                | 작업 종료마다            |
| [agent/OVERVIEW.md](agent/OVERVIEW.md)                                         | 전체 흐름·아키텍처 요약 + 문서 맵                                                            | 구조 변경 시             |
| [agent/ROADMAP.md](agent/ROADMAP.md)                                           | 단계별 할 일 체크리스트                                                                      | 진척마다                 |
| [agent/DECISION.md](agent/DECISION.md)                                         | 의사결정 + 이유 (D1~D4 이후)                                                                 | 결정마다                 |
| [agent/PLAN.md](agent/PLAN.md)                                                 | 설계 단일 출처 (상세)                                                                        | 설계 변경 시             |
| [agent/DATA_PIPELINE_SCOPE.md](agent/DATA_PIPELINE_SCOPE.md)                   | **데이터 출입(포함/제외) 전 단계 명세** — DART→수집→정규화→주석→적재                         | 스키마 변경 시           |
| [agent/PHASE1_INTEGRITY_PLAN.md](agent/PHASE1_INTEGRITY_PLAN.md)               | Phase1 완성(정합성) 테스트 프레임 A~F + 분식5사 1급                                          | 점검 진행 시             |
| [agent/PHASE1_VERIFICATION_PROTOCOL.md](agent/PHASE1_VERIFICATION_PROTOCOL.md) | **LLM 감사 프로토콜** — 회사별 데이터 dump를 에이전트가 읽고 판단(전 차원·구현상태·발견이력) | 검증/발견 시             |
| [agent/PHASE1_EXIT_GATE.md](agent/PHASE1_EXIT_GATE.md)                         | **PHASE1 종료게이트(S11)** — 결정론 최종 커버리지(recall 5/6) + 분식별 LLM 인계 매핑(빈칸 0) | Phase1 종료/신호 변경 시 |
| [agent/DATA_CONTRACT.md](agent/DATA_CONTRACT.md)                               | (역사) 초기 삼성 스파이크 raw 관찰 — 현재는 DATA_PIPELINE_SCOPE 참조                         | 수집/스키마 변경 시      |
| [agent/NORMALIZE_REPORT.md](agent/NORMALIZE_REPORT.md)                         | L1 canonical 매핑 측정 결과                                                                  | 정규화 변경 시           |
| [agent/SIGNAL_REPORT.md](agent/SIGNAL_REPORT.md)                               | L2 결정론 신호 계산 결과                                                                     | 신호엔진 변경 시         |
| [agent/FINDING_REPORT.md](agent/FINDING_REPORT.md)                             | 첫 Finding 실행 기록                                                                         | Finding 생성 시          |
| [agent/SETUP.md](agent/SETUP.md)                                               | 스킬·구조 자산 정리                                                                          | 셋업 변경 시             |
| [agent/CODEX.md](agent/CODEX.md)                                               | Codex 에이전트 작업 지침                                                                     | —                        |
