---
name: disclosure-testing
description: "Disclosure Review Agent test selection and verification for multi-BS. Use when running pytest, validating signal engine calculations, testing XBRL normalization, note indexer, tool DSL, agents, or proving completion. Triggers: pytest, uv run pytest, signal test, normalization test, tool DSL test, agent test, dashboard import, 검증 완료, disclosure test. 공시 분석 테스트 시 활성화."
---

# Disclosure Testing (multi-BS)

## 원칙

테스트 범위는 변경 범위에 비례. 좁게 시작, contract 또는 사용자 가시 동작이 바뀌면 확장.
전역 `pytest-backend-testing`과 별개로 공시 분석 도메인 특화 룰(결정론 계산·XBRL 정규화·
tool DSL·LLM grounding)을 적용한다.

## 베이스라인 명령

```powershell
uv run pytest tests -q            # 전체 빠른 통과 확인
uv run pytest tests/ -v           # 상세
uv run ruff check .
uv run mypy .
uv run streamlit run dashboard/app.py
```

## 변경 영역별 테스트 선택

### 결정론 계산 (signals / analysis_tools) — 최우선 정확도
- 증감률·비율·항등식·tool DSL 함수는 **정확한 기대값**으로 검증 (golden number).
- materiality 비교는 round 경계 케이스 포함 (`accounting-precision`: 0.1+0.2 오차).
- 회계 항등식(자산=부채+자본, 기초+증감=기말, 영업CF 연결) 위반/정상 양쪽 케이스.
- **이 경로에 LLM이 끼어들지 않음을 보장** — 순수 함수 단위 테스트.

### 수집 / 정규화 (collect / normalize)
- OpenDART 응답은 fixture(저장된 JSON/TSV)로. **default 테스트에서 라이브 API 호출 금지.**
- 연결/별도, 보고서 구분, 누락 컬럼 graceful degradation 케이스.
- canonical 매핑 4단계(exact/alias/parent_rollup/unmapped) + unmapped 게시 동작 검증.
- 계정 코드 하드코딩 부재 확인 (YAML 매핑 경로).

### 주석 인덱서 (notes)
- 섹션 분류 + 계정↔섹션 매핑 + note diff(전기/당기) 케이스.
- watchlist 키워드 신규 등장 탐지 정확도. 미분류 섹션 보존.

### 역할 에이전트 (agents)
- LLM 호출은 mock / fake client / structured output 계약 테스트로. **라이브 API 금지.**
- 출력 스키마(AccountFinding / DisclosureChangeFinding) 검증 + EvidenceRef grounding 강제.
- 반박 에이전트가 근거 없는 주장을 기각하는 경로 테스트.
- invalid output / missing evidence 에 hallucination 대신 반려·재시도.

### DuckDB / 파이프라인 (db / orchestrate)
- temp DB path 또는 fixture만. 실제 `analysis.duckdb` 덤프 금지(사용자 승인 시만).
- 회사/연도 격리 유지. schema/contract 변경 시 파이프라인 테스트 확장.

### Streamlit / Dashboard
- 변경 탭/컴포넌트 좁은 테스트 + 항상 import smoke:
```powershell
uv run python -c "import dashboard.app"
```
- session key 안정성, 큰 DataFrame cap, rerun 동작. UI 동작 변경 시 브라우저 검증 권장.

### Docs-Only
- 일반적으로 pytest 불필요. 링크·single-source·관련 docs 갱신 필요 여부만 확인.

## Secret / 안전

- raw 공시 payload, API 키, token, secret이 전송·로깅·테스트 출력에 노출되지 않는지 검증.
- LLM payload·DataFrame을 광범위 로깅하지 않음.

## 완료 보고 (verification-before-completion 답습)

응답 전 다음 보고:
- 실제 실행한 검증 명령
- 각 명령 결과
- 의도적으로 건너뛴 검증 + 사유
- live-API/slow/browser 미실행 시 잔여 위험

## 전역 스킬과의 관계

- 전역 `pytest-backend-testing` — 일반 백엔드 패턴. 본 스킬은 공시 도메인 보완.
- `tdd`, `verification-before-completion` — 본 스킬 위에 덧붙여 적용.
