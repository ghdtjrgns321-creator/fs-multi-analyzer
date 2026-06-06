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
- [x] L1.5 주석 인덱서 (`src/notes`) — 8개 주석 카테고리 매핑/섹션 파싱, note diff 보류
- [x] L2 신호엔진 (`src/signals`) — MVP1 관계 사슬 결정론 계산
- [x] tool DSL (`src/analysis_tools`) — compare_growth / compute_ratio
- [ ] L3 계정 에이전트 (`src/agents`) — 매출채권·장기차입금·사채 live 완료, 재고 mock 완료
- [x] L4 리포트 (`src/report`) — 6관점 독립 평가 + 교차 + 종합 live 완료
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
- [x] 외부 ContextBrief 5번째 관점 승격 + 외부 포함 교차 판정
- [x] 삼성전자 2025 사업보고서 포함 L0~L4 최신 재실행
- [x] 외부 관점 agentic search 개선(LLM 쿼리 생성 → 검색 → 외부 평가)
- [x] 외부 관점 Gemini 3.1 Pro preview 라우팅 분리
- [x] 동종업계 6번째 관점 추가(B 접근: 피어 지표 baseline + 교차 참여)
- [x] L4 삼성 하드코딩 일반화(company profile 동적 조회 + induty_code별 피어 config)
- [x] 차입금 / 유동성 기본 분석
- [x] 남은 주요 주석 카테고리 매핑(D82240/D82245/D82757/D82210/D86120/D83800)
- [x] BS·IS·CF 주요 계정 전면 등록 + IS·CF 흐름 분석 강화
- [x] 전 계정 보편 신호 스캔 + CFS/OFS 연결 괴리 신호
- [x] Stage1 백테스트 보편 스캔 결함 수정(account_id 변경 시계열 연결 + OFS fallback)
- [x] P7 관계엔진 연도 하드코딩 제거(config years 대신 데이터/호출자 years 사용)
- [x] Stage1 신호 아티팩트 억제 Tier 1+2(CF universal 제외, YoY 기저 가드, z cap, 계정 dedupe)
- [x] Stage1 mvp1 Tier 1 가드 확장(CF single_account_yoy 제외, 관계 divergence 양측 기저 가드)
- [x] Stage1 홀드아웃 검증 실행(엔진 동결, labels/run_backtest 인자화, positive 3/3)
- [x] Stage1 single_account_yoy 기저 가드 완성 + `%/pp` normalized strength cap
- [x] Stage1 백테스트 지표 재정의(발굴 recall 주지표 + 상위10 strict 보조)
- [x] Stage1 FIX 1·2·4(라벨 매핑 완전화, 진행률 계약자산/계약부채 사슬, 자산총계 sanity 가드)
- [x] Stage1 FIX 3(신호 두 트랙 분리 게시: 규모 계정 A / 소액 급변 B, legacy strict 병기)
- [ ] 공시 변동 (watchlist 키워드 신규 등장)
- [x] 첫 Finding 리포트 + 감사인 확인 질문 — Gemini 3.5 Flash 재시도 후 생성 완료

## 통합 경로 (Claude 확정 전략 — 매출채권 → 다(多)계정 → 통합)

> 이 프로젝트의 핵심은 여러 계정·신호를 멀티에이전트가 모아 **종합 판단**하는 것이다.
> 매출채권 1줄기만으로는 "통합"을 테스트할 수 없다. 계정 2~3개로 넓힌 뒤 통합 단계를 만든다.
> 전부(165개)가 아니라 **통합 작동을 증명할 최소 계정(3~4개)**으로 충분하다.

1. [x] 매출채권 줄기 (수치 + 주석 교차검증)
2. [x] **재고 줄기 추가** (매출채권 패턴 복제 + 일반화 점검 — 복제 비용 측정)
3. [x] 차입금 줄기 추가
4. [x] **통합 리포트(L4)** — 여러 Finding → "이 회사 종합 리스크 한 장" ← 통합 테스트 지점
5. [ ] 깊이 보강 (통합 작동 확인 후): note diff 정밀화, 외부 결과 도메인 필터 개선

### 계정 추가 비용 측정

- 매출채권 → 재고자산: config 8줄 추가(주석 매핑 4줄, 관계 4줄) + 일반화 코드 수정 1회.
- 재고자산 → 차입금·사채·충당부채: 주석 mapping/canonical/relationship config 보강 +
  L4 note material 하드코딩 제거 1회. 다음 계정은 YAML 추가 중심으로 확장 가능.
- BS·IS·CF 확장: canonical BS 34개, IS 17개, CF 18개 등록. 흐름 관점은 CF/차입/영업손익/
  운전자본 키워드 기반 material로 확대.
- 전수 보편 스캔: 코드 1개 모듈(`src/signals/universal.py`) 추가 후 계정 추가 없이 모든
  BS·IS·CF account_id에 YoY/z-score/구성비/CFS-OFS 괴리를 적용한다.

## 이후 (PLAN §16)

주석 의미 diff 고도화 · 다회 토론 · RAGAS 평가
