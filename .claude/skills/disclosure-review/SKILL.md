---
name: disclosure-review
description: "Disclosure Review Agent code review checklist for multi-BS. Use when reviewing changes to OpenDART collection, XBRL normalization, note indexer, signal engine, tool DSL, role agents, Finding report, DuckDB isolation, or Streamlit review UI. Triggers: code review, 코드 리뷰, Finding, 공시, 주석, XBRL, 정규화, materiality, signal engine, tool DSL, disclosure change, 분식, fraud language. 공시 재무제표 리뷰 시 활성화."
---

# Disclosure Review (multi-BS)

## 원칙

리뷰는 findings 우선. 버그·회귀·테스트 누락·과장된 audit 언어·계산 환각·secret 노출·문서
drift 중심. 전역 `code-reviewer` 에이전트와 별개로 공시 분석 도메인 규약을 강제한다.
설계 단일 출처는 `docs/agent/PLAN.md`.

## 출력 형식

1. findings 먼저, severity 순
2. file:line 참조
3. 각 finding: impact + 구체 수정 방향
4. 미해결 질문/가정 따로
5. 요약은 부수적·간결
6. 이슈 없으면 명시 + 잔여 테스트 갭/미검증 위험 나열

## 포지셔닝 / 언어 (최우선)

CLAUDE.md 포지셔닝 원칙(PLAN §15) 강제:

> 이 도구는 부정을 확정하지 않는다. 감사인이 검토할 리스크 후보를 제시한다.

체크:
- 결과 언어가 "분식 확정 / 부정 적발"로 들리지 않음 (review 후보로 표현)
- 모든 Finding이 `counter_evidence`·`normal_explanation`·`confirm_question`·`next_procedure`를 포함
- priority/risk 언어가 약한 신호를 과장하지 않음
- "운영 성능 검증 완료" 류 성능보장 표현 없음

## 계산 vs LLM 분리 (원칙 1·4)

- **숫자 계산이 LLM 경로에 들어가지 않음.** 증감률·비율·항등식은 `src/signals` /
  `src/analysis_tools`의 결정론 코드. LLM은 계산 결과를 해석만.
- LLM 주장은 반드시 `EvidenceRef`(실제 수치·주석 위치)를 인용. grounding 없는 주장은 반려.
- LLM은 자유 SQL이 아니라 tool DSL 함수만 호출. 자유 SQL이 `analysis_tools` 밖으로 새지 않음.
- 반박 에이전트(⑤)가 근거 없는 주장을 기각하는 경로가 유지됨.

## 에이전트 경계 (원칙 2)

- 에이전트는 **역할(관점) 5개 고정** — 데이터 차원(계정·기간)을 에이전트로 만들지 않음.
- 신규 에이전트 추가 시 **에이전트 추가 게이트**(PLAN §3 원칙2) 통과 여부 확인.
- ③ 흐름(공간축)과 ④ 변동(시간축)의 책임이 섞이지 않음. ④ 변동 에이전트는 계정-agnostic.

## 수집 / 정규화 / 데이터 계약 (L0·L1)

- OpenDART 응답 파싱: 연결/별도(CFS/OFS), 보고서 구분, 누락 컬럼 graceful 처리.
- canonical account 매핑에 `mapping_status`(exact/alias/parent_rollup/unmapped) 부여.
- **unmapped 계정을 분석 제외하지 않고 "기타 중요 계정"으로 게시** (누락 = 2종오류).
- 계정 코드·라벨 하드코딩 금지 → `config/canonical_accounts.yaml` (`pandera-validation` 참조).
- 금액 비교는 round 후 (`accounting-precision` 참조). `closing_balance` 의미(당기증감 vs
  누적잔액) 혼동 금지.
- Pandera 3계층: L1 구조 → L2 회계 항등식 → L3 통계 순차 적용.

## 주석 인덱서 (L1.5)

- 섹션 분류(note_section_type) 결과가 안정적 — 미분류 섹션은 누락이 아니라 기타로 보존.
- note diff(전기/당기 정렬)가 watchlist 키워드 등장을 정확히 잡음.
- 계정 ↔ 주석 섹션 매핑이 끊기지 않음.

## 신호엔진 (L2)

- materiality / relationship graph / QoE / change 신호가 설정(playbook) 기반 — 코드 하드코딩 아님.
- score는 normalized 후 집계. **severity 텍스트(High/Mid/Low) 직접 합산 금지.**
- 동적 계정 선정(top-N)이 유의성 큰 계정을 누락하지 않음.

## DuckDB / 격리

- `data/companies/{corp}/{year}/analysis.duckdb` 회사/연도 격리 보존.
- temp 테스트는 temp DB만. 운영 유사 경로 덤프 금지(사용자 명시 승인 시만).
- DDL 변경 시 contract 보존 또는 마이그레이션 경로 명확.

## Streamlit / Dashboard

- 위험·우선순위 문구가 과도하게 단정적이지 않음 (review 후보로 읽힘).
- 큰 DataFrame은 session state 저장·렌더링 전 cap. session key 안정·rerun-safe.
- CSS 변경이 의도한 컴포넌트로 scope. UI 동작 변경 시 import smoke + 좁은 테스트.

## Safety / Secrets

거부 또는 flag:
- `.env`, API 키, token, 공시 raw payload를 읽거나 출력/로깅.
- LLM payload·DataFrame·SQL 결과를 광범위 로깅.
- 전역 install·파괴적 cleanup·git 쓰기를 사용자 명시 승인 없이 추가.

## 문서 drift 점검

갱신 필요 여부:
- `docs/agent/PLAN.md` (아키텍처/원칙/MVP 변경)
- `docs/agent/DECISION.md` (결정 추가/번복)
- `docs/agent/DATA_CONTRACT.md` (스키마·mapping 변경, 생성 후)
- `docs/agent/SIGNAL_ENGINE.md` (신호 카탈로그 변경, 생성 후)
- `docs/agent/STATE.md` (작업 상태·다음 할 일)
- `docs/agent/ROADMAP.md` (진척 체크)
- `docs/human/TROUBLESHOOT.md` (의미 있는 버그·수정)

## 검증 기대치

- 테스트가 변경 동작에 scope?
- 결정론 계산은 정확한 기대값으로 검증? (LLM 경로와 분리)
- live-API/slow/browser 미실행 사유 명시?
- 최종 보고가 검증된 것·남은 위험을 구분?

## 전역 스킬·에이전트와의 관계

- 전역 `code-reviewer` — 코드 품질 일반. 본 스킬은 공시 도메인 semantics layer 추가.
- 전역 `verification-before-completion` — 본 스킬 "검증 기대치"와 정합.
- 전역 `pandera-validation`, `accounting-precision`, `ripple-search` — 도메인 룰 적용 시 함께 활성.
