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
- [ ] MVP1 구현

## 레이어 구현 순서

- [x] L0 수집 (`src/collect`) — OpenDART 재무제표 + 주석 raw 저장
- [x] L1 정규화 (`src/normalize`) — canonical + mapping confidence
- [ ] L1.5 주석 인덱서 (`src/notes`) — 섹션 분류·note diff
- [ ] L2 신호엔진 (`src/signals`) — materiality·관계사슬·QoE·변화
- [ ] tool DSL (`src/analysis_tools`)
- [ ] L3 에이전트 5 (`src/agents`)
- [ ] L4 리포트 (`src/report`)
- [ ] L5 대시보드 (`dashboard`)
  - [ ] (필수) 못 맞춘 계정 → 사전 보강 인터랙션: 사용자가 계정 지정 시
    `config/canonical_accounts.yaml` 자동 확장 (Human-in-the-Loop). 상세: [../user/UX.md](../user/UX.md)

## MVP1 — 유동성·운전자본 + 공시 변동

- [x] BS/IS/CF 3개년 raw 수집
- [x] canonical mapping
- [ ] 매출 → 매출채권 → 영업CF 관계 사슬 분석
- [ ] 차입금 / 유동성 기본 분석
- [ ] 공시 변동 (watchlist 키워드 신규 등장)
- [ ] Finding 리포트 + 감사인 확인 질문

## 이후 (PLAN §16)

업종 벤치마크 · 주석 의미 diff 고도화 · 다회 토론 · RAGAS 평가
