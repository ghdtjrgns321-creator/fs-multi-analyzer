# ROADMAP — 단계별 할 일

> 진척마다 체크. 현재 위치·우선순위는 [STATE.md](STATE.md). 설계 근거는 [PLAN.md](PLAN.md).

## 마일스톤

- [x] 설계 확정 (PLAN)
- [x] 결정 D1~D4 (DECISION)
- [x] 프로젝트 뼈대 스캐폴딩
- [x] docs 구조 재편 (user/ · agent/)
- [x] `uv sync` + smoke 검증
- [x] L0 수집 스파이크 (삼성전자 3개년 재무제표·주석 raw 수집)
- [x] L1 정규화 스파이크 (account_id 1순위 / label alias 보조 가설 검증)
- [x] L2 신호엔진 스파이크 (MVP1 관계 사슬 결정론 계산)
- [ ] MVP1 구현

## 레이어 구현 순서

- [x] L0 수집 (`src/collect`) — OpenDART 재무제표 + 주석 raw 저장
- [x] L1 정규화 (`src/normalize`) — canonical + mapping confidence
- [ ] L1.5 주석 인덱서 (`src/notes`) — D82242/D82638 섹션 파싱 완료, note diff 보류
- [x] L2 신호엔진 (`src/signals`) — MVP1 관계 사슬 결정론 계산
- [x] tool DSL (`src/analysis_tools`) — compare_growth / compute_ratio
- [ ] L3 에이전트 5 (`src/agents`) — 매출채권 live 완료, 재고 mock 완료/live 보류
- [x] L4 리포트 (`src/report`) — 4관점 독립 평가 + 교차 + 종합 live 완료
- [ ] L5 대시보드 (`dashboard`)
  - [ ] (필수) 못 맞춘 계정 → 사전 보강 인터랙션: 사용자가 계정 지정 시
    `config/canonical_accounts.yaml` 자동 확장 (Human-in-the-Loop). 상세: [../user/UX.md](../user/UX.md)

## MVP1 — 유동성·운전자본 + 공시 변동

- [x] BS/IS/CF 3개년 raw 수집
- [x] canonical mapping
- [x] 매출 → 매출채권 → 영업CF 관계 사슬 분석
- [x] 매출채권 D82242 주석 섹션 인덱싱 + 주석 분석가 mock 검증
- [x] 재고자산 D82638 주석 섹션 인덱싱 + 범용 계정 파이프라인 mock 검증
- [x] 외부 맥락 ContextBrief 스키마 + Google Search grounding mock 검증
- [x] 감사기준·K-IFRS 전수 평가 + 관계 사슬 audit_basis 매핑
- [x] 실무 재무지표·계정 조합 웹검색 발굴 + financial_ratios.yaml 외부화
- [x] 기본 합계 계정 추가 + 삼성 3개년 실무 재무지표 계산
- [x] L4 통합 리포트 결정론 큐 + 지표 요약
- [x] L4 멀티에이전트 독립 평가 + 교차 판정 구조
- [x] L4 수치·주석·흐름·변동 4관점 live 평가 (`gemini-2.5-flash`)
- [ ] 차입금 / 유동성 기본 분석
- [ ] 공시 변동 (watchlist 키워드 신규 등장)
- [x] 첫 Finding 리포트 + 감사인 확인 질문 — Gemini 3.5 Flash 재시도 후 생성 완료

## 통합 경로 (Claude 확정 전략 — 매출채권 → 다(多)계정 → 통합)

> 이 프로젝트의 핵심은 여러 계정·신호를 멀티에이전트가 모아 **종합 판단**하는 것이다.
> 매출채권 1줄기만으로는 "통합"을 테스트할 수 없다. 계정 2~3개로 넓힌 뒤 통합 단계를 만든다.
> 전부(165개)가 아니라 **통합 작동을 증명할 최소 계정(3~4개)**으로 충분하다.

1. [x] 매출채권 줄기 (수치 + 주석 교차검증)
2. [x] **재고 줄기 추가** (매출채권 패턴 복제 + 일반화 점검 — 복제 비용 측정)
3. [ ] 차입금 줄기 추가
4. [x] **통합 리포트(L4)** — 여러 Finding → "이 회사 종합 리스크 한 장" ← 통합 테스트 지점
5. [ ] 깊이 보강 (통합 작동 확인 후): 외부 맥락 live, note diff 정밀화

### 계정 추가 비용 측정

- 매출채권 → 재고자산: config 8줄 추가(주석 매핑 4줄, 관계 4줄) + 일반화 코드 수정 1회.
- 다음 계정 목표: config 추가만으로 `src.agents.account_finding` CLI 재사용.

## 이후 (PLAN §16)

업종 벤치마크 · 주석 의미 diff 고도화 · 다회 토론 · RAGAS 평가
