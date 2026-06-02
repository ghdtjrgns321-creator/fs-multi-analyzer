# STATE — 현재 작업 상태

> 새 세션·다른 프롬프트는 **이 파일부터** 읽는다. "지금 어디까지 됐고 다음은 무엇인가."
> 작업 종료 시 반드시 갱신한다. 전체 흐름은 [OVERVIEW.md](OVERVIEW.md), 상세 설계는
> [PLAN.md](PLAN.md), 할 일 전체는 [ROADMAP.md](ROADMAP.md).

## 현재 위치

- 단계: 설계 확정 → 프로젝트 뼈대 구축 → L0 수집 → L1 정규화 → L2 신호엔진 →
  **외부 맥락 ContextBrief 코드 완료, live 수집 보류**
- 최근 작업 (2026-06-02): Gemini Google Search grounding 기반 외부 맥락 수집 단계를
  `ContextBrief`로 추가했다. 외부 맥락은 Finding과 분리하며, grounding URL과 매칭되는
  출처(title+URL)가 있는 항목만 남긴다. `risk_level`, `issue_type`, 점수 등 판단 필드는
  변경하지 않는 mock 테스트를 추가했다. live 실행은 Gemini 3.5 Flash 503으로 보류했다.

## 완료

- 설계 단일 출처 [PLAN.md](PLAN.md) — 아키텍처 L0~L6, 원칙 5개, MVP 1~3
- 결정 D1~D4 ([DECISION.md](DECISION.md))
- 스킬 2종(`disclosure-review`/`disclosure-testing`) + skill-rules.json
- CLAUDE.md, pyproject.toml, config/playbooks, src/ 스캐폴딩, `src/schemas/findings.py`
- Codex/비-Claude 진입점 [../../AGENTS.md](../../AGENTS.md) + [CODEX.md](CODEX.md)
- L0 수집 모듈 [../../src/collect](../../src/collect)
- L0 raw 데이터 `data/companies/00126380/{2022,2023,2024}/raw/`
- Raw 데이터 계약 [DATA_CONTRACT.md](DATA_CONTRACT.md)
- L1 정규화 모듈 [../../src/normalize](../../src/normalize)
- L1 canonical config [../../config/canonical_accounts.yaml](../../config/canonical_accounts.yaml)
- L1 정규화 결과 `data/companies/00126380/{2022,2023,2024}/analysis.duckdb`
- L1 측정 보고서 [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md)
- 결정 D5 ([DECISION.md](DECISION.md))
- L2 tool DSL [../../src/analysis_tools](../../src/analysis_tools)
- L2 MVP1 관계 사슬 계산 [../../src/signals](../../src/signals)
- L2 계산 보고서 [SIGNAL_REPORT.md](SIGNAL_REPORT.md)
- L2 threshold 빨간불 추출 [../../src/signals/red_flags.py](../../src/signals/red_flags.py)
- 수치 분석가 1명 [../../src/agents/numeric_analyst.py](../../src/agents/numeric_analyst.py)
- D82242 주석 인덱서 [../../src/notes/indexer.py](../../src/notes/indexer.py)
- 매출채권 주석 분석가 [../../src/agents/note_analyst.py](../../src/agents/note_analyst.py)
- 매출채권 주석 매핑 [../../config/playbooks/note_mappings.yaml](../../config/playbooks/note_mappings.yaml)
- 외부 맥락 스키마 [../../src/schemas/context.py](../../src/schemas/context.py)
- Google Search grounding ContextBrief [../../src/agents/context_brief.py](../../src/agents/context_brief.py)
- 첫 Finding 실행 기록 [FINDING_REPORT.md](FINDING_REPORT.md)
- Gemini 일시 오류 재시도 테스트 [../../tests/test_red_flags_and_agent.py](../../tests/test_red_flags_and_agent.py)
- 주석 파싱/주석 분석가 mock 테스트 [../../tests/test_notes_and_note_agent.py](../../tests/test_notes_and_note_agent.py)
- 외부 맥락 출처/비오염 테스트 [../../tests/test_context_brief.py](../../tests/test_context_brief.py)
- 결정 D6 ([DECISION.md](DECISION.md))
- 결정 D8 ([DECISION.md](DECISION.md))

## 다음 할 일 (우선순위)

1. Gemini 3.5 Flash 가용성 회복 후 `uv run python -m src.agents.first_context_brief`
   재실행해 출처 포함 `context_brief` live 수집
2. Gemini 3.5 Flash 가용성 회복 후 `uv run python -m src.agents.first_note_finding`
   재실행해 D82242 `note_evidence`가 병합된 live Finding 생성
3. D82242 표 구조 정밀 복원 또는 note diff(2022↔2023) 추가 여부 결정

## 열린 이슈 / 주의

- `finstate_all` 응답에는 `fs_div` 컬럼이 없다. 수집 context에서 CFS/OFS를 주입해야 한다.
- `account_id == "-표준계정코드 미사용-"` 행이 존재한다. MVP1에서는 `매입채무`(2022)와
  `단기차입금`(2023~2024)이 label alias 보조를 필요로 했다.
- 전체 raw 행 기준 미매핑 비율은 높다. 현재 `canonical_accounts.yaml`이 MVP1 10개 계정만
  담기 때문이며, 미매핑 계정을 숨기지 않는다.
- 주석은 표와 텍스트가 섞인 HTML이다. 단순 TXT만으로는 행/열 구조가 손실된다.
- 이번 D82242 인덱서는 표를 텍스트 수준으로만 보존한다. 행/열 정밀 복원은 아직 하지 않았다.
- 유동비율, 영업CF/순이익 비율은 MVP1 계정 부족으로 보류했다.
- 수치 분석가 prompt는 외부 사실을 쓰지 않는다. 정상 설명은 일반적 가능성으로만 작성해야 한다.
- 외부 업황·뉴스 맥락은 `ContextBrief`로만 제시한다. 출처 없는 외부 주장은 버리고,
  Finding 판단 필드는 변경하지 않는다.
- Gemini fallback은 `gemini_fallback_model` 설정이 비어 있으면 비활성이다. OpenAI fallback은 사용하지 않는다.

## 진입 포인트

- 전체 흐름 → [OVERVIEW.md](OVERVIEW.md) → 상세 [PLAN.md](PLAN.md)
- Codex 작업 지침 → [../../AGENTS.md](../../AGENTS.md) → [CODEX.md](CODEX.md)
- 할 일 → [ROADMAP.md](ROADMAP.md) · 결정·이유 → [DECISION.md](DECISION.md)
- L1 측정 → [NORMALIZE_REPORT.md](NORMALIZE_REPORT.md)
- L2 계산 → [SIGNAL_REPORT.md](SIGNAL_REPORT.md)
- 첫 Finding → [FINDING_REPORT.md](FINDING_REPORT.md)
- 문제 기록(사람용) → [../user/TROUBLESHOOT.md](../user/TROUBLESHOOT.md)
